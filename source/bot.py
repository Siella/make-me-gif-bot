import io
import time
from functools import wraps
from typing import List
from urllib.error import HTTPError

import telebot
from urllib3.exceptions import MaxRetryError

from source.config import (BATCH_SIZE, FONT_COMMANDS, FONT_SIZES, IMAGES, MSG,
                           SETTINGS, TOKEN)
from source.storage import MinioClient
from source.transformer import ImageTransformer

bot = telebot.TeleBot(TOKEN)
client = MinioClient()


@bot.message_handler(commands=["help"])
def help(message):
    """
    Basic command handler. Gives a bot description.
    """
    bot.send_message(message.chat.id, MSG.help)


@bot.message_handler(commands=["start"])
def start(message):
    """
    Basic command handler. Start the process of image transformation.
    Note that user's buffer of images is flushed each time start
    command is typed.
    """
    IMAGES[message.from_user.id] = []  # refresh buffer
    chat_id = message.chat.id
    user_first_name = message.from_user.first_name
    msg = bot.send_message(chat_id, MSG.start.format(user_first_name))
    bot.register_next_step_handler(msg, process_photo_step)


def connect_storage(func):
    def wrapper(message, *args, **kwargs):
        try:
            func(message, *args, **kwargs)
        except (MaxRetryError, HTTPError):
            bot.reply_to(message, MSG.storage_exc)
            return
    return wrapper


@bot.message_handler(commands=["download"])
def download_user_content(message):
    user_id = str(message.from_user.id)
    bot.send_message(message.chat.id, MSG.download)
    _download_all_content(message, [user_id])


@bot.message_handler(commands=["download_all"])
def download_all_content(message):
    msg = bot.send_message(message.chat.id, MSG.download_all)
    bot.register_next_step_handler(msg, _download_all_content)


@connect_storage
def _download_all_content(message, user_list: List[str] = []):
    text = message.text
    if text != '/all' and not user_list:
        user_list = ("".join(text.split())).split(',')
    content = client.download_all_content(user_list)
    message.text = '/Y'  # first mock answer
    send_batch(message, content)


def send_batch(message, content: List[io.BytesIO] = []):
    if message.text != '/Y':  # answer for question ``More?``
        return
    for i, obj in enumerate(content, 1):
        send_content(message, obj)
        if i % BATCH_SIZE == 0:
            msg = bot.send_message(message.chat.id, MSG.more)
            bot.register_next_step_handler(
                msg, send_batch, content[BATCH_SIZE:]
            )
            break


def send_content(message, obj: io.BytesIO, caption=None):
    chat_id = message.chat.id
    bot.send_document(chat_id, obj, caption=caption)


@bot.message_handler(content_types=["text"])
def text_handler(message):
    """
    Basic text handler. Replies to an unexpected text.
    """
    bot.send_message(message.chat.id, MSG.text)


def step_break_handler(func):
    """
    Breaks interaction with a user if /restart is typed.
    """
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if message.text == '/restart':
            bot.send_message(message.chat.id, MSG.restart)
            bot.clear_step_handler_by_chat_id(message.chat.id)
            return
        return func(message, *args, **kwargs)
    return wrapper


def process_photo(message):
    """
    Adds image bytes to the USERS dictionary.
    """
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_bytes = bot.download_file(file_info.file_path)
    IMAGES[message.from_user.id].append(file_bytes)


@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    """
    Handler for a photo content type.
    """
    process_photo(message)


@step_break_handler
def process_photo_step(message):
    """
    Stores images received from a user as bytes in USERS
    until /done command is typed.
    """
    answer = MSG.process_photo
    next_step = process_photo_step
    if message.photo:
        photo_handler(message)
        time.sleep(2)
        answer = MSG.process_photo_done
    if (message.text == '/done') and IMAGES[message.from_user.id]:
        next_step = process_text_step
        answer = MSG.process_photo_next
    msg = bot.send_message(message.chat.id, answer)
    bot.register_next_step_handler(msg, next_step)


@step_break_handler
def process_text_step(message):
    """
    Asks for a watermark as text. If text is passed,
    the bot goes to a font selection step.
    """
    answer = MSG.process_text_repeat
    next_step = process_text_step
    if message.text:
        user_id = message.from_user.id
        text = message.text
        SETTINGS[user_id].text = text
        answer = MSG.font
        next_step = process_font_type_step
    msg = bot.send_message(message.chat.id, answer)
    bot.register_next_step_handler(msg, next_step)


@step_break_handler
def process_font_type_step(message):
    """
    Asks for a font family. If available font
    is passed, the bot goes to a size selection step.
    """
    answer = MSG.font
    next_step = process_font_type_step
    if message.text in FONT_COMMANDS:
        user_id = message.from_user.id
        font_family = message.text[1:]
        SETTINGS[user_id].font_family = font_family
        answer = MSG.size
        next_step = process_font_size_step
    msg = bot.send_message(message.chat.id, answer)
    bot.register_next_step_handler(msg, next_step)


@step_break_handler
def process_font_size_step(message):
    """
    Asks for a font size (as aspect ratio). If proper
    command for size is passed, the bot goes to
    a GIF/photo creation step.
    """
    if message.text in FONT_SIZES:
        user_id = message.from_user.id
        font_size = FONT_SIZES[message.text]
        SETTINGS[user_id].font_size = font_size
        bot.send_message(message.chat.id, MSG.wait)
        send_result_step(message)
        return
    msg = bot.send_message(message.chat.id, MSG.size)
    bot.register_next_step_handler(msg, process_font_size_step)


@step_break_handler
def send_result_step(message):
    """
    Sends a result of an image transformation.
    If one image was received, returns a photo with a watermark.
    If several images were received, returns a GIF with a watermark.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    obj = ImageTransformer(user_id).transform()
    send_content(message, obj, caption='All done!')
    msg = bot.send_message(chat_id, MSG.finish)
    bot.register_next_step_handler(msg, upload_result_step, obj)


@connect_storage
def upload_result_step(message, obj: io.BytesIO):
    if message.text in ['/save', '/publish']:
        is_private = (message.text == '/save') | (obj.name[-3:] != 'GIF')
        client.upload(message.from_user.id, obj, is_private)
        bot.send_message(message.chat.id, MSG.saved)
    else:
        text_handler(message)


if __name__ == '__main__':
    bot.enable_save_next_step_handlers()
    bot.load_next_step_handlers()
    bot.infinity_polling()
