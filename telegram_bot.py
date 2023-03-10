import os
import textwrap
import time

import dotenv
import logging

from enum import Enum, auto

import telegram
from telegram.ext import CallbackQueryHandler, PreCheckoutQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from functools import partial
from elasticpath import get_access_token, get_product, get_file, add_products_to_cart, get_cart_items, delete_cart_item, get_flow_entries, create_flow_entry
from telegram_send import send_basket, send_menu, send_invoice
import telegram_send
from logger import ChatbotLogsHandler
import elasticpath
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)
from geocoder import fetch_coordinates, compare_distance
import json


logger = logging.getLogger(__file__)


class States(Enum):
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_BASKET = auto()
    HANDLE_ADDRESS = auto()
    HANDLE_PAYMENT = auto()
    HANDLE_DELIVERY = auto()
    WAIT_FOR_PAYMENT = auto()


def check_timestamp(client_id, client_secret, access_token):
    if elasticpath.TIMESTAMP <= time.time():
        access_token, timestamp = get_access_token(client_id, client_secret)
        elasticpath.TIMESTAMP = timestamp
    return access_token


def start(update, context, access_token, client_id, client_secret):

    access_token = check_timestamp(client_id, client_secret, access_token)

    message, reply_markup = send_menu(update, access_token)
    context.bot.send_photo(caption=message, photo=telegram_send.LOGO, chat_id=update.message.chat_id, reply_markup=reply_markup)

    return States.HANDLE_MENU


def get_product_detail(update, context, access_token, client_id, client_secret):
    query = update.callback_query

    access_token = check_timestamp(client_id, client_secret, access_token)

    if 'basket' in query.data:
        cart_items = get_cart_items(access_token, query.message.chat_id)
        message, reply_markup = send_basket(cart_items)

        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        context.bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return States.HANDLE_BASKET

    if '#' in query.data:
        message, reply_markup = send_menu(update, access_token)
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        context.bot.send_photo(caption=message, photo=telegram_send.LOGO, chat_id=query.message.chat_id, reply_markup=reply_markup)
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

        ????????: {price}

        {description}
        """
    )

    keyboard = [
        [
            InlineKeyboardButton('???????????????? ?? ??????????????', callback_data=f'{product_id}'),
        ],
        [InlineKeyboardButton('??????????', callback_data='back')]
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

    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    context.bot.send_photo(caption=message, photo=telegram_send.LOGO, chat_id=query.message.chat_id, reply_markup=reply_markup)

    return States.HANDLE_MENU


def get_basket(update, context, access_token, client_id, client_secret):

    query = update.callback_query
    data = query.data

    access_token = check_timestamp(client_id, client_secret, access_token)

    if data == 'back_to_menu':
        message, reply_markup = send_menu(update, access_token)
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        context.bot.send_photo(caption=message, photo=telegram_send.LOGO, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return States.HANDLE_MENU

    if data == 'payment':
        message = '????????????????????????, ?????????????????? ???????????????????? ?????? ?????????? (o????????o)'
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
        message = '??????-???? ???? ???????? ?????????? ?????????? ??????????, ?????????????? ?????? ?????????? (????????????????????????? ??)??'
        update.message.reply_text(text=message)

        return States.HANDLE_ADDRESS

    access_token = check_timestamp(client_id, client_secret, access_token)

    page = 0
    entries = get_flow_entries(access_token, 'pizza-seller', page)
    all_pizzerias = []
    while page != entries['meta']['page']['total']:
        for entry in entries['data']:
            all_pizzerias.append(
                {
                    'distance': compare_distance(coordinates, (entry['latitude'], entry['longitude'])),
                    'address': entry['address'],
                    'coordinates': {
                        'latitude': entry['latitude'],
                        'longitude': entry['longitude']
                    },
                    'delivery_guy': entry['delivery_guy']
                }
            )
        page += 1
        entries = get_flow_entries(access_token, 'pizza-seller', page)
    nearest_one = min(all_pizzerias, key=lambda pizzeria: pizzeria['distance'])

    keyboard = [
        [InlineKeyboardButton('????????????????', callback_data='delivery')],
        [InlineKeyboardButton('??????????????????', callback_data='pickup')],
        [InlineKeyboardButton('?????????????????? ?????????? ??????????', callback_data='resend_address')]
    ]
    if nearest_one['distance'] <= 0.5:
        message = f'???? ???????????? ???????????????? ?? ?????????????????? ??????????????????, ?????????? ?????????????? ???????????????????? ???????????????? ??????????????????????'
    elif nearest_one['distance'] <= 5:
        message = f'?????????????????? ???????????????? ?????????????????? ???? ???????????? ??????????, ???????????????? ???????????????? ???????????????? ?? ?????????????? 100 ???????????? (- ????-)'
    elif nearest_one['distance'] <= 20:
        message = f'????, ??????-???? ???? ???????????? ???? ?????????????????? ????????????????, ???????????????? ???????????????? ???????????????? ?? ?????????????? 300 ???????????? (?????????)'
    else:
        keyboard = [
            [InlineKeyboardButton('????????????', callback_data='pickup')],
            [InlineKeyboardButton('?????????????????? ?????????? ??????????', callback_data='resend_address')]
        ]
        message = f'?????????????? ????????????????????, ???? ?????? ???????????? ???? ?????????????????? ???? ??????????. ?????? ???????????? ????????????????????? (???_???)'

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['address'] = nearest_one["address"]
    context.user_data['coordinates'] = nearest_one["coordinates"]
    context.user_data['delivery_guy'] = nearest_one["delivery_guy"]
    context.bot.send_message(text=message, chat_id=update.message.chat_id, reply_markup=reply_markup)

    return States.HANDLE_DELIVERY


def handle_delivery(update, context, access_token, client_id, client_secret, provider_token):
    query = update.callback_query

    access_token = check_timestamp(client_id, client_secret, access_token)

    if 'resend_address' in query.data:
        message = '???? ????????????????, ?????????????????? ?????????? ???????????????????? ?????? ?????????? (o????????o)'
        context.bot.edit_message_text(text=message,
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id
                                      )

        return States.HANDLE_ADDRESS

    elif 'pickup' in query.data:
        address = context.user_data['address']
        message = textwrap.dedent(
            f"""
            ??????????????????, ???????? ???????? ???? ???????????? <b>{address}</b> (?????????????????????)???
            
            ???????? ?????? ??????????????????????, ???? ?????????????? ?????? ???? ?????????????? /start c:
            """
        )
        context.bot.edit_message_text(text=message,
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      parse_mode=telegram.ParseMode.HTML
                                      )

    elif 'delivery' in query.data:
        cart_items = get_cart_items(access_token, query.message.chat_id)

        price = cart_items['meta']['display_price']['with_tax']['amount']
        payload = {
            'coordinates': context.user_data['coordinates'],
            'delivery_guy': context.user_data['delivery_guy'],
            'chat_id': query.message.chat_id,
        }

        send_invoice(update, context, payload, price, provider_token)
        message = '?? ?????????????????????? ???????? ????????????! ???????? ???? ??????????????????, ???? ???????????? /start'

        context.bot.edit_message_text(text=message,
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      parse_mode=telegram.ParseMode.HTML
                                      )

        return States.WAIT_FOR_PAYMENT


def notice_after_hour(context):
    message = textwrap.dedent(
        """
        ?????????????????? ????????????????! ???\(^o^)/???
        
        ???????? ?????????????? ???????????????????? (?????????? ???? ??????????????), ???? ???????????? ???????? ???? ?????????? alksndr.zln@gmail.com, ?? ???? ???????????? ??????????????????!
        ???????????? ???????????????? :(
        """
    )
    context.bot.send_message(text=message, chat_id=context.job.context)


def successful_payment(update, context, access_token, client_id, client_secret, job_queue):

    invoice_data = context.user_data
    coordinates = invoice_data['coordinates']
    delivery_guy = invoice_data['delivery_guy']
    chat_id = update.message.chat_id

    access_token = check_timestamp(client_id, client_secret, access_token)

    message = textwrap.dedent(
        """
        ??????????????????, ???????????? ?????????? ??????????! ???????? ?????????? ?????? ?????????? ???? ?????????? ????????????????????, ???? ?????? ???? ?????? ???????? [????$????(???? ???? ???? ????????)????$????]
        
        ???????? ???????? ?????????? ???? ?????????????? /start :??
        """
    )
    context.bot.send_message(text=message,
                             chat_id=chat_id,
                             parse_mode=telegram.ParseMode.HTML
                             )

    create_flow_entry(access_token, 'pizzeria-customer-addresses', coordinates)
    cart_items = get_cart_items(access_token, chat_id)

    delivery_guy_message, reply_markup = send_basket(cart_items)
    context.bot.send_message(text=delivery_guy_message, chat_id=delivery_guy)
    context.bot.send_location(latitude=coordinates['latitude'], longitude=coordinates['longitude'],
                              chat_id=delivery_guy)

    job_queue.run_once(notice_after_hour, 3600, context=chat_id)


def precheckout_callback(update, context) -> None:

    query = update.pre_checkout_query
    invoice_data = json.loads(query.invoice_payload)
    if 'delivery_guy' in invoice_data and 'chat_id' in invoice_data and 'coordinates' in invoice_data:
        query.answer(ok=True)
    else:
        query.answer(ok=False, error_message="Something went wrong...")


def main() -> None:
    dotenv.load_dotenv()

    telegram_token = os.environ['TELEGRAM_TOKEN']
    telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']

    logging.basicConfig(level=logging.WARNING)
    logger.addHandler(ChatbotLogsHandler(telegram_chat_id, telegram_token))

    yandex_api_token = os.environ['YANDEX_API_TOKEN']

    provider_token = os.environ['PROVIDER_TOKEN']

    moltin_client_id = os.environ['MOLTIN_CLIENT_ID']
    moltin_secret_key = os.environ['MOLTIN_SECRET_KEY']
    moltin_access_token, timestamp = get_access_token(moltin_client_id, moltin_secret_key)
    elasticpath.TIMESTAMP = timestamp

    updater = Updater(telegram_token)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    start_credentials = partial(start, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_product_detail_credentials = partial(get_product_detail, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    go_back_credentials = partial(go_back, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_basket_credentials = partial(get_basket, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    handle_address_credentials = partial(handle_address, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key, yandex_api_key=yandex_api_token)
    handle_delivery_credentials = partial(handle_delivery, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key, provider_token=provider_token)
    successful_payment_credentials = partial(successful_payment, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key, job_queue=job_queue)

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
            States.WAIT_FOR_PAYMENT: [
                MessageHandler(Filters.successful_payment, successful_payment_credentials),
            ],
        },
        fallbacks=[],
        name='bot_conversation',
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("start", start_credentials))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback),)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
