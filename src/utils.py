import json
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from src.constants import QUEUE_LIMIT
from src.db import db_session
from src.db.models.domain import Domain
from src.db.models.state import State


def delete_last_message(func):
    def wrapper(update, context: CallbackContext):
        if context.user_data.get('message_id'):
            try:
                context.bot.deleteMessage(context.user_data['id'], context.user_data.pop('message_id'))
            except BadRequest:
                pass
        while context.user_data.get('messages_to_delete'):
            context.bot.deleteMessage(context.user_data['id'],
                                      context.user_data['messages_to_delete'].pop(0))
        output = func(update, context)
        if isinstance(output, tuple):
            msg, callback = output
            context.user_data['message_id'] = msg.message_id
            save_state(context.user_data['id'], callback, context.user_data)
        else:
            callback = output
        return callback

    return wrapper


def save_state(user_id: int, callback: str, data: dict):
    with db_session.create_session() as session:
        state = session.query(State).get(user_id)
        str_data = json.dumps(data)
        if state:
            state.user_id = user_id
            state.callback = callback
            state.data = str_data
        else:
            state = State(user_id=user_id, callback=callback, data=str_data)
        session.add(state)
        session.commit()


def build_pagination(array: list[tuple], pag_step: int, current_page: int,
                     with_main_menu: bool = True):
    array_length = len(array)
    pages_count = (
        array_length // pag_step if array_length / pag_step == array_length // pag_step
        else array_length // pag_step + 1)
    if current_page > pages_count:
        current_page = pages_count
    start = (current_page - 1) * pag_step
    end = current_page * pag_step if current_page * pag_step <= array_length else array_length
    buttons = [[InlineKeyboardButton(elem[0], callback_data=elem[1])] for elem in array[start:end]]
    if pages_count > 1:
        pag_block = [InlineKeyboardButton(f'{current_page}/{pages_count}', callback_data='refresh')]
        if current_page > 1:
            pag_block.insert(0, InlineKeyboardButton('«', callback_data='prev_page'))
        if current_page < pages_count:
            pag_block.append(InlineKeyboardButton('»', callback_data='next_page'))
        buttons.append(pag_block)
    buttons.append([InlineKeyboardButton('Вернуться назад', callback_data='back')])
    if with_main_menu:
        buttons.append([InlineKeyboardButton('Вернуться в основное меню', callback_data='menu')])
    return InlineKeyboardMarkup(buttons), pages_count


def delete_message(_, context: CallbackContext):
    context.bot.delete_message(context.user_data['id'], int(context.match.string.split()[-1]))


def check_user_permission(user_id: int, env_var: str):
    return user_id in [int(x) for x in os.getenv(env_var, '').split(';') if x and x.strip().isdigit()]