from telegram import ParseMode

from src.constants import PAGINATION_STEP
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.queue import Queue
from src.utils import build_pagination


class DomainGeneral:
    @staticmethod
    def show_all(_, context, with_main_menu: bool = True):
        with db_session.create_session() as session:
            data = [(d.url, d.id) for d in
                    session.query(Domain).filter(Domain.user_id == context.user_data['id']).all()]
        if not context.user_data.get('domain_pagination'):
            context.user_data['domain_pagination'] = 1
        markup, pages_count = build_pagination(
            data, PAGINATION_STEP, context.user_data['domain_pagination'],
            with_main_menu)
        context.user_data['domain_pages_count'] = pages_count
        return ([context.user_data['id'], '<b>Выберите домен</b> %s\n\n<i>Для выбора страницы в пагинации '
                                          'также можно отправить её номер</i>'],
                {'reply_markup': markup, 'parse_mode': ParseMode.HTML})

    @staticmethod
    def set_next_page(_, context):
        context.user_data['domain_pagination'] += 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        context.user_data['domain_pagination'] -= 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        n = int(update.message.text)
        if not (1 <= n <= context.user_data['domain_pages_count']):
            update.message.reply_text('Введён неверный номер страницы')
        else:
            context.user_data['domain_pagination'] = n
        return DomainGeneral.show_all(update, context)


class QueueGeneral:
    @staticmethod
    def show_all(_, context, with_main_menu: bool = True):
        with db_session.create_session() as session:
            data = [(f'#{q.number}', q.id) for q in
                    session.query(Queue).filter(
                        (Queue.user_id == context.user_data['id']) &
                        (Queue.domain_id == context.user_data['domain_id'])).all()]
            print(f'{data=}')
        if not context.user_data.get('queue_pagination'):
            context.user_data['queue_pagination'] = 1
        markup, pages_count = build_pagination(
            data, PAGINATION_STEP, context.user_data['queue_pagination'],
            with_main_menu)
        context.user_data['queue_pages_count'] = pages_count
        return ([context.user_data['id'], '<b>Выберите очередь</b> %s\n\n<i>Для выбора страницы в пагинации '
                                          'также можно отправить её номер</i>'],
                {'reply_markup': markup, 'parse_mode': ParseMode.HTML})

    @staticmethod
    def set_next_page(_, context):
        context.user_data['queue_pagination'] += 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        context.user_data['queue_pagination'] -= 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        n = int(update.message.text)
        if not (1 <= n <= context.user_data['queue_pages_count']):
            update.message.reply_text('Введён неверный номер страницы')
        else:
            context.user_data['queue_pagination'] = n
        return DomainGeneral.show_all(update, context)