from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from elasticpath import get_products
import textwrap


def send_menu(access_token):
    products = get_products(access_token)

    message = textwrap.dedent(
        """
        Внимание, внимание\!
        Открывается веселое гуляние\!
        Торопись, честной народ,
        Тебя ярмарка зовет\!
        """
    )

    keyboard = []
    for product in products['data']:
        keyboard.append([InlineKeyboardButton(product['attributes']['name'], callback_data=product['id'])])
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='basket')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    return message, reply_markup


def send_basket(cart_items):
    message = ''
    total = 0
    keyboard = [[InlineKeyboardButton('Оплатить', callback_data='payment')]]

    for product in cart_items['data']:
        price = int(product['unit_price']['amount']) / 100
        quantity = int(product['quantity'])
        name = product['name']
        description = product['description']

        product_message = textwrap.dedent(f"""
        {name.upper()}

        {description}

        {quantity} за ${price * quantity}

        """)
        message += product_message
        total += price * quantity
        keyboard.append([InlineKeyboardButton(f'Убрать из корзины {name}', callback_data=f'{product["id"]}')])

    if not message:
        message = 'Дружище, корзина пуста (ㆆ _ ㆆ)'
    else:
        message += f'ИТОГО: ${total}'

    keyboard.append([InlineKeyboardButton('В меню', callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    return message, reply_markup
