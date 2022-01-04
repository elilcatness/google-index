from telegram import ParseMode

from src.constants import PAGINATION_STEP
from src.db import db_session
from src.db.models.domain import Domain
from src.utils import build_pagination


class DomainGeneral:
    @staticmethod
    def show_all(_, context, with_main_menu: bool = True):
        with db_session.create_session() as session:
            data = [(d.url, d.id) for d in session.query(Domain).filter(Domain.user_id == context.user_data['id']).all()]
        if not context.user_data.get('domain_edit_pagination'):
            context.user_data['domain_edit_pagination'] = 1
        markup, pages_count = build_pagination(
            data, PAGINATION_STEP, context.user_data['domain_edit_pagination'],
            with_main_menu)
        context.user_data['domain_edit_pages_count'] = pages_count
        return ([context.user_data['id'], '<b>Выберите домен</b> %s\n\n<i>Для выбора страницы в пагинации '
                                          'также можно отправить её номер</i>'],
                {'reply_markup': markup, 'parse_mode': ParseMode.HTML})

    @staticmethod
    def set_next_page(_, context):
        context.user_data['domain_edit_pagination'] += 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        context.user_data['domain_edit_pagination'] -= 1
        return DomainGeneral.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        n = int(update.message.text)
        if not (1 <= n <= context.user_data['domain_edit_pages_count']):
            update.message.reply_text('Введён неверный номер страницы')
        else:
            context.user_data['domain_edit_pagination'] = n
        return DomainGeneral.show_all(update, context)
