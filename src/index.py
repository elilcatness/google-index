import csv
import os
import time
from datetime import datetime

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode, Document
from telegram.ext import CallbackContext

from src.constants import QUEUE_LIMIT, CSV_DELIMITER, MESSAGE_MAX_LENGTH, QUEUE_LIMIT_PER, QUEUE_LIMIT_CHECK_RATE
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.queue import Queue
from src.db.models.state import State
from src.general import DomainGeneral
from src.indexation import GoogleIndexationAPI
from src.utils import delete_last_message


class DomainIndex:
    @staticmethod
    @delete_last_message
    def show_all(_, context):
        args, kwargs = DomainGeneral.show_all(_, context, with_main_menu=False)
        args[1] = args[1] % 'для отправки на индекс'
        return context.bot.send_message(*args, **kwargs), 'domain_index.show_all'

    @staticmethod
    def set_next_page(_, context):
        DomainGeneral.set_next_page(_, context)
        return DomainIndex.show_all(_, context)

    @staticmethod
    def set_previous_page(_, context):
        DomainGeneral.set_previous_page(_, context)
        return DomainIndex.show_all(_, context)

    @staticmethod
    def set_page(update, context):
        DomainGeneral.set_page(update, context)
        return DomainIndex.show_all(update, context)

    @staticmethod
    @delete_last_message
    def ask_mode(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('URL UPDATED', callback_data='URL_UPDATED')],
                                       [InlineKeyboardButton('URL DELETED', callback_data='URL_DELETED')],
                                       [InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        return (context.bot.send_message(context.user_data['id'], 'Выберите тип запросов',
                                         reply_markup=markup), 'domain_index.ask_mode')

    @staticmethod
    @delete_last_message
    def get_queue(_, context: CallbackContext):
        if context.match:
            context.user_data['index_method'] = context.match.string
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        return context.bot.send_message(
            context.user_data['id'],
            'Добавьте страницы (каждая с новой строки) и '
            'нажмите отправить или отправьте текстовый файл с ссылками, если они не вмещаются в одно сообщение',
            reply_markup=markup), 'domain_index.get_queue'

    @staticmethod
    @delete_last_message
    def correct_urls(update: Update, context: CallbackContext):
        if update.message.document:
            try:
                raw_urls = update.message.document.get_file().download_as_bytearray().decode('utf-8').split('\n')
            except UnicodeDecodeError:
                context.bot.send_message(context.user_data['id'],
                                         'У файла неверный формат, или он повреждён')
                return DomainIndex.get_queue(update, context)
        else:
            raw_urls = update.message.text.split('\n')
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            urls = []
            for u in raw_urls:
                if u not in urls and u.startswith('http') and domain.url in u:
                    urls.append(u)
            if not urls:
                context.bot.send_message(context.user_data['id'], 'Ни один URL не прошёл фильтрацию!')
                return DomainIndex.get_queue(update, context)
        context.user_data['urls'] = urls[:]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Всё верно', callback_data='proceed')],
                                       [InlineKeyboardButton('Ввести ссылки заново', callback_data='back')],
                                       [InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        first = True
        messages_to_delete = []
        msg = None
        while urls:
            text = '<b>Список ссылок был обработан следующим образом:</b> \n\n' if first else ''
            while len(text) < MESSAGE_MAX_LENGTH and urls:
                text += urls.pop(0) + '\n'
            msg = context.bot.send_message(context.user_data['id'], text,
                                           parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            messages_to_delete.append(msg.message_id)
            if first:
                first = False
        msg.edit_reply_markup(markup)
        context.user_data['messages_to_delete'] = messages_to_delete[:-1]
        return msg, 'domain_index.correct_urls'

    @staticmethod
    @delete_last_message
    def create_queue(_, context: CallbackContext):
        urls = context.user_data['urls']
        groups = [urls[i:i + QUEUE_LIMIT] if i + QUEUE_LIMIT < len(urls)
                  else urls[i:len(urls) + 1] for i in range(0, len(urls), QUEUE_LIMIT)]
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            domain_url = domain.url
            last_n = len(session.query(Queue).filter(
                Queue.domain_id == context.user_data['domain_id']).all())
            for i, group in enumerate(groups):
                session.add(Queue(user_id=context.user_data['id'],
                                  domain_id=context.user_data['domain_id'],
                                  number=last_n + i + 1,
                                  method=context.user_data['index_method'],
                                  urls=','.join(group),
                                  start_length=len(group)))
                session.commit()
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Показать меню', callback_data='menu')]])
        prefix = 'Создана очередь на отправку' if len(groups) == 1 else 'Созданы очереди на отправку'
        msg = context.bot.send_message(
            context.user_data['id'],
            f'<b>{prefix}: \n\n</b>%s\n\n<b>Метод:</b> {context.user_data["index_method"]}' % (
                "\n".join([f"{domain_url}_{i} [{len(groups[i - last_n - 1])}/{QUEUE_LIMIT}]"
                           for i in range(last_n + 1, last_n + len(groups) + 1)])),
            reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        msg.edit_reply_markup(InlineKeyboardMarkup(
            [[InlineKeyboardButton('Удалить сообщение', callback_data=f'delete {msg.message_id}'),
              InlineKeyboardButton('Показать меню', callback_data='menu')]]))
        if not context.job_queue.get_jobs_by_name('process_queues'):
            context.job_queue.run_once(process_queues, 1, name='process_queues')
        return DomainIndex.show_all(_, context)


def process_queue(context: CallbackContext, session, queue: Queue, user_ids: list):
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Показать меню', callback_data='menu')]])
    markup_with_edit = None
    if (queue.domain.out_of_limit and queue.last_request and (
            datetime.utcnow() - queue.last_request).total_seconds() < QUEUE_LIMIT_CHECK_RATE):
        return
    api = GoogleIndexationAPI(queue.id, queue.domain.json_keys, queue.urls.split(','),
                              queue.domain.url, queue.method, queue.data)
    try:
        output, status = api.indexation_worker()
    except Exception as e:
        for user_id in user_ids:
            msg = context.bot.send_message(user_id,
                                           f'<b>Очередь #{queue.number}</b> домена {queue.domain.url}\n\n'
                                           f'<b>Возникла ошибка:</b> {str(e)}',
                                           disable_web_page_preview=True, parse_mode=ParseMode.HTML,
                                           reply_markup=markup)
            markup_with_edit = InlineKeyboardMarkup(
                [[InlineKeyboardButton('Удалить сообщение',
                                       callback_data=f'delete {msg.message_id}'),
                  InlineKeyboardButton('Показать меню',
                                       callback_data='menu')]])
            msg.edit_reply_markup(markup_with_edit)
        queue.is_broken = True
        session.add(queue)
        session.commit()
        return
    if status == 'out-of-limit':
        queue.domain.out_of_limit = True
        queue.last_request = datetime.utcnow()
        session.add(queue)
        session.add(queue.domain)
        session.commit()
        msg_text = f'прервана ввиду превышения лимита в {QUEUE_LIMIT} запросов в {QUEUE_LIMIT_PER}'
        schedule_delete = False
    else:
        if queue.domain.out_of_limit:
            queue.domain.out_of_limit = False
        if queue.limit_message_sent:
            queue.limit_message_sent = False
        msg_text = f'успешно обработана!'
        schedule_delete = True
    if not queue.limit_message_sent:
        dt = datetime.utcnow().isoformat().replace(':', '_').replace('T', '~').split('.')[0]
        filename = f'{queue.domain.url.split("//")[1].replace("/", "")}_{queue.number}_{dt}.csv'
        print(f'{output=}')
        with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file, delimiter=CSV_DELIMITER)
            writer.writerows(output)
        sent_count = 0
        for log in output:
            if log[-1] == 200:
                sent_count += 1
        for user_id in user_ids:
            with open(filename, 'rb') as f:
                msg = context.bot.send_document(
                    user_id, f,
                    caption=f'<b>Очередь #{queue.number}</b> домена {queue.domain.url} <b>{msg_text}</b>\n\n'
                            f'<b>Метод:</b> {queue.method.replace("_", " ")}\n\n'
                            f'Отправлено URL <b>{sent_count}</b> из <b>{queue.start_length}</b>',
                    reply_markup=markup, parse_mode=ParseMode.HTML)
            if not markup_with_edit:
                markup_with_edit = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Удалить сообщение',
                                           callback_data=f'delete {msg.message_id}'),
                      InlineKeyboardButton('Показать меню',
                                           callback_data='menu')]])
            msg.edit_reply_markup(markup_with_edit)
        if status == 'OK':
            queue.is_broken = True
            session.add(queue)
            session.commit()
        if queue.domain.out_of_limit:
            queue.limit_message_sent = True
            session.add(queue)
            session.commit()
        try:
            os.remove(filename)
        except PermissionError:
            pass
    if schedule_delete:
        session.delete(queue)
        session.commit()


def process_queues(context: CallbackContext):
    with db_session.create_session() as session:
        queues = session.query(Queue).filter(Queue.is_broken == False).all()
        print(f'Current queues: {queues}')
        user_ids = [state.user_id for state in session.query(State).all()]
        for queue in queues:
            process_queue(context, session, queue, user_ids)
        print()
    context.job_queue.run_once(process_queues, 10, name='process_queues')