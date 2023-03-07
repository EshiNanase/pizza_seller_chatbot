import requests
import json

TIMESTAMP = None


def get_access_token(client_id, client_secret):

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    token = response.json()['access_token']
    timestamp = response.json()['expires']
    return token, timestamp


def get_access_token_implicit(client_id):

    payload = {
        'client_id': client_id,
        'grant_type': 'implicit'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    token = response.json()['access_token']
    return token


def get_cart(token, chat_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{chat_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_items(token, chat_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers)
    response.raise_for_status()
    return response.json()


def delete_cart_item(token, chat_id, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{chat_id}/items/{product_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def create_customer(token, chat_id, email):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    payload = {
        'data': {
            'type': 'customer',
            'name': str(chat_id),
            'email': email
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/customers', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_price_book(token, price_book_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/pcm/pricebooks/{price_book_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def create_cart(token, chat_id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-moltin-customer-token': chat_id
    }
    payload = {
        'data': {
            'name': chat_id,
            'description': f'{chat_id}\'s cart'
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/carts', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def add_products_to_cart(token, chat_id, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'data': {
            "id": product_id,
            "type": "cart_item",
            "quantity": 1,
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_products(token):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get('https://api.moltin.com/pcm/products', headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(token, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/catalog/products/{product_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def create_product(token, data):
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    response = requests.post(f'https://api.moltin.com/pcm/products/', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()


def create_product_v2(token, data):
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    response = requests.post(f'https://api.moltin.com/v2/products', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()


def get_stock(token, product_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/inventories/{product_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def get_file(token, file_id):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def create_file(token, file):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.post(f'https://api.moltin.com/v2/files/', headers=headers, files=file)
    response.raise_for_status()
    return response.json()


def attach_file(token, product_id, file):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.post(f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image', headers=headers, json={'data': file})
    response.raise_for_status()


def create_product_price(token, price_book_id, data):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.post(f'https://api.moltin.com/pcm/pricebooks/{price_book_id}/prices', headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def create_flow_field(token, data):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.post('https://api.moltin.com/v2/fields', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()


def create_flow(token, data):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.post('https://api.moltin.com/v2/flows', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()


def load_data(access_token, file_name):
    products = open_json(file_name)
    for product in products:

        data = {
            'type': 'product',
            'attributes': {
                'name': product['name'],
                "slug": str(product['id']),
                "sku": str(product['id']) + 'sku',
                'description': product['description'],
                "status": "live",
                "commodity_type": "physical",
                "manage_stock": False,
            }

        }

        product_created = create_product(access_token, data)

        file = {
            'file_location': (None, product['product_image']['url']),
        }

        image_created = create_file(access_token, file)

        image_data = {
            'type': 'file',
            'id': image_created['data']['id']
        }
        attach_file(access_token, product_created['data']['id'], image_data)

        price_data = {
            "data": {
                "type": "product-price",
                "attributes": {
                    "sku": str(product['id']) + 'sku',
                    "currencies": {
                        "USD": {
                            "amount": int(int(product['price'])/60),
                            "includes_tax": True,
                        }
                    }
                }
            }
        }
        price_created = create_product_price(access_token, '4228904d-b1cc-4517-a805-f8835a69fea5', price_data)


def load_addresses(access_token, flow_id, filename):
    addresses = open_json(filename)
    for address in addresses:
        description = f"{address['address']['full']}\n{address['coordinates']['lat']}:::{address['coordinates']['lon']}"
        data = {
            "type": "field",
            "name": address['alias'],
            "slug": address['id'],
            "field_type": "string",
            'description': description,
            'required': False,
            'enabled': True,
            'homosexual': 'i am',
            "relationships": {
                "flow": {
                    "data": {
                        "type": "flow",
                        "id": flow_id
                    }
                }
            }
        }
        create_flow_field(access_token, data)


def create_flow_entry(token, slug, coordinates):

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    data = {
        'type': 'entry'
    }
    data.update(coordinates)
    response = requests.post(f'https://api.moltin.com/v2/flows/{slug}/entries', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()


def open_json(file_name):
    with open(file_name, 'r', encoding='utf-8') as file:
        data = file.read()
    return json.loads(data)


def get_flow_entries(token, slug, page):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries?page[limit]=100&page[offset]={page*100}', headers=headers)
    return response.json()


def update_flow_entry(token, slug, entry_id, data):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.put(f'https://api.moltin.com/v2/flows/{slug}/entries/{entry_id}', headers=headers, json={'data': data})
    response.raise_for_status()
    return response.json()
