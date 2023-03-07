# Пиццерия "Пузана"

Телеграм бот для продажи продукции "Пузаны"
Каталог из 28 товаров и 78 пиццерий для доставки. После оплаты с помощью invoice'а, доставщику отправляется ваше местоположение, и в течение часа он будет у вас! Если нет, то вернем деньги с:

![](https://github.com/EshiNanase/fish_seller_chatbot/blob/main/example.gif)

[Бот на практике](https://t.me/ultimate_pizza_seller_chatbot)

## Виртуальное окружение

```
python==3.9
```
## Установка

Во-первых, необходимо клонировать репозиторий:

```
git clone https://github.com/EshiNanase/fish_seller_chatbot.git
```
Во-вторых, необходимо перейти в терминал, активировать виртуальное окружение и установить необходимые библиотеки:

```
pip install -r requirements.txt
```
В-третьих, необходимо создать магазин на elasticpath.com:
```
https://euwest.cm.elasticpath.com/
```
В-четвертых, в магазине должно быть:
```
Flow со slug'ом "pizza-seller": адреса магазинов с полями address, alias, longitude, latitude (необходимо заполнить)
Flow со slug'ом "pizza-customer-addresse": адреса клиентов с полями longitude, latitude (оставьте пустым)
Products на elasticpath.com/products page: выставьте у них цену и поставьте статус live
Hierarchy на .elasticpath.com/configurations: просто создайте один Node и добавьте в него все созданные товары
Price Book на elasticpath.com/pricebooks: добавьте в него все созданные товары и выставьте им цены
Catalog на elasticpath.com/catalogs: добавьте созданные Hierarchy, Price Book и опубликуйте каталог
## Переменные окружения

Необходимо создать файл .env и указать в нем следующие переменные:

```
MOLTIN_CLIENT_ID=8aSlzNH3k8pUBm1l2V562lta3pN4hicrb8GFEUgZfM
MOLTIN_SECRET_KEY=vckoSaEQpmJrwkOYg8fKK62tvnCwTOQ7bfVrZ5tuYm
TELEGRAM_TOKEN = токен вашего телеграм бота, создать и получить здесь https://t.me/BotFather
TELEGRAM_CHAT_ID = необходим для логера, получить здесь https://t.me/userinfobot
PROVIDER_TOKEN = токен банка, через который вы собираетесь принимать платежи, получить здесь https://core.telegram.org/bots/payments
YANDEX_API_TOKEN = токен яндекс геокодера, необходим для вычисления расстояния между клиентом и ближайшим рестораном, получить здесь https://developer.tech.yandex.ru/services
LOGO_LINK = ссылка на ваш логотип, например, https://ibb.co/qsv0R2W
```
## Запуск

Необходимо зайти в терминал, активировать виртуальное окружение и написать:

```
python telegram_bot.py
```