import json

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode
from telegram.ext import CallbackContext

from src.constants import QUEUE_LIMIT
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.queue import Queue
from src.general import DomainGeneral, QueueGeneral
from src.utils import delete_last_message


@delete_last_message
def edit_menu(_, context: CallbackContext):
    for key in 'domain_pagination', 'queue_pagination':
        if context.user_data.get(key):
            context.user_data.pop(key)
    with db_session.create_session() as session:
        if session.query(Queue).first():
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='edit_domains')],
                                           [InlineKeyboardButton('Очереди', callback_data='edit_queues')],
                                           [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
        else:
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('Домены', callback_data='edit_domains')],
                                           [InlineKeyboardButton('Вернуться назад', callback_data='back')]])
    return context.bot.send_message(context.user_data['id'], 'Выберите тип объекта для редактирования',
                                    reply_markup=markup), 'edit_menu'


class DomainEdit:
    @staticmethod
    @delete_last_message
    def show_all(_, context: CallbackContext):
        args, kwargs = DomainGeneral.show_all(_, context)
        args[1] = args[1] % 'для редактирования'
        return context.bot.send_message(*args, **kwargs), 'domain_edit.show_all'

    @staticmethod
    @delete_last_message
    def show_domain_properties(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(val, callback_data=f'{domain.id} {key}')]
                 for key, val in domain.verbose_names.items()] +
                [[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                  InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
            return (context.bot.send_message(
                context.user_data['id'], f'<b>Домен:</b> {domain.url}',
                reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True),
                    'domain_edit.properties')

    @staticmethod
    @delete_last_message
    def ask_to_edit_property(_, context: CallbackContext):
        key = context.match.string.split()[-1]
        context.user_data['domain_key_to_change'] = key
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            return (context.bot.send_message(context.user_data['id'],
                                             f'На что Вы хотите заменить <b>{domain.verbose_names[key]}</b>?\n\n'
                                             f'<b>Текущее значение:</b> {getattr(domain, key)}',
                                             reply_markup=markup, parse_mode=ParseMode.HTML,
                                             disable_web_page_preview=True),
                    'domain_edit.ask_to_edit_property')

    @staticmethod
    @delete_last_message
    def edit_property(update: Update, context: CallbackContext):
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            setattr(domain, context.user_data['domain_key_to_change'], update.message.text)
            session.add(domain)
            session.commit()
            context.bot.send_message(
                context.user_data['id'],
                f'Переменная <b>{domain.verbose_names[context.user_data.pop("domain_key_to_change")]}</b> '
                f'домена {domain.url} была обновлена',
                parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return DomainEdit.show_domain_properties(update, context)


class QueueEdit:
    @staticmethod
    @delete_last_message
    def show_all_domains(_, context: CallbackContext):
        args, kwargs = DomainGeneral.show_all(_, context)
        args[1] = args[1] % 'для редактирования'
        return context.bot.send_message(*args, **kwargs), 'queue_edit.show_all_domains'

    @staticmethod
    @delete_last_message
    def show_all(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        args, kwargs = QueueGeneral.show_all(_, context)
        args[1] = args[1] % 'для редактирования'
        return context.bot.send_message(*args, **kwargs), 'queue_edit.show_all'

    @staticmethod
    @delete_last_message
    def ask_urls(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['queue_id'] = int(context.match.string)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        if str(QUEUE_LIMIT)[-1] == '1' and QUEUE_LIMIT != 11:
            phrase = 'адрес'
        elif any(map(lambda x: str(QUEUE_LIMIT)[-1] == x, '234')) and not (12 <= QUEUE_LIMIT <= 14):
            phrase = 'адреса'
        else:
            phrase = 'адресов'
        return (context.bot.send_message(
            context.user_data['id'],
            f'Введите новые адреса страниц текстовым сообщением или файлом '
            f'(максимальное количество: {QUEUE_LIMIT} {phrase})',
            reply_markup=markup), 'queue_edit.ask_urls')

    @staticmethod
    @delete_last_message
    def correct_urls(update: Update, context: CallbackContext):
        if update.message.document:
            try:
                raw_urls = update.message.document.get_file().download_as_bytearray().decode('utf-8').split('\n')
            except UnicodeDecodeError:
                context.bot.send_message(context.user_data['id'],
                                         'У файла неверный формат, или он повреждён')
                return QueueEdit.ask_urls(update, context)
        else:
            raw_urls = update.message.text.split('\n')
        with db_session.create_session() as session:
            queue = session.query(Queue).get(context.user_data['queue_id'])
            if not queue:
                context.bot.send_message(context.user_data['id'],
                                         'Очередь уже была отправлена и не подлежит редактированию')
                return QueueEdit.show_all(update, context)
            urls = []
            for u in raw_urls:
                if u not in urls and u.startswith('http') and queue.domain.url in u:
                    urls.append(u)
            if not urls:
                context.bot.send_message(context.user_data['id'], 'Ни один URL не прошёл фильтрацию!')
                return QueueEdit.ask_urls(update, context)
            if len(urls) > 200:
                context.bot.send_message(context.user_data['id'], 'Новые данные должны быть менее 200 адресов')
                return QueueEdit.ask_urls(update, context)
            if queue.data:
                prev_data = json.loads(queue.data)[1:]
                prev_urls = [x[0] for x in prev_data]
                offset = 0
                for i in range(len(urls)):
                    if urls[i] in prev_urls:
                        urls.pop(i - offset)
                        offset += 1
            queue.urls = ','.join(urls)
            queue.start_length = len(urls)
            session.add(queue)
            session.commit()
            context.bot.send_message(context.user_data['id'],
                                     f'Данные очереди <b>#{queue.id}</b> домена {queue.domain.url} '
                                     'были успешно обновлены!', parse_mode=ParseMode.HTML)
            return QueueEdit.show_all(update, context)