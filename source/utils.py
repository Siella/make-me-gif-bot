import os
from pathlib import Path


class Settings:
    def __init__(self, text, font_family, font_size):
        self.text = text
        self.font_family = font_family
        self.font_size = font_size


def parse_available_font_types():
    files = os.listdir(
        os.path.join(
            Path(os.path.dirname(__file__)).parent, 'fonts')
    )
    return list(map(lambda x: x[:x.rfind('.')], files))


FONT_TYPES = parse_available_font_types()
FONT_SIZES = {
    '/small': 0.3,
    '/medium': 0.7,
    '/large': 0.9,
}
