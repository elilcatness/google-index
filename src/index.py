from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode
from telegram.ext import CallbackContext

from src.constants import QUEUE_LIMIT
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.queue import Queue
from src.general import DomainGeneral
from src.utils import delete_last_message


class DomainIndex:
    @staticmethod
    @delete_last_message
    def show_all(_, context):
        args, kwargs = DomainGeneral.show_all(_, context, with_main_menu=False)
        args[1] = args[1] % 'для отправки на индекс'
        return context.bot.send_message(*args, **kwargs), 'domain_index.show_all'

    @staticmethod
    @delete_last_message
    def ask_mode(_, context: CallbackContext):
        if context.match and context.match.string.isdigit():
            context.user_data['domain_id'] = int(context.match.string)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('URL UPDATED', callback_data='1')],
                                       [InlineKeyboardButton('URL DELETED', callback_data='2')],
                                       [InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        return (context.bot.send_message(context.user_data['id'], 'Выберите тип запросов',
                                         reply_markup=markup), 'domain_index.ask_mode')

    @staticmethod
    @delete_last_message
    def get_queue(_, context: CallbackContext):
        if context.match:
            context.user_data['index_method'] = context.match.string
        print(context.user_data)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back'),
                                        InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        return context.bot.send_message(
            context.user_data['id'],
            'Добавьте страницы (каждая с новой строки) и нажмите отправить',
            reply_markup=markup), 'domain_index.get_queue'

    @staticmethod
    @delete_last_message
    def correct_urls(update: Update, context: CallbackContext):
        raw_urls = update.message.text.split('\n')
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            urls = []
            for u in raw_urls:
                if u not in urls and u.startswith('http') and domain.url in u:
                    urls.append(u)
        context.user_data['urls'] = urls
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Всё верно', callback_data='proceed')],
                                       [InlineKeyboardButton('Ввести ссылки заново', callback_data='back')],
                                       [InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')]])
        return (context.bot.send_message(context.user_data['id'],
                                         '<b>Список ссылок был обработан следующим образом:</b> \n\n' +
                                         '\n'.join(urls),
                                         reply_markup=markup, parse_mode=ParseMode.HTML,
                                         disable_web_page_preview=True),
                'domain_index.correct_urls')

    @staticmethod
    @delete_last_message
    def create_queue(_, context: CallbackContext):
        urls = context.user_data['urls']
        groups = [urls[i:i + QUEUE_LIMIT] if i + QUEUE_LIMIT < len(urls)
                  else urls[i:len(urls) + 1] for i in range(0, len(urls), QUEUE_LIMIT)]
        with db_session.create_session() as session:
            domain = session.query(Domain).get(context.user_data['domain_id'])
            domain_url = domain.url
            last_n = len(session.query(Queue).filter(Queue.user_id == context.user_data['id'] and
                                                     Queue.domain_id == context.user_data['domain_id']).all())
            for i, group in enumerate(groups):
                session.add(Queue(user_id=context.user_data['id'],
                                  domain_id=context.user_data['domain_id'],
                                  number=last_n + i + 1,
                                  method=context.user_data['index_method'],
                                  urls=','.join(group),
                                  json_keys=context.user_data['json_keys']))
                session.commit()
        prefix = 'Создана очередь на отправку' if len(groups) == 1 else 'Созданы очереди на отправку'
        method = 'URL UPDATED' if context.user_data['index_method'] == '1' else 'URL DELETED'
        context.bot.send_message(
            context.user_data['id'],
            f'<b>{prefix}: \n\n</b>%s\n\n<b>Метод:</b> {method}' % (
                "\n".join([f"{domain_url}_{i} [{len(groups[i - last_n - 1])}/{QUEUE_LIMIT}]"
                           for i in range(last_n + 1, last_n + len(groups) + 1)])),
            parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        context.job_queue.run_once(process_queue, )
        return DomainIndex.show_all(_, context)


def process_queue(context: CallbackContext):
    pass