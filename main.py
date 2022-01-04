from datetime import time
import json
import os
from pytz import utc
from dotenv import load_dotenv
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackQueryHandler, ConversationHandler, Dispatcher)

from src.add import Addition
from src.db import db_session
from src.db.models.state import State
from src.delete import DomainDelete, delete_menu
from src.edit import DomainEdit, edit_menu
from src.general import DomainGeneral
from src.index import DomainIndex
from src.start import menu
from src.view import view_menu, DomainView
from src.utils import refresh_limit


def load_states(updater: Updater, conv_handler: ConversationHandler):
    with db_session.create_session() as session:
        for state in session.query(State).all():
            conv_handler._conversations[(state.user_id, state.user_id)] = state.callback
            updater.dispatcher.user_data[state.user_id] = json.loads(state.data)
            t = time(3, tzinfo=utc)
            print(f'{t=}')
            for job in updater.dispatcher.job_queue.get_jobs_by_name(str(state.user_id)):
                job.schedule_removal()
            updater.dispatcher.job_queue.run_daily(refresh_limit, t, name=str(state.user_id))


def main():
    updater = Updater(os.getenv('token'))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', menu)],
        allow_reentry=True,
        states={
            'menu': [CallbackQueryHandler(Addition.ask_url, pattern='add_new_domain'),
                     CallbackQueryHandler(edit_menu, pattern='edit_menu'),
                     CallbackQueryHandler(delete_menu, pattern='delete_menu'),
                     CallbackQueryHandler(view_menu, pattern='view_menu'),
                     CallbackQueryHandler(DomainIndex.show_all, pattern='index_menu')],
            'addition.url': [MessageHandler(Filters.text, Addition.ask_login),
                             CallbackQueryHandler(menu, pattern='back')],
            'addition.login': [MessageHandler(Filters.text, Addition.ask_password),
                               CallbackQueryHandler(Addition.ask_url, pattern='back')],
            'addition.password': [MessageHandler(Filters.text, Addition.ask_json_keys),
                                  CallbackQueryHandler(Addition.ask_login, pattern='back')],
            'addition.json_keys': [MessageHandler(Filters.text | Filters.document, Addition.finish),
                                   CallbackQueryHandler(Addition.ask_password, pattern='back')],
            'edit_menu': [CallbackQueryHandler(DomainEdit.show_all, pattern='edit_domains'),
                          CallbackQueryHandler(menu, pattern='back')],
            'domain_edit.show_all': [CallbackQueryHandler(DomainEdit.show_domain_properties, pattern=r'[0-9]+'),
                                     CallbackQueryHandler(DomainGeneral.set_next_page, pattern='next_page'),
                                     CallbackQueryHandler(DomainEdit.show_all, pattern='refresh'),
                                     CallbackQueryHandler(DomainGeneral.set_previous_page, pattern='prev_page'),
                                     MessageHandler(Filters.regex(r'[0-9]+'), DomainGeneral.set_page),
                                     CallbackQueryHandler(edit_menu, pattern='back')],
            'domain_edit.properties': [CallbackQueryHandler(DomainEdit.ask_to_edit_property,
                                                            pattern=r'[0-9]+ .+'),
                                       CallbackQueryHandler(DomainEdit.show_all, pattern='back')],
            'domain_edit.ask_to_edit_property': [MessageHandler(Filters.text, DomainEdit.edit_property),
                                                 CallbackQueryHandler(DomainEdit.show_domain_properties,
                                                                      pattern='back')],
            'delete_menu': [CallbackQueryHandler(DomainDelete.show_all, pattern='domains'),
                            CallbackQueryHandler(menu, pattern='back')],
            'domain_delete.show_all': [CallbackQueryHandler(DomainDelete.confirm, pattern=r'[0-9]+'),
                                       CallbackQueryHandler(DomainGeneral.set_next_page, pattern='next_page'),
                                       CallbackQueryHandler(DomainEdit.show_all, pattern='refresh'),
                                       CallbackQueryHandler(DomainGeneral.set_previous_page, pattern='prev_page'),
                                       MessageHandler(Filters.regex(r'[0-9]+'), DomainGeneral.set_page),
                                       CallbackQueryHandler(edit_menu, pattern='back')],
            'domain_delete.confirm': [CallbackQueryHandler(DomainDelete.delete, pattern='delete'),
                                      CallbackQueryHandler(DomainDelete.show_all, pattern='back')],
            'view_menu': [CallbackQueryHandler(DomainView.show_all, pattern='domains'),
                          CallbackQueryHandler(menu, pattern='back')],
            'domain_view.show_all': [CallbackQueryHandler(DomainView.show_info, pattern=r'[0-9]+'),
                                     CallbackQueryHandler(view_menu, pattern='back')],
            'domain_view.info': [CallbackQueryHandler(DomainView.show_all, pattern='back')],
            'domain_index.show_all': [CallbackQueryHandler(DomainIndex.ask_mode, pattern=r'[0-9]+'),
                                      CallbackQueryHandler(menu, pattern='back')],
            'domain_index.ask_mode': [CallbackQueryHandler(DomainIndex.get_queue, pattern='[1-2]'),
                                      CallbackQueryHandler(DomainIndex.show_all, pattern='back')],
            'domain_index.get_queue': [MessageHandler(Filters.regex(r'^https?://*'), DomainIndex.correct_urls)],
            'domain_index.correct_urls': [CallbackQueryHandler(DomainIndex.create_queue, pattern='proceed'),
                                          CallbackQueryHandler(DomainIndex.get_queue, pattern='back')]
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
