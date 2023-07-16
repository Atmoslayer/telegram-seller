import json
import logging

import requests


def test_token(access_token):
    url = 'https://useast.api.elasticpath.com/v2/carts/abc'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        return False
    else:
        return True


def get_new_token(client_id, client_secret):
    url = 'https://useast.api.elasticpath.com/oauth/access_token'
    data = {
        'client_id': client_id,
        'grant_type': 'client_credentials',
        'client_secret': client_secret
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    new_token = response.json()['access_token']
    logging.info('New token generated')
    return new_token


def get_access_token(redis_client):
    access_token = redis_client.get('access_token')
    client_id = redis_client.get('client_id')
    client_secret = redis_client.get('client_secret')
    is_valid_token = test_token(access_token)
    if not is_valid_token:
        access_token = get_new_token(client_id, client_secret)
    redis_client.set('access_token', access_token)
    return access_token


def add_to_cart(access_token, product_id, quantity, chat_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': int(quantity),
        }
    }
    data = json.dumps(data)
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def delete_from_cart(access_token, product_id, chat_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items/{product_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_items(access_token, chat_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_products(access_token):
    url = 'https://useast.api.elasticpath.com/pcm/products'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'include': 'main_image'
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    products = response.json()

    ordered_products = []
    for index, product in enumerate(products['data']):
        product_sku = product['attributes']['sku']
        product_id = product['id']
        ordered_product = {
            'id': product_id,
            'name': product['attributes']['name'],
            'description': product['attributes']['description'],
            'sku': product_sku,
            'slug': product['attributes']['slug'],
            'image_url': products['included']['main_images'][index]['link']['href'],
            'image_type': products['included']['main_images'][index]['mime_type'].split('/')[1]
        }
        ordered_products.append(ordered_product)
    return ordered_products


def get_price_books(access_token):
    url = 'https://useast.api.elasticpath.com/pcm/pricebooks/'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_price_book(access_token, price_books):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'include': 'prices'
    }
    for price_book in price_books['data']:
        if price_book['attributes']['name'] == 'Fish price book':
            url = f'https://useast.api.elasticpath.com/pcm/pricebooks/{price_book["id"]}'
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

    return response.json()


def get_prices(price_book):
    prices = {}
    for price in price_book['included']:
        price_attributes = price['attributes']
        prices[price_attributes['sku']] = price_attributes['currencies']['USD']['amount'] / 100
    return prices


def get_product_quantity(access_token, product_id):
    url = f'https://useast.api.elasticpath.com/v2/inventories/{product_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    product_quantity_data = response.json()
    product_quantity = product_quantity_data['data']['available']

    return product_quantity


def get_image(access_token, product):
    url = product['image_url']
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.content


def update_product_quantity(access_token, product_id, quantity, action):
    url = f'https://useast.api.elasticpath.com/v2/inventories/{product_id}/transactions'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'data': {
            'type': 'stock-transaction',
            'action': action,
            'quantity': int(quantity),
        }
    }
    data = json.dumps(data)
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def create_customer(access_token, user_name, phone_number, email):
    url = f'https://useast.api.elasticpath.com/v2/customers'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'data': {
            'type': 'customer',
            'name': user_name,
            'email': email,
            'password': phone_number
        }
    }
    data = json.dumps(data)
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def update_customer(access_token, user_name, phone_number, email, customer_id):
    url = f'https://useast.api.elasticpath.com/v2/customers/{customer_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'data': {
            'type': 'customer',
            'name': user_name,
            'email': email,
            'password': phone_number
        }
    }
    data = json.dumps(data)
    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()
