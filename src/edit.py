from random import choice

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode
from telegram.ext import CallbackContext

from src.constants import PAGINATION_STEP
from src.db import db_session
from src.db.models.domain import Domain
from src.utils import delete_last_message, build_pagination


@delete_last_message
def edit_menu(_, context: CallbackContext):
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Данные домена', callback_data='edit_domains')],
                                   [InlineKeyboardButton('Очередь', callback_data='edit_queues')],
                                   [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
    return context.bot.send_message(context.user_data['id'], 'Выберите тип объекта для редактирования',
                                    reply_markup=markup), 'edit_menu'


class DomainEdit:
    @staticmethod
    @delete_last_message
    def show_all(_, context: CallbackContext):
        with db_session.create_session() as session:
            data = [(d.url, d.id) for d in session.query(Domain).all()]
        if not context.user_data.get('domain_edit_pagination'):
            context.user_data['domain_edit_pagination'] = 1
        markup, pages_count = build_pagination(
            data, PAGINATION_STEP, context.user_data['domain_edit_pagination'])
        context.user_data['domain_edit_pages_count'] = pages_count
        return (context.bot.send_message(
            context.user_data['id'],
            '<b>Выберите домен</b>\n\n<i>Для выбора страницы в пагинации '
            'также можно отправить её номер</i>',
            reply_markup=markup, parse_mode=ParseMode.HTML),
                'domain_edit.show_all')

    @staticmethod
    def set_next_page(_, context):
        context.user_data['domain_edit_pagination'] += 1
        return DomainEdit.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        context.user_data['domain_edit_pagination'] -= 1
        return DomainEdit.show_all(_, context)

    @staticmethod
    def set_page(update: Update, context: CallbackContext):
        n = int(update.message.text)
        if not(1 <= n <= context.user_data['domain_edit_pages_count']):
            update.message.reply_text('Введён неверный номер страницы')
        else:
            context.user_data['domain_edit_pagination'] = n
        return DomainEdit.show_all(update, context)

    @staticmethod
    @delete_last_message
    def show_domain_properties(_, context: CallbackContext):
        with db_session.create_session() as session:
            domain = session.query(Domain).get(int(context.match.string))
            context.user_data['domain_edit_id'] = domain.id
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(val, callback_data=f'{domain.id} {key}')]
                 for key, val in domain.verbose_names.items()] +
                [[InlineKeyboardButton('Вернуться назад', callback_data='back')]])
            return (context.bot.send_message(
                context.user_data['id'], f'<b>Домен:</b> {domain.url}',
                reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True),
                    'domain_edit.properties')

    @staticmethod
    @delete_last_message
    def edit_property(_, context: CallbackContext):
        print(context.match.string)


class QueueEdit:
    pass