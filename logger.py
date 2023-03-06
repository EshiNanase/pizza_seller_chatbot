import logging
import telegram


class ChatbotLogsHandler(logging.Handler):

    def __init__(self, telegram_chat_id, token):
        super(ChatbotLogsHandler, self).__init__()
        self.bot = telegram.Bot(token=token)
        self.chat_id = telegram_chat_id

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)

