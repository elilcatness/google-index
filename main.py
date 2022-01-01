import json
import os

from dotenv import load_dotenv
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackQueryHandler, ConversationHandler)

from src.add import Addition
from src.db import db_session
from src.db.models.state import State
from src.edit import DomainEdit, edit_menu
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
            'menu': [CallbackQueryHandler(Addition.ask_url, pattern='add_new_domain'),
                     CallbackQueryHandler(edit_menu, pattern='edit_menu')],
            'addition.url': [MessageHandler(Filters.text, Addition.ask_login),
                             CallbackQueryHandler(menu, pattern='back')],
            'addition.login': [MessageHandler(Filters.text, Addition.ask_password),
                               CallbackQueryHandler(Addition.ask_url, pattern='back')],
            'addition.password': [MessageHandler(Filters.text, Addition.ask_api_key),
                                  CallbackQueryHandler(Addition.ask_login, pattern='back')],
            'addition.api_key': [MessageHandler(Filters.text, Addition.finish),
                                 CallbackQueryHandler(Addition.ask_password, pattern='back')],
            'edit_menu': [CallbackQueryHandler(DomainEdit.show_all, pattern='edit_domains'),
                          CallbackQueryHandler(menu, pattern='back')],
            'domain_edit.show_all': [CallbackQueryHandler(DomainEdit.show_domain_properties, pattern=r'[0-9]+'),
                                     CallbackQueryHandler(DomainEdit.set_next_page, pattern='next_page'),
                                     CallbackQueryHandler(DomainEdit.show_all, pattern='refresh'),
                                     CallbackQueryHandler(DomainEdit.set_previous_page, pattern='prev_page'),
                                     MessageHandler(Filters.regex(r'[0-9]+'), DomainEdit.set_page),
                                     CallbackQueryHandler(edit_menu, pattern='back')],
            'domain_edit.properties': [CallbackQueryHandler(DomainEdit.edit_property, pattern=r'[0-9]+ .+'),
                                       CallbackQueryHandler(DomainEdit.show_all, pattern='back')]
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
