import logging
from enum import Enum

import redis
import telegram
from environs import Env
from requests import HTTPError
from telegram.ext import Updater, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, \
    KeyboardButton
from email_validate import validate

from moltin_api import get_products, get_access_token, \
    get_product_quantity, get_price_books, get_price_book, get_prices, get_image, add_to_cart, delete_from_cart, \
    update_product_quantity, get_cart_items, update_customer, create_customer

logger = logging.getLogger('bot_logger')


class BotLogsHandler(logging.Handler):

    def __init__(self, bot, admin_chat_id):
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        super().__init__()

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(
            chat_id=self.admin_chat_id,
            text=log_entry,
        )


class State(Enum):
    PRODUCTS_SENT = 1
    PRODUCT_HANDLED = 2
    PURCHASE_HANDLED = 3
    REGISTRATION_REQUESTED = 4
    ASKED_NAME = 5
    NAME_REQUESTED = 6
    EMAIL_REQUESTED = 7
    PHONE_NUMBER_REQUESTED = 8
    ORDER_REGISTERED = 9


SHOP_BACK_BUTTON = {
    'name': 'Назад',
    'data': 'back_to_menu'
}

PAYMENT_BACK_BUTTON = {
    'name': 'Вернуться к продуктам',
    'data': 'back_to_menu'
}

CART_BUTTON = {
    'name': 'Корзина',
    'data': 'go_to_cart'
}

PAYMENT_BUTTON = {
    'name': 'Перейти к оформлению',
    'data': 'go_to_payment'
}


def get_lists_of_buttons(buttons, cols_quantity):
    for button_number in range(0, len(buttons), cols_quantity):
        yield buttons[button_number: button_number + cols_quantity]


def get_inline_keyboard(buttons, cols_quantity):
    keyboard_buttons = []
    for button in buttons:
        keyboard_buttons.append(InlineKeyboardButton(button['name'], callback_data=button['data']))
    keyboard = get_lists_of_buttons(keyboard_buttons, cols_quantity)
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def start(update, context):
    message = 'Здравствуйте! Я бот для продажи свежайшей рыбы!'
    update.message.reply_text(
        text=message,
        reply_markup=ReplyKeyboardRemove(),
    )
    send_products(update, context)
    return State.PRODUCTS_SENT


def send_products(update, context):
    query = update.callback_query
    chat_id = update.effective_chat.id

    products = context.bot_data['products']
    keyboard_buttons = []
    for product in products:
        keyboard_buttons.append(
            {
                'name': product['name'],
                'data': product['id']
            }
        )

    keyboard_buttons.append(CART_BUTTON)
    message = 'Выберите продукт:'
    reply_markup = get_inline_keyboard(keyboard_buttons, 2)
    if query:
        message_id = query.message.message_id
        context.bot.delete_message(chat_id, message_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=reply_markup
    )
    return State.PRODUCTS_SENT


def handle_product(update, context):
    try:
        redis_client = context.bot_data['redis_client']
        access_token = get_access_token(redis_client)
        query = update.callback_query
        message_id = query.message.message_id
        chat_id = update.effective_chat.id
        product_id = query.data
        products_quantity = get_product_quantity(access_token, product_id)

        keyboard_buttons = []

        if products_quantity == 0:
            stock_message = 'К сожалению, данный товар закончился'

        else:
            keyboard_buttons = [
                {
                    'name': '1 кг',
                    'data': f'1 {product_id}'
                }
            ]
            stock_message = f'{products_quantity} кг на складе'

        if products_quantity >= 5:
            keyboard_buttons.append(
                {
                    'name': '5 кг',
                    'data': f'5 {product_id}'
                }
            )
        if products_quantity >= 10:
            keyboard_buttons.append(
                {
                    'name': '10 кг',
                    'data': f'10 {product_id}'
                }
            )

        keyboard_buttons.append(SHOP_BACK_BUTTON)
        keyboard_buttons.append(CART_BUTTON)
        price_books = get_price_books(access_token)
        price_book = get_price_book(access_token, price_books)
        prices = get_prices(price_book)

        products = context.bot_data['products']

        for product in products:
            if product['id'] == product_id:
                message = f'{product["name"]}\n\n' \
                          f'${prices[product["sku"]]} за кг\n\n' \
                          f'{stock_message}\n\n' \
                          f'{product["description"]}'
                current_product = product

        reply_markup = get_inline_keyboard(keyboard_buttons, 3)
        image = get_image(access_token, current_product)

        context.bot.delete_message(chat_id, message_id)

        context.bot.send_photo(
            chat_id=chat_id,
            photo=image,
            caption=message,
            reply_markup=reply_markup
        )

        return State.PRODUCT_HANDLED
    except HTTPError as http_error:
        logging.error(http_error.response.text)


def handle_purchase(update, context):
    try:
        redis_client = context.bot_data['redis_client']
        access_token = get_access_token(redis_client)
        query = update.callback_query
        chat_id = update.effective_chat.id
        message_id = query.message.message_id
        product_quantity, product_id = query.data.split(' ')
        cart = add_to_cart(access_token, product_id, product_quantity, chat_id)
        update_product_quantity(access_token, product_id, product_quantity, 'allocate')
        display_cart(cart, message_id, chat_id, context)

        return State.PURCHASE_HANDLED
    except HTTPError as http_error:
        logging.error(http_error.response.text)


def handle_cart(update, context):
    try:
        redis_client = context.bot_data['redis_client']
        access_token = get_access_token(redis_client)
        query = update.callback_query
        chat_id = update.effective_chat.id
        message_id = query.message.message_id
        cart = get_cart_items(access_token, chat_id)
        display_cart(cart, message_id, chat_id, context)

        return State.PURCHASE_HANDLED
    except HTTPError as http_error:
        logging.error(http_error.response.text)


def handle_removal(update, context):
    try:
        redis_client = context.bot_data['redis_client']
        access_token = get_access_token(redis_client)
        query = update.callback_query
        chat_id = update.effective_chat.id
        message_id = query.message.message_id

        product_quantity, product_id = query.data.split(' ')
        cart_item_id = context.user_data[product_id]
        cart = delete_from_cart(access_token, cart_item_id, chat_id)
        update_product_quantity(access_token, product_id, product_quantity, 'deallocate')
        display_cart(cart, message_id, chat_id, context)

        return State.PURCHASE_HANDLED
    except HTTPError as http_error:
        logging.error(http_error.response.text)


def display_cart(cart, message_id,  chat_id, context):
    keyboard_buttons = []
    message = 'Ваши продукты:\n\n'
    total_price = 0
    for product in cart['data']:
        product_name = product["name"]
        product_quantity = product["quantity"]
        product_id = product["product_id"]
        product_cost = product["meta"]["display_price"]["without_discount"]["value"]["amount"] / 100
        total_price += product_cost
        message += f'{product_name}\n' \
                   f'{product_quantity} кг в корзине на ' \
                   f'${product_cost}\n\n'
        keyboard_buttons.append(
            {
                'name': f'Удалить из корзины {product_name}',
                'data': f'{product_quantity} {product_id}'
            }
        )
        context.user_data[product_id] = product["id"]
    message += f'Всего: ${total_price}'
    if total_price > 0:
        keyboard_buttons.append(PAYMENT_BUTTON)
    keyboard_buttons.append(SHOP_BACK_BUTTON)
    reply_markup = get_inline_keyboard(keyboard_buttons, 1)
    context.bot.delete_message(chat_id, message_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=reply_markup
    )


def handle_registration(update, context):
    redis_client = context.bot_data['redis_client']
    query = update.callback_query
    chat_id = update.effective_chat.id
    customer_id = redis_client.get(f'id {chat_id}')
    if customer_id:
        message = 'Вы авторизованы. Желаете изменить данные или оформить заказ?'
        keyboard_buttons = [
            {
                'name': 'Изменить данные',
                'data': 'change_data'
            },
            {
                'name': 'Оформить заказ',
                'data': 'arrange_order'
            },
        ]

        reply_markup = get_inline_keyboard(keyboard_buttons, 2)
        query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
        return State.REGISTRATION_REQUESTED

    else:
        return proceed_registration(update, context)


def proceed_registration(update, context):
    query = update.callback_query
    user = query.from_user
    user_first_name = user['first_name']
    user_last_name = user['last_name']
    context.user_data['user_name'] = user_first_name + ' ' + user_last_name
    keyboard_buttons = [
        {
            'name': 'Да, всё верно',
            'data': 'name_accepted'
        },
        {
            'name': 'Нет, изменить',
            'data': 'name_rejected'
        }
    ]
    reply_markup = get_inline_keyboard(keyboard_buttons, 2)

    if user_last_name:
        query.edit_message_text(
            f'{user_first_name} {user_last_name} - это Ваши имя и фамилия?',
            reply_markup=reply_markup
        )
    else:
        query.edit_message_text(
            f'{user_first_name} - это Ваше имя?',
            reply_markup=reply_markup
        )
    return State.ASKED_NAME


def handle_order(update, context):
    query = update.callback_query
    message = 'Спасибо! Ваш заказ оформлен. Скоро с Вами свяжется менеджер.'
    reply_markup = get_inline_keyboard([PAYMENT_BACK_BUTTON], 1)
    query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

    return State.ORDER_REGISTERED


def handle_accepted_name(update, context):
    query = update.callback_query
    message = 'Пришлите мне почту для связи'
    query.edit_message_text(
        text=message
    )
    return State.EMAIL_REQUESTED


def handle_rejected_user_name(update, context):
    query = update.callback_query
    query.edit_message_text(
        text='Введите, пожалуйста, ваше имя и фамилию'
    )
    return State.NAME_REQUESTED


def handle_new_name(update, context):
    user_name = update.message.text
    context.user_data['user_name'] = user_name
    message = 'Пришлите мне почту для связи'
    update.message.reply_text(
        text=message,
        reply_markup=ReplyKeyboardRemove(),
    )
    return State.EMAIL_REQUESTED


def handle_email(update, context):
    email = update.message.text
    if validate(email):
        message = 'Пришлите мне Ваш номер телефона'
        context.user_data['email'] = email
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton('Предоставить номер телефона', request_contact=True)]], resize_keyboard=True
        )
        request_message = update.message.reply_text(
            text=message,
            reply_markup=reply_markup,
        )
        context.user_data['request_message_id'] = request_message.message_id
        return State.PHONE_NUMBER_REQUESTED
    else:
        message = 'Пожалуйста, проверьте введенные данные ' \
                  'и отправьте почту заново'
        update.message.reply_text(
            text=message,
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.EMAIL_REQUESTED


def handle_phone_number_text(update, context):
    message = 'Пожалуйста, воспользуйтесь кнопкой для передачи контакта'
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton('Предоставить номер телефона', request_contact=True)]], resize_keyboard=True
    )
    request_message = update.message.reply_text(
        text=message,
        reply_markup=reply_markup,
    )
    context.user_data['request_message_id'] = request_message.message_id
    return State.PHONE_NUMBER_REQUESTED


def handle_contact(update, context):
    try:
        redis_client = context.bot_data['redis_client']
        access_token = get_access_token(redis_client)
        chat_id = update.effective_chat.id
        phone_number = update.message.contact.phone_number
        user_name = context.user_data['user_name']
        email = context.user_data['email']

        customer_id = redis_client.get(f'id {chat_id}')
        if customer_id:
            customer = update_customer(access_token, user_name, phone_number, email, customer_id)
        else:
            customer = create_customer(access_token, user_name, phone_number, email)

        customer_id = customer['data']['id']

        redis_client.set(f'id {chat_id}', customer_id)

        request_message_id = context.user_data['request_message_id']

        message = 'Спасибо! Ваш заказ оформлен. Скоро с Вами свяжется менеджер.'
        reply_markup = get_inline_keyboard([PAYMENT_BACK_BUTTON], 1)
        context.bot.delete_message(chat_id, request_message_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup
        )

        return State.ORDER_REGISTERED
    except HTTPError as http_error:
        logging.error(http_error.response.text)


def main():
    env = Env()
    env.read_env()

    bot_token = env('BOT_TOKEN')
    admin_chat_id = env('ADMIN_CHAT_ID')
    host = env('HOST')
    port = env('PORT')
    db_password = env('DB_PASSWORD')
    client_id = env('CLIENT_ID')
    client_secret = env('CLIENT_SECRET')

    redis_client = redis.Redis(
        host=host,
        port=port,
        password=db_password,
        decode_responses=True
    )

    redis_client.set('client_id', client_id)
    redis_client.set('client_secret', client_secret)
    access_token = get_access_token(redis_client)

    bot = telegram.Bot(token=bot_token)

    logger.setLevel(logging.INFO)
    log_handler = BotLogsHandler(bot, admin_chat_id)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    log_handler.setLevel(logging.INFO)

    logger.addHandler(log_handler)

    try:
        products = get_products(access_token)

        updater = Updater(token=bot_token, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.bot_data['products'] = products
        dispatcher.bot_data['redis_client'] = redis_client

        conversation_handler = ConversationHandler(
            per_chat=False,
            entry_points=[CommandHandler('start', start)],
            states={
                State.PRODUCTS_SENT: [
                    CallbackQueryHandler(
                        handle_cart,
                        pattern='go_to_cart'
                    ),
                    CallbackQueryHandler(
                        handle_product
                    )
                ],
                State.PRODUCT_HANDLED: [
                    CallbackQueryHandler(
                        send_products,
                        pattern='back_to_menu'
                    ),
                    CallbackQueryHandler(
                        handle_cart,
                        pattern='go_to_cart'
                    ),
                    CallbackQueryHandler(
                        handle_purchase
                    )
                ],
                State.PURCHASE_HANDLED: [
                    CallbackQueryHandler(
                        send_products,
                        pattern='back_to_menu'
                    ),
                    CallbackQueryHandler(
                        handle_registration,
                        pattern='go_to_payment'
                    ),
                    CallbackQueryHandler(
                        handle_removal
                    )
                ],
                State.REGISTRATION_REQUESTED: [
                    CallbackQueryHandler(
                        proceed_registration,
                        pattern='change_data'
                    ),
                    CallbackQueryHandler(
                        handle_order,
                        pattern='arrange_order'
                    ),
                ],
                State.ASKED_NAME: [
                    CallbackQueryHandler(
                        handle_accepted_name,
                        pattern='name_accepted'
                    ),
                    CallbackQueryHandler(
                        handle_rejected_user_name,
                        pattern='name_rejected'
                    ),
                ],
                State.NAME_REQUESTED: [
                    MessageHandler(
                        Filters.text,
                        handle_new_name
                    )
                ],
                State.EMAIL_REQUESTED: [
                    MessageHandler(
                        Filters.text,
                        handle_email
                    )
                ],
                State.PHONE_NUMBER_REQUESTED: [
                    MessageHandler(
                        Filters.text,
                        handle_phone_number_text
                    ),
                    MessageHandler(
                        Filters.contact,
                        handle_contact
                    ),
                ],
                State.ORDER_REGISTERED: [
                    CallbackQueryHandler(
                        send_products
                    )
                ],
            },
            fallbacks=[
                CommandHandler('start', start)
            ]
        )

        dispatcher.add_handler(conversation_handler)
        logger.info('The bot started')
        updater.start_polling()
        updater.idle()
    except HTTPError as http_error:
        logger.error(http_error.response.text)


if __name__ == '__main__':
    main()
