import json
import os

from dotenv import load_dotenv
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackQueryHandler, ConversationHandler)

from src.add import Addition
from src.db import db_session
from src.db.models.state import State
from src.start import menu


def load_states(updater: Updater, conv_handler: ConversationHandler):
    with db_session.create_session() as session:
        for state in session.query(State).all():
            conv_handler._conversations[(state.user_id, state.user_id)] = state.callback
            updater.dispatcher.user_data[state.user_id] = json.loads(state.data)


def main():
    updater = Updater(os.getenv('token'))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', menu)],
        allow_reentry=True,
        states={
            'menu': [CallbackQueryHandler(Addition.ask_url, pattern='add_new_domain')],
            'addition.url': [MessageHandler(Filters.text, Addition.ask_login),
                             CallbackQueryHandler(menu, pattern='back')],
            'addition.login': [MessageHandler(Filters.text, Addition.ask_password),
                               CallbackQueryHandler(Addition.ask_url, pattern='back')],
            'addition.password': [MessageHandler(Filters.text, Addition.ask_api_key),
                                  CallbackQueryHandler(Addition.ask_login, pattern='back')],
            'addition.api_key': [MessageHandler(Filters.text, Addition.finish),
                                 CallbackQueryHandler(Addition.ask_password, pattern='back')]
        },
        fallbacks=[CommandHandler('start', menu),
                   CallbackQueryHandler(menu, pattern='menu')]
    )
    updater.dispatcher.add_handler(conv_handler)
    load_states(updater, conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    load_dotenv()
    db_session.global_init(os.getenv('DATABASE_URL'))
    main()
