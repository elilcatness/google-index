from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.general import DomainGeneral
from src.utils import delete_last_message


@delete_last_message
def view_menu(_, context: CallbackContext):
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='domains')],
                                   [InlineKeyboardButton('Очереди', callback_data='queues')],
                                   [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
    return (context.bot.send_message(context.user_data['id'], 'Выберите тип объекта для просмотра',
                                     reply_markup=markup), 'view_menu')


class DomainView:
    @staticmethod
    @delete_last_message
    def show_all(_, context):
        args, kwargs = DomainGeneral.show_all(_, context)
        args[1] = args[1] % 'для просмотра'
        return context.bot.send_message(*args, **kwargs), 'domain_view.show_all'

    @staticmethod
    @delete_last_message
    def show_info(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            return (context.bot.send_message(
                context.user_data['id'],
                f'<b>Домен:</b> {domain.url}\n\n' +
                '\n'.join([f'<b>{val}:</b> {getattr(domain, key)}' for key, val in domain.verbose_names.items()]),
                reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True), 'domain_view.info')
