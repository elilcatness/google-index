from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.general import DomainGeneral
from src.utils import delete_last_message


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
    pass