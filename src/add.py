from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, ParseMode
from telegram.ext import CallbackContext

from src.db import db_session
from src.db.models.domain import Domain
from src.utils import delete_last_message
from src.start import menu


class Addition:
    @staticmethod
    @delete_last_message
    def ask_url(_, context: CallbackContext):
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back')]])
        context.user_data['addition'] = {}
        return context.bot.send_message(context.user_data['id'], 'Введите адрес сайта с протоколом',
                                        reply_markup=markup), 'addition.url'

    @staticmethod
    @delete_last_message
    def ask_login(update: Update, context: CallbackContext):
        if not context.user_data['addition'].get('url'):
            url = update.message.text
            if not url.startswith('http://') and not url.startswith('https://'):
                update.message.reply_text('Адрес должен быть с <b>протоколом</b>!', parse_mode=ParseMode.HTML)
                return Addition.ask_url(update, context)
            context.user_data['addition']['url'] = url
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back')]])
        return context.bot.send_message(context.user_data['id'], 'Введите логин',
                                        reply_markup=markup), 'addition.login'

    @staticmethod
    @delete_last_message
    def ask_password(update: Update, context: CallbackContext):
        if not context.user_data['addition'].get('login'):
            context.user_data['addition']['login'] = update.message.text
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться назад', callback_data='back')]])
        return context.bot.send_message(context.user_data['id'], 'Введите пароль',
                                        reply_markup=markup), 'addition.password'

    @staticmethod
    @delete_last_message
    def ask_api_key(update: Update, context: CallbackContext):
        if not context.user_data['addition'].get('password'):
            context.user_data['addition']['password'] = update.message.text
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуься назад', callback_data='back')]])
        return context.bot.send_message(context.user_data['id'], 'Введите API ключ',
                                        reply_markup=markup), 'addition.api_key'

    @staticmethod
    @delete_last_message
    def finish(update: Update, context: CallbackContext):
        context.user_data['addition']['api_key'] = update.message.text
        url = context.user_data['addition']['url']
        with db_session.create_session() as session:
            session.add(Domain(**context.user_data.pop('addition')))
            session.commit()
        context.bot.send_message(context.user_data['id'], f'Сайт <b>{url}</b> был добавлен',
                                 disable_web_page_preview=True, parse_mode=ParseMode.HTML)
        return menu(update, context)
