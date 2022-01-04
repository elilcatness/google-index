from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.general import DomainGeneral
from src.utils import delete_last_message


@delete_last_message
def delete_menu(_, context: CallbackContext):
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='domains')],
                                   [InlineKeyboardButton('Очереди', callback_data='queues')],
                                   [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
    return (context.bot.send_message(context.user_data['id'], 'Выберите тип объекта для удаления',
                                     reply_markup=markup), 'delete_menu')


class DomainDelete:
    @staticmethod
    @delete_last_message
    def show_all(_, context):
        args, kwargs = DomainGeneral.show_all(_, context)
        args[1] = args[1] % 'для удаления'
        return context.bot.send_message(*args, **kwargs), 'domain_delete.show_all'

    @staticmethod
    @delete_last_message
    def confirm(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Удалить', callback_data='delete')],
                                       [InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            return (context.bot.send_message(context.user_data['id'],
                                             f'Вы уверены, что хотите удалить из списка домен {domain.url}?',
                                             reply_markup=markup, disable_web_page_preview=True),
                    'domain_delete.confirm')

    @staticmethod
    @delete_last_message
    def delete(_, context: CallbackContext):
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            url = domain.url
            session.delete(domain)
            session.commit()
        context.bot.send_message(context.user_data['id'], f'Домен {url} был успешно удалён',
                                 disable_web_page_preview=True)
        return DomainDelete.show_all(_, context)


class QueueDelete:
    pass
