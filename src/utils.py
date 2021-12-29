import json

from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.state import State


def delete_last_message(func):
    def wrapper(update, context: CallbackContext):
        if context.user_data.get('message_id'):
            context.bot.deleteMessage(context.user_data['id'], context.user_data.pop('message_id'))
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