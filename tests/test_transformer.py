import io
import os

from PIL import Image
from telebot import types

from source.transformer import ImageTransformer
from source.utils import Settings


def find_test_file(name):
    return os.path.join(
        os.path.dirname(__file__),
        'test_images',
        name
    )


with open(find_test_file('1.jpg'), "rb") as image:
    f = image.read()
    im1 = bytearray(f)

with open(find_test_file('2.jpg'), "rb") as image:
    f = image.read()
    im2 = bytearray(f)

im3 = Image.open(find_test_file('3.gif'))


def create_text_message(text):
    params = {'text': text}
    chat = types.User(11, False, 'test')
    return types.Message(1, chat, None, chat, 'text', params, "")


msg = create_text_message('test')
s = Settings()
s.text, s.font_family, s.font_size = msg.text, 'arial', 0.7


def test_image_transformer():
    transformer = ImageTransformer([im1, im2], s, msg)

    assert transformer.width == 700
    assert transformer.height == 525
    assert transformer.format == 'GIF'
    assert transformer.text == 'test'
    assert transformer.user_id == '11'

    result = transformer.transform().bytes
    im4 = Image.open(result)
    assert im3.mode == im4.mode
    assert im3.size == im4.size

    bytes_1 = io.BytesIO()
    im3.save(bytes_1, 'gif')
    bytes_1.seek(0)

    bytes_2 = io.BytesIO()
    im4.save(bytes_2, 'gif')
    bytes_2.seek(0)
    assert bytes_1.getvalue()[:3000] == bytes_2.getvalue()[:3000]
