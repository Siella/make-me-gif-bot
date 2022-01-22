from collections import defaultdict
from functools import wraps

import config
import telebot
from telebot import types
from transformer import ImageTransformer

bot = telebot.TeleBot(config.TOKEN)

USERS = defaultdict(list)


@bot.message_handler(commands=["help"])
def help(message):
    """
    Basic command handler. Gives a bot description.
    """
    bot.send_message(
        message.chat.id,
        "I can make a GIF with a watermark from images and text!\n"
        "Type /start command to create your own GIF."
    )


@bot.message_handler(commands=["start"])
def start(message):
    """
    Basic command handler. Start the process of image transformation.
    Note that user's buffer of images is flushed each time start
    command is typed.
    """
    chat_id = message.chat.id
    USERS[chat_id] = []
    user_first_name = message.from_user.first_name
    msg = bot.send_message(chat_id, f"Hey, {user_first_name}!"
                                    f"\nSend me one or more pictures"
                                    f" (not grouped), first.")
    bot.register_next_step_handler(msg, process_photo_step)


@bot.message_handler(content_types=["text"])
def text_handler(message):
    """
    Basic text handler. Replies to an unexpected text.
    """
    bot.send_message(
        message.chat.id,
        "Try to type /start or /help command."
    )


def step_break_handler(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        keyboard = types.ReplyKeyboardMarkup(True)  # сделать inline?
        keyboard.row('Basta!')
        if message.text == 'Basta!':
            bot.send_message(
                message.chat.id, 'Okay, I stop.', reply_markup=keyboard
            )
            bot.clear_step_handler_by_chat_id(message.chat.id)
            return
        return func(message, *args, **kwargs)
    return wrapper


def step_exception_handler(func):  # сюды логгер
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        try:
            result = func(message, *args, **kwargs)
        except Exception:  # ???
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.reply_to(
                message,
                "Something went wrong.\n"
                "Try /start or /help command again."
            )
            return
        return result
    return wrapper


def process_photo(message):
    """
    Adds image bytes to the USERS dictionary.
    """
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_bytes = bot.download_file(file_info.file_path)
    USERS[message.chat.id].append(file_bytes)


@bot.message_handler(content_types=['photo'])
def photo(message):
    """
    Handler for a photo content type.
    """
    process_photo(message)


@step_break_handler
@step_exception_handler
def process_photo_step(message):
    """
    Stores images received from a user as bytes in USERS
    until /done command is typed.
    """
    answer = "Please, send me pictures (compressed)."
    next_step = process_photo_step
    if message.photo:
        process_photo(message)
        answer = "Upload another pictures or type /done to go further."
    if message.text == '/done':
        next_step = process_text_step
        answer = "Next, give me a some text."
    msg = bot.send_message(message.chat.id, answer)
    bot.register_next_step_handler(msg, next_step)


@step_break_handler
@step_exception_handler
def process_text_step(message):
    """
    Asks for a watermark as text. If text is passed,
    the bot goes to a GIF/image transformation step.
    """
    answer = "Please, send me some symbols."
    next_step = process_text_step
    if message.text:
        answer = "Okay, wait a little bit..."
        bot.send_message(message.chat.id, answer)
        send_result(message)
        return
    msg = bot.send_message(message.chat.id, answer)
    bot.register_next_step_handler(msg, next_step)


def send_result(message):
    """
    Sends a result of an image transformation.
    If one image was received, returns a photo with a watermark.
    If several images were received, returns a GIF with a watermark.
    """
    chat_id = message.chat.id
    img = ImageTransformer(USERS[chat_id], message)
    res = img.transform()
    res.seek(0)
    if res.name[-5:] == '.JPEG':
        bot.send_photo(chat_id, res, caption='All done!')
    else:
        bot.send_animation(chat_id, res, None, caption='All done!')


if __name__ == '__main__':
    bot.enable_save_next_step_handlers()
    bot.load_next_step_handlers()
    bot.infinity_polling()
