# Телеграм бот для продажи рыбы
Проект содержит чат бота, продающего рыбу через сервис [elasticpath](https://www.elasticpath.com/).
Посредством запросов бот получает от сервиса всю необходимую информацию и отображает её пользователю.
## Пример работы бота
![](https://github.com/Atmoslayer/telegram-seller/blob/main/fish-shop.gif)

[Рабочая версия проекта](https://t.me/atmoslayer_seller_bot)
## Как установить
### Для elasticpath
Необходимо зарегистрироваться в сервисе и перейти в [личный кабинет](https://useast.cm.elasticpath.com/).
После регистрации в разделе `system/application_keys` необходимо сохранить `STORE_ID` подобный этому: 
`mmfnshryueldfsk894kksd93llfsdfFk38fdsD` и создать новый API-ключ. После его создания необходимо
сохранить `CLIENT_ID` подобный этому: `212LJ3k0i2382364HIUEjfeJB98yvH` и  `CLIENT_SECRET` подобный этому 
`ttthrhdkdnvbahdkeotk-784jalfjhq6rr7f9hg`. Вторая переменная будет показана лишь раз, о чем сервис предупреждает после 
создания ключа.
После создания ключа можно приступать к созданию продуктов в разделе `products`.
Для корректной работы с API необходимо активировать все продукты, создать для них иерархии и книгу цен в разделе
`price book`. При создании книгу необходимо назвать `Fish price book`. После создания всего вышеперечисленного 
необходимо создать каталог в разделе `catalogs`, где объединить все данные и опубликовать его.
### Для телеграм бота
Необходимо создать телеграм бота с помощью отца ботов @BotFather, написав ему и выбрав имена для бота. 
После этого будет получен токен, подобный этому: `1234567890:ABCDEFGHIjklmnoPqrsStuvwxyzINet1234`.
Логи работы телеграм бота отсылаются администратору, телеграм id которого можно получить,
написав боту @getmyid_bot.
После этого будет получен id наподобие этого: `1234567891`.
### Для базы данных
В качестве базы данных в проекте используется redis. Для получения данных подключения к БД необходимо зарегистрироваться 
на сайте [redislabs](https://redislabs.com/). Возможно, для этого потребуется подключение через VPN. 
Необходимы ссылка на подключение наподобие этой: `redis-1234.asia-northwest1-1.cloud.redislabs.com`,
порт наподобие этого: `12345`, пароль от базы данных наподобие этого: `qjrljfsdfireppnbvmsdfsdklwer`.
### Для работы проекта
Для хранения токенов в проекте используются переменные окружения. Все полученные ключи нужно сохранить в файле 
`.env` в подобном виде:
```
STORE_ID=mmfnshryueldfsk894kksd93llfsdfFk38fdsD
CLIENT_ID=212LJ3k0i2382364HIUEjfeJB98yvH
CLIENT_SECRET=ttthrhdkdnvbahdkeotk-784jalfjhq6rr7f9hg
BOT_TOKEN=234567890:ABCDEFGHIjklmnoPqrsStuvwxyzINet1234
ADMIN_CHAT_ID=1234567891
HOST=redis-1234.asia-northwest1-1.cloud.redislabs.com
PORT=12345
DB_PASSWORD=qjrljfsdfireppnbvmsdfsdklwer
```
Python3 должен быть уже установлен.
Затем используйте `pip` (или `pip3`, если есть конфликт с Python2) для установки зависимостей:
```
pip install -r requirements.txt
```
## Запуск проекта
Бот запускается командой:
```commandline
python telegram_bot.py
```
После запуска бот готов к работе.
### Запуск с помощью docker
Проект содержит dockerfile, позволяющий создать образ и контейнер для проекта.
Docker должен быть установлен и запущен.
Для создания образа используйте `docker build` с указанием имени образа через `-t`:
```commandline
docker build . -t seller-bot
```
Для создания контейнеров  в каталоге проекта используйте `docker run` с указанием имени контейнера через `--name`, указанием пути к .env файлу через `--env-file` 
и аргументом для запуска бота:
```commandline
docker run --name seller-bot --env-file=./.env -it seller-bot python telegram_bot.py
```
Для запуска перезагружаемого в случае ошибки контейнера используйте:
```commandline
docker run --name seller-bot --restart unless-stopped --env-file=./.env -it seller-bot python telegram_bot.py
```
После создания контейнера бот будет готов к работе.