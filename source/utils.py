from pathlib import Path


class Settings:
    __slots__ = ('text', 'font_family', 'font_size')


def parse_available_font_types():
    path = Path(__file__).parents[1] / 'fonts'
    files = [
        x.name for x in path.iterdir()
        if x.is_file()
    ]
    return files
