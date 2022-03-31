import os
from collections import defaultdict

from dotenv import load_dotenv

from source.utils import Settings, parse_available_font_types

load_dotenv()

TOKEN = os.environ.get('TOKEN')
ADDRESS = os.environ.get('MINIO_API_ADDRESS')
ACCESS_KEY = os.environ.get('ACCESS_KEY')
SECRET_KEY = os.environ.get('SECRET_KEY')

IMAGES = defaultdict(list)
SETTINGS = defaultdict(lambda: Settings())
BATCH_SIZE = 2

FONT_TYPES = parse_available_font_types()
FONT_COMMANDS = list(
    map(lambda x: '/' + x[:-4], FONT_TYPES)  # arial.ttf --> /arial
)
FONT_SIZES = {
    '/small': 0.3,
    '/medium': 0.7,
    '/large': 0.9,
}

############################
# Bot's messages and replies
############################


class MSG:
    help = \
        "I can make a GIF with a watermark from images and text!\n"\
        "Type /start command to create your own GIF.\n"\
        "Type /download to get all content you generated "\
        "or /download_all to get all publicly available " \
        "content (or by specific users)."

    start = \
        "Hey, {}!\n"\
        "Send me one or more pictures "\
        "(not grouped), first."

    download = "Here you go!"
    storage_exc = "Sorry, storage is not reachable."
    download_all = \
        "Type IDs of users whom content you'd like to download "\
        "(comma-separated, e.g., 1,2,3,...) or type /all "\
        "to get all available content."
    more = "More? (/Y or /N)"

    text = "Try to type /start or /help command."
    restart = "Okay, I stop."

    process_photo = "Please, send me pictures (compressed)."
    process_photo_done = \
        "Upload another pictures or type /done to go further."
    process_photo_next = "Next, give me a some text."

    process_text_repeat = "Please, send me some symbols."
    font = '\n'.join(["Choose a font:"] + FONT_COMMANDS)
    size = '\n'.join(["Choose font size:"] + list(FONT_SIZES))
    wait = "Okay, wait a little bit..."

    finish = \
        "Type /publish (only for GIFs) to upload the result "\
        "in a publicly available storage or /save for private "\
        "only keeping."
    saved = "I kept it!"
