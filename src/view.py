from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CallbackContext

from src.constants import MESSAGE_MAX_LENGTH
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.queue import Queue
from src.general import DomainGeneral, QueueGeneral
from src.utils import delete_last_message


@delete_last_message
def view_menu(_, context: CallbackContext):
    for key in 'domain_pagination', 'queue_pagination':
        if context.user_data.get(key):
            context.user_data.pop(key)
    with db_session.create_session() as session:
        if session.query(Queue).first():
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='view_domains')],
                                           [InlineKeyboardButton('Очереди', callback_data='view_queues')],
                                           [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
        else:
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='view_domains')],
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

    @staticmethod
    def set_next_page(_, context):
        DomainGeneral.set_next_page(_, context)
        return DomainView.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        DomainGeneral.set_previous_page(_, context)
        return DomainView.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        DomainGeneral.set_page(update, context)
        return DomainView.show_all(update, context)


class QueueView:
    @staticmethod
    @delete_last_message
    def show_all_domains(_, context: CallbackContext):
        args, kwargs = DomainGeneral.show_all(_, context)
        args[1] = args[1] % 'для просмотра'
        return context.bot.send_message(*args, **kwargs), 'queue_view.show_all_domains'

    @staticmethod
    @delete_last_message
    def show_all(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        args, kwargs = QueueGeneral.show_all(_, context)
        args[1] = args[1] % 'для просмотра'
        return context.bot.send_message(*args, **kwargs), 'queue_view.show_all'

    @staticmethod
    @delete_last_message
    def show_info(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['queue_id'] = int(context.match.string)
        with db_session.create_session() as session:
            queue = session.query(Queue).get(context.user_data['queue_id'])
            if not queue:
                context.bot.send_message(context.user_data['id'],
                                         'Очередь уже была отправлена и не подлежит просмотру')
                return QueueView.show_all(_, context)
            number = queue.number
            start_length = queue.start_length
            domain_url = queue.domain.url
            method = queue.method
            is_broken = queue.is_broken
            urls = queue.urls.split(',')
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        first = True
        msg = None
        messages_to_delete = []
        start_text = (f'Очередь <b>#{number}</b> домена {domain_url}\n\n<b>Количество необработанных адресов:</b> '
                      f'{len(urls)} из {start_length}\n'
                      f'<b>Метод:</b> {method}\n'
                      f'<b>Остановлена ли из-за ошибки:</b> {"Да" if is_broken else "Нет"}')
        if not urls:
            return (context.bot.send_message(
                context.user_data['id'], start_text,
                parse_mode=ParseMode.HTML, disable_web_page_preview=True), 'queue_info.info')
        while urls:
            text = (start_text + f'\n<b>Адреса:</b>\n' if first else '')
            while len(text) < MESSAGE_MAX_LENGTH and urls:
                text += urls.pop(0) + '\n'
            msg = context.bot.send_message(context.user_data['id'], text,
                                           parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            messages_to_delete.append(msg.message_id)
            if first:
                first = False
        msg.edit_reply_markup(markup)
        context.user_data['messages_to_delete'] = messages_to_delete[:-1]
        return msg, 'queue_view.info'

    @staticmethod
    def set_next_page_domain(_, context):
        DomainGeneral.set_next_page(_, context)
        return QueueView.show_all_domains(_, context)

    @staticmethod
    def set_previous_page_domain(_, context):
        DomainGeneral.set_previous_page(_, context)
        return QueueView.show_all_domains(_, context)

    @staticmethod
    def set_page_domain(update, context):
        DomainGeneral.set_page(update, context)
        return QueueView.show_all_domains(update, context)

    @staticmethod
    def set_next_page(_, context):
        QueueGeneral.set_next_page(_, context)
        return QueueView.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        QueueGeneral.set_previous_page(_, context)
        return QueueView.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        QueueGeneral.set_page(update, context)
        return QueueView.show_all(update, context)
