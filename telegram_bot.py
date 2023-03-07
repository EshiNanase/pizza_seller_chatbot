import os
import textwrap
import time

import dotenv
import logging

from enum import Enum, auto
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from functools import partial
from elasticpath import get_access_token, get_product, get_file, add_products_to_cart, get_cart_items, delete_cart_item, create_customer, get_flow_entries
from telegram_send import send_basket, send_menu
from logger import ChatbotLogsHandler
import elasticpath
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)
from geocoder import fetch_coordinates, compare_distance

from pprint import pprint

logger = logging.getLogger(__file__)


class States(Enum):
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_BASKET = auto()
    HANDLE_ADDRESS = auto()
    HANDLE_PAYMENT = auto()
    HANDLE_DELIVERY = auto()


def check_timestamp(client_id, client_secret, access_token):
    if elasticpath.TIMESTAMP <= time.time():
        access_token, timestamp = get_access_token(client_id, client_secret)
        elasticpath.TIMESTAMP = timestamp
    return access_token


def start(update, context, access_token, client_id, client_secret):

    access_token = check_timestamp(client_id, client_secret, access_token)

    message, reply_markup = send_menu(update, access_token)
    context.bot.send_message(text=message, chat_id=update.message.chat_id, reply_markup=reply_markup)
    context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)

    return States.HANDLE_MENU


def get_product_detail(update, context, access_token, client_id, client_secret):
    query = update.callback_query

    access_token = check_timestamp(client_id, client_secret, access_token)

    if 'basket' in query.data:
        cart_items = get_cart_items(access_token, query.message.chat_id)
        message, reply_markup = send_basket(cart_items)

        context.bot.edit_message_text(text=message,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              reply_markup=reply_markup
                              )
        return States.HANDLE_BASKET

    if '#' in query.data:
        message, reply_markup = send_menu(update, access_token)
        context.bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return States.HANDLE_MENU

    product_id = query.data

    product = get_product(access_token, product_id)

    image_id = product['data']['relationships']['main_image']['data']['id']
    image_url = get_file(access_token, image_id)['data']['link']['href']

    description = product['data']['attributes']['description']
    description = description.replace('\n', '')

    name = product['data']['attributes']['name']
    price = product['data']['meta']['display_price']['with_tax']['formatted']

    message = textwrap.dedent(
        fr"""
        {name}

        Цена: {price}

        {description}
        """
    )

    keyboard = [
        [
            InlineKeyboardButton('Положить в корзину', callback_data=f'{product_id}'),
        ],
        [InlineKeyboardButton('Назад', callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_photo(caption=message, photo=image_url, chat_id=query.message.chat_id, reply_markup=reply_markup)
    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    return States.HANDLE_DESCRIPTION


def go_back(update, context, access_token, client_id, client_secret):

    query = update.callback_query

    access_token = check_timestamp(client_id, client_secret, access_token)

    if query.data != 'back':
        product_id = query.data
        add_products_to_cart(access_token, query.message.chat_id, product_id)
        return States.HANDLE_MENU

    message, reply_markup = send_menu(update, access_token)

    context.bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    return States.HANDLE_MENU


def get_basket(update, context, access_token, client_id, client_secret):

    query = update.callback_query
    data = query.data

    access_token = check_timestamp(client_id, client_secret, access_token)

    if data == 'back_to_menu':
        message, reply_markup = send_menu(update, access_token)
        context.bot.edit_message_text(text=message,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              reply_markup=reply_markup
                              )
        return States.HANDLE_MENU

    if data == 'payment':
        message = 'Договорились, отправляй геолокацию или адрес (o･ω･o)'
        context.bot.edit_message_text(text=message,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id
                              )

        return States.HANDLE_ADDRESS

    delete_cart_item(access_token, query.message.chat_id, data)

    cart_items = get_cart_items(access_token, query.message.chat_id)
    message, reply_markup = send_basket(cart_items)

    context.bot.edit_message_text(text=message,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup
                          )
    return States.HANDLE_BASKET


def handle_address(update, context, access_token, client_id, client_secret, yandex_api_key):

    if hasattr(update.message.location, 'latitude'):
        coordinates = (update.message.location.latitude, update.message.location.longitude)
    else:
        longitude, latitude = fetch_coordinates(yandex_api_key, update.message.text)
        coordinates = (latitude, longitude)

    if None in coordinates:
        message = 'Что-то не могу найти такой адрес, отправь еще разок (̿▀̿ ̿Ĺ̯̿̿▀̿ ̿)̄'
        update.message.reply_text(text=message)

        return States.HANDLE_ADDRESS

    access_token = check_timestamp(client_id, client_secret, access_token)

    page = 0
    entries = get_flow_entries(access_token, 'pizza-seller', page)
    all_pizzerias = []
    for entry in entries['data']:
        all_pizzerias.append(
            {
                'distance': compare_distance(coordinates, (entry['latitude'], entry['longitude'])),
                'address': entry['address']
            }
        )
    while page != entries['meta']['page']['total']:
        page += 1
        entries = get_flow_entries(access_token, 'pizza-seller', page)
        for entry in entries['data']:
            all_pizzerias.append(
                {
                    'distance': compare_distance(coordinates, (entry['latitude'], entry['longitude'])),
                    'address': entry['address']
                }
            )
    nearest_one = min(all_pizzerias, key=lambda pizzeria: pizzeria['distance'])
    keyboard = [
        [InlineKeyboardButton('Доставка', callback_data='delivery')],
        [InlineKeyboardButton('Самовывоз', callback_data='pickup')],
        [InlineKeyboardButton('Отправить новый адрес', callback_data='resend_address')]
    ]
    if nearest_one['distance'] <= 0.5:
        message = f'Ты совсем рядышком с ближайшей пиццерией, можем сделать бесплатную доставку ヽ༼ຈل͜ຈ༽ﾉ'
    elif nearest_one['distance'] <= 5:
        message = f'Ближайшая пиццерия находится не совсем рядом, придется оплатить доставку в размере 100 рублей (- ʖ̯-)'
    elif nearest_one['distance'] <= 20:
        message = f'Ой, что-то ты далеко от ближайшей пиццерии, придется оплатить доставку в размере 300 рублей (≧︿≦)'
    else:
        keyboard = [
            [InlineKeyboardButton('Хорошо', callback_data='delivery')],
            [InlineKeyboardButton('Отправить новый адрес', callback_data='resend_address')]
        ]
        message = f'Дичайше извиняемся, но так далеко мы доставить не можем. Как насчеть самовывоза? (ಠ_ಠ)'

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text=message, reply_markup=reply_markup)

    return States.HANDLE_DELIVERY


def handle_delivery(update, context, access_token, client_id, client_secret, yandex_api_key):
    query = update.callback_query

    if 'resend_address' in query.data:
        message = 'Не проблема, отправляй новую геолокацию или адрес (o･ω･o)'
        update.message.reply_text(text=message)

        return States.HANDLE_ADDRESS


def main() -> None:
    dotenv.load_dotenv()

    telegram_token = os.environ['TELEGRAM_TOKEN']
    telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']

    logging.basicConfig(level=logging.WARNING)
    logger.addHandler(ChatbotLogsHandler(telegram_chat_id, telegram_token))

    yandex_api_token = os.environ['YANDEX_API_TOKEN']

    moltin_client_id = os.environ['MOLTIN_CLIENT_ID']
    moltin_secret_key = os.environ['MOLTIN_SECRET_KEY']
    moltin_access_token, timestamp = get_access_token(moltin_client_id, moltin_secret_key)
    elasticpath.TIMESTAMP = timestamp

    start_credentials = partial(start, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_product_detail_credentials = partial(get_product_detail, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    go_back_credentials = partial(go_back, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_basket_credentials = partial(get_basket, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    handle_address_credentials = partial(handle_address, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key, yandex_api_key=yandex_api_token)
    handle_delivery_credentials = partial(handle_delivery, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_credentials)],
        states={
            States.HANDLE_MENU: [
                CallbackQueryHandler(get_product_detail_credentials),
            ],
            States.HANDLE_DESCRIPTION: [
                CallbackQueryHandler(go_back_credentials),
            ],
            States.HANDLE_BASKET: [
                CallbackQueryHandler(get_basket_credentials),
            ],
            States.HANDLE_ADDRESS: [
                MessageHandler(Filters.location, handle_address_credentials),
                MessageHandler(Filters.text, handle_address_credentials),
            ],
            States.HANDLE_DELIVERY: [
                CallbackQueryHandler(handle_delivery_credentials),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        name='bot_conversation',
    )

    updater = Updater(telegram_token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
