from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from elasticpath import get_products
import textwrap
import dotenv
import os

dotenv.load_dotenv()

LOGO = os.environ['LOGO_LINK']


def send_menu(update, access_token):

    query = update.callback_query

    if hasattr(query, 'data') and '#' in query.data:
        page = int(query.data.split('#')[1])
    else:
        page = 0

    pagination_per_page = 5
    products = get_products(access_token)
    pages_count = round(len(products['data'])/pagination_per_page)
    pages = {page: products['data'][page + page*pagination_per_page:pagination_per_page + page + page*pagination_per_page] for page in range(pages_count)}

    keyboard = []
    for product in pages[page]:
        keyboard.append([InlineKeyboardButton(product['attributes']['name'], callback_data=product['id'])])

    if page == 0:
        keyboard.append(
            [
                InlineKeyboardButton('Корзина', callback_data='basket'),
                InlineKeyboardButton('->', callback_data=f'next#{page + 1}')
            ]
        )
    elif page + 1 == pages_count:
        keyboard.append(
            [
                InlineKeyboardButton('<-', callback_data=f'back#{page - 1}'),
                InlineKeyboardButton('Корзина', callback_data='basket')
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton('<-', callback_data=f'back#{page - 1}'),
                InlineKeyboardButton('Корзина', callback_data='basket'),
                InlineKeyboardButton('->', callback_data=f'next#{page + 1}')
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = textwrap.dedent(
        """
        Добро пожаловать в онлайн-пиццерию "Пузана" 
        ヽ༼ ຈل͜ຈ༼ ▀̿̿Ĺ̯̿̿▀̿ ̿༽Ɵ͆ل͜Ɵ͆ ༽ﾉ
        
        Мы продаем только качественную пицу и только за доллары, потому что мы - люди серьезные.
        
        Анекдот:
        Пицца - это круговая диаграмма, показывающая сколько у тебя осталось пиццы.
        """
    )

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

    if not cart_items['data']:
        keyboard.pop(0)

    if not message:
        message = 'Дружище, корзина пуста (ㆆ _ ㆆ)'
    else:
        message += f'ИТОГО: ${total}'

    keyboard.append([InlineKeyboardButton('В меню', callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    return message, reply_markup


def send_invoice(update, context, payload, price, provider_token):
    query = update.callback_query
    chat_id = query.message.chat_id
    title = chat_id
    description = f'Pizza for {chat_id}'
    payload = payload
    currency = "USD"
    prices = [LabeledPrice("USD", price)]

    context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=prices
    )
