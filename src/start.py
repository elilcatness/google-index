from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.utils import delete_last_message


@delete_last_message
def menu(update: Update, context: CallbackContext):
    if update.message and not context.user_data.get('id'):
        context.user_data['id'] = update.message.from_user.id
    buttons = [[InlineKeyboardButton('Добавить новый домен', callback_data='add_new_domain')]]
    with db_session.create_session() as session:
        if session.query(Domain).all():
            buttons += [[InlineKeyboardButton('Отправить страницы в индекс', callback_data='send_to_index')],
                        [InlineKeyboardButton('Редактировать', callback_data='edit_menu')],
                        [InlineKeyboardButton('Удалить', callback_data='delete_menu')],
                        [InlineKeyboardButton('Доступные домены и очереди', callback_data='domains & queues')]]
    markup = InlineKeyboardMarkup(buttons)
    return context.bot.send_message(context.user_data['id'], 'Меню', reply_markup=markup), 'menu'