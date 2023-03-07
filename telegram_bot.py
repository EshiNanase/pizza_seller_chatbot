import os
import textwrap
import time

import dotenv
import logging

from enum import Enum, auto
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from functools import partial
from elasticpath import get_access_token, get_product, get_file, add_products_to_cart, get_cart_items, delete_cart_item, create_customer
from telegram_send import send_basket, send_menu
from logger import ChatbotLogsHandler
import elasticpath
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

logger = logging.getLogger(__file__)


class States(Enum):
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_BASKET = auto()
    WAITING_EMAIL = auto()


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
        message = 'Отправляй почту, дружище (o･ω･o)'
        context.bot.edit_message_text(text=message,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id
                              )

        return States.WAITING_EMAIL

    delete_cart_item(access_token, query.message.chat_id, data)

    cart_items = get_cart_items(access_token, query.message.chat_id)
    message, reply_markup = send_basket(cart_items)

    context.bot.edit_message_text(text=message,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup
                          )
    return States.HANDLE_BASKET


def wait_for_email(update, context, access_token, client_id, client_secret):

    email = update.message.text
    chat_id = update.message.chat_id

    access_token = check_timestamp(client_id, client_secret, access_token)

    create_customer(access_token, chat_id, email)
    update.message.reply_text(text=f'Спасибо за почту "{email}" (˵ ͡° ͜ʖ ͡°˵)')

    message, reply_markup = send_menu(update, access_token)
    update.message.reply_text(text=message, reply_markup=reply_markup)

    return States.HANDLE_MENU


def main() -> None:
    dotenv.load_dotenv()

    telegram_token = os.environ['TELEGRAM_TOKEN']
    telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']

    logging.basicConfig(level=logging.WARNING)
    logger.addHandler(ChatbotLogsHandler(telegram_chat_id, telegram_token))

    moltin_client_id = os.environ['MOLTIN_CLIENT_ID']
    moltin_secret_key = os.environ['MOLTIN_SECRET_KEY']
    moltin_access_token, timestamp = get_access_token(moltin_client_id, moltin_secret_key)
    elasticpath.TIMESTAMP = timestamp

    start_credentials = partial(start, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_product_detail_credentials = partial(get_product_detail, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    go_back_credentials = partial(go_back, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    get_basket_credentials = partial(get_basket, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)
    wait_for_email_credentials = partial(wait_for_email, access_token=moltin_access_token, client_id=moltin_client_id, client_secret=moltin_secret_key)

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
            States.WAITING_EMAIL: [
                MessageHandler(Filters.text, wait_for_email_credentials),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        name='bot_conversation',
    )

    updater = Updater(telegram_token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("start", start_credentials))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()