import os
import time
from collections import defaultdict
from functools import wraps

import telebot
from dotenv import load_dotenv
from storage import MinioClient
from transformer import ImageObject, ImageTransformer

load_dotenv()

TOKEN = os.environ.get('TOKEN')
client = MinioClient()

USERS = defaultdict(list)


class Bot:
    def __init__(self):
        self.bot = telebot.TeleBot(TOKEN)

        @self.bot.message_handler(commands=["help"])
        def help(message):
            """
            Basic command handler. Gives a bot description.
            """
            self.bot.send_message(
                message.chat.id,
                "I can make a GIF with a watermark from images and text!\n"
                "Type /start command to create your own GIF.\n"
                "Type /download to get all content you generated "
                "or /download_all to get all publicly available "
                "content (or by specific users)."
            )

        @self.bot.message_handler(commands=["start"])
        def start(message):
            """
            Basic command handler. Start the process of image transformation.
            Note that user's buffer of images is flushed each time start
            command is typed.
            """
            chat_id = message.chat.id
            user_id = message.from_user.id
            USERS[user_id] = []
            user_first_name = message.from_user.first_name
            msg = self.bot.send_message(chat_id,
                                        f"Hey, {user_first_name}!"
                                        f"\nSend me one or more pictures"
                                        f" (not grouped), first.")
            self.bot.register_next_step_handler(msg, process_photo_step)

        @self.bot.message_handler(commands=["download"])
        def download_user_content(message):
            self.bot.send_message(message.chat.id, 'Here you go!')
            user_id = message.from_user.id
            content = client.download_generated_content(user_id)
            for obj in content:
                send_content(message, obj)

        @self.bot.message_handler(commands=["download_all"])
        def download_all_content(message):
            answer = "Type IDs of users whom content you'd like to download " \
                     "(comma-separated, e.g., 1,2,3,...) or type /all " \
                     "to get all available content."
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, _download_all_content)

        def _download_all_content(message):
            user_list = []
            text = message.text
            if text != '/all':
                user_list = ("".join(text.split())).split(',')
            content = client.download_all_content(user_list)
            for obj in content:
                send_content(message, obj)

        @self.bot.message_handler(content_types=["text"])
        def text_handler(message):
            """
            Basic text handler. Replies to an unexpected text.
            """
            self.bot.send_message(
                message.chat.id,
                "Try to type /start or /help command."
            )

        def step_break_handler(func):
            @wraps(func)
            def wrapper(message, *args, **kwargs):
                if message.text == '/restart':
                    self.bot.send_message(message.chat.id, 'Okay, I stop.')
                    self.bot.clear_step_handler_by_chat_id(message.chat.id)
                    return
                return func(message, *args, **kwargs)
            return wrapper

        def process_photo(message):
            """
            Adds image bytes to the USERS dictionary.
            """
            file_id = message.photo[-1].file_id
            file_info = self.bot.get_file(file_id)
            file_bytes = self.bot.download_file(file_info.file_path)
            USERS[message.from_user.id].append(file_bytes)

        @self.bot.message_handler(content_types=['photo'])
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
            answer = "Please, send me pictures (compressed)."
            next_step = process_photo_step
            if message.photo:
                photo_handler(message)
                time.sleep(2)
                answer = "Upload another pictures or type /done to go further."
            if message.text == '/done':
                next_step = process_text_step
                answer = "Next, give me a some text."
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, next_step)

        @step_break_handler
        def process_text_step(message):
            """
            Asks for a watermark as text. If text is passed,
            the bot goes to a GIF/image transformation step.
            """
            answer = "Please, send me some symbols."
            next_step = process_text_step
            if message.text:
                answer = "Okay, wait a little bit..."
                self.bot.send_message(message.chat.id, answer)
                send_result_step(message)
                return
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, next_step)

        def send_content(message, obj: ImageObject, caption=None):
            chat_id = message.chat.id
            if obj.format == 'GIF':
                self.bot.send_animation(
                    chat_id, obj.bytes, None, caption=caption
                )

        @step_break_handler
        def send_result_step(message):
            """
            Sends a result of an image transformation.
            If one image was received, returns a photo with a watermark.
            If several images were received, returns a GIF with a watermark.
            """
            user_id = message.from_user.id
            img = ImageTransformer(USERS[user_id], message)
            obj = img.transform()
            send_content(message, obj, 'All done!')
            answer = "Type /publish to upload the result in a publicly " \
                     "available storage (only for GIFs) or /save " \
                     "for private only keeping."
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, upload_result_step, obj)

        def upload_result_step(message, obj: ImageObject):
            if message.text in ['/save', '/publish']:
                private = (message.text == '/save') | (obj.format != 'GIF')
                client.upload(message.from_user.id, obj, private)
                self.bot.send_message(message.chat.id, 'I kept it!')
            else:
                text_handler(message)


if __name__ == '__main__':
    tg = Bot()
    tg.bot.enable_save_next_step_handlers()
    tg.bot.load_next_step_handlers()
    tg.bot.infinity_polling()
