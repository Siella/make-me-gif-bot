import io
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from source.config import IMAGES, SETTINGS


class ImageTransformer:
    """
    Class for an image transformation:
    if several images were passed, transforms to a GIF
    and adds a watermark. If one was passed, only adds
    a watermark.

    :ivar user_id: Telegram user ID
    :ivar text: message text
    :ivar font_family: font family name (e.g., arial)
    :ivar img_fraction: ratio of font and image sizes
    :ivar images: list of images as bytes
    :ivar format: file format for after transforming
    :ivar width: resulting image width
    :ivar height: resulting image height
    """
    def __init__(self, user_id: int):
        self.user_id = str(user_id)
        self.text = SETTINGS[user_id].text
        self.font_family = SETTINGS[user_id].font_family
        self.img_fraction = SETTINGS[user_id].font_size
        self.images = [Image.open(io.BytesIO(img)) for img in IMAGES[user_id]]
        self.format = 'JPEG' if len(self.images) <= 1 else 'GIF'
        self.width, self.height = self._define_gif_size()

    def _define_gif_size(self) -> Tuple[int, int]:
        """
        Determines an optimal GIF size in case
        of images having different sizes.

        :return: optimal width and height
        """
        max_width, max_height = -1, -1
        for image in self.images:
            width, height = image.size
            if width > max_width:
                max_width = width
            if height > max_height:
                max_height = height
        return max_width, max_height

    def _add_borders(self, img: Image.Image) -> Image.Image:
        """
        Expands an image size in accordance to an optimal one.

        :param img: image to process
        :return: expanded image
        """
        width, height = img.size
        w_border = (self.width - width) // 2
        h_border = (self.height - height) // 2
        expand = ImageOps.expand(
            img, (w_border, h_border, w_border, h_border), fill='white'
        )
        return expand

    def _add_watermark(self, img: Image.Image,
                       font_size: int = 1) -> Image.Image:
        """
        Adds a watermark to an image.

        :param img: image to process
        :param font_size: initial font size
        :return: image with a watermark
        """
        txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)
        font = ImageFont.truetype(
            f"fonts/{self.font_family}.ttf", font_size
        )
        while font.getsize(self.text)[0] < self.img_fraction * img.size[0]:
            font_size += 1
            font = ImageFont.truetype(
                f"fonts/{self.font_family}.ttf", font_size
            )
        w_text, h_text = draw.textsize(self.text, font=font)
        draw.text((
            (self.width - w_text) // 2,
            (self.height - h_text) // 2),
            self.text, font=font, fill=(0, 0, 0, 128)
        )
        out = Image.alpha_composite(img.convert('RGBA'), txt)
        return out.convert('RGB')

    def _process_image(self, img: Image.Image) -> Image.Image:
        """
        Sequentially applies all transformation steps
        (only for GIFs).

        :param img: image to process
        :return: expanded image with a watermark
        """
        expand = self._add_borders(img)
        watermark = self._add_watermark(expand)
        return watermark

    def transform(self) -> io.BytesIO:
        """
        Applies necessary transformation steps to get
        an intended result (GIF or JPEG).

        :return: ImageObject with filled data
        """
        new_image_bytes = io.BytesIO()
        new_image_bytes.name = ''.join([self.user_id, '.', self.format])
        if self.format == 'JPEG':
            image = self.images.pop(0)
            new_image = self._add_watermark(image)
            new_image.save(new_image_bytes, format=self.format)
        else:
            images = [self._process_image(img) for img in self.images]
            images[0].save(
                new_image_bytes, format=self.format,
                save_all=True, append_images=images[1:],
                optimize=False, duration=600, loop=0
            )
        new_image_bytes.seek(0)
        return new_image_bytes
