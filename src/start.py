from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.utils import delete_last_message, check_user_permission


@delete_last_message
def menu(update: Update, context: CallbackContext):
    if update.message and not context.user_data.get('id'):
        context.user_data['id'] = update.message.from_user.id
    buttons = ([[InlineKeyboardButton('Добавить новый домен', callback_data='add_new_domain')]]
               if check_user_permission(context.user_data['id'], 'ADD_USERS') else [])
    with db_session.create_session() as session:
        if session.query(Domain).all():
            for text, callback_data, env_vars in [
                    ('Индексация / Удаление из индекса', 'index_menu', ['URL_UPDATED_USERS', 'URL_DELETED_USERS']),
                    ('Редактировать', 'edit_menu', ['EDIT_USERS']),
                    ('Удалить', 'delete_menu', ['DELETE_USERS']),
                    ('Доступные домены и очереди', ['VIEW_USERS'])]:
                if any(check_user_permission(context.user_data['id'], v) for v in env_vars):
                    buttons += [InlineKeyboardButton(text, callback_data=callback_data)]
    if not buttons:
        return context.bot.send_message(context.user_data['id'],
                                        'Хьюстон, у Вас проблема! Свяжитесь с разработчиком')
    markup = InlineKeyboardMarkup(buttons)
    return context.bot.send_message(context.user_data['id'], 'Меню', reply_markup=markup), 'menu'