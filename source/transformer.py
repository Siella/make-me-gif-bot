import io
from typing import List

from PIL import Image, ImageDraw, ImageFont, ImageOps


class ImageTransformer:
    """
    Class for an image transformation:
    if several images were passed, transforms to a GIF
    and adds a watermark. If one was passed, only adds
    a watermark.
    """
    def __init__(self, images: List[bytes], message):
        self.chat_id = str(message.chat.id)
        self.text = message.text
        self.images = [Image.open(io.BytesIO(img)) for img in images]
        self.format = 'JPEG' if len(self.images) <= 1 else 'GIF'
        self.width, self.height = self._define_gif_size()
        self.url_to_upload = None

    def _define_gif_size(self):
        """
        Determines an optimal GIF size in case
        of images having different sizes.

        :return: optimal width and height
        :rtype: tuple
        """
        max_width, max_height = -1, -1
        for image in self.images:
            width, height = image.size
            if width > max_width:
                max_width = width
            if height > max_height:
                max_height = height
        return max_width, max_height

    def _add_borders(self, img: Image.Image):
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

    def _add_watermark(self,
                       img: Image.Image,
                       font_type: str = "arial.ttf",
                       font_size=1,
                       img_fraction=.7):
        """
        Adds a watermark to an image.

        :param img: image to process
        :param font_type: font family
        :param font_size: initial font size
        :param img_fraction: ratio of font and image sizes
        :return: image with a watermark
        """
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(f"fonts/{font_type}", font_size)
        while font.getsize(self.text)[0] < img_fraction * img.size[0]:
            font_size += 1
            font = ImageFont.truetype(f"fonts/{font_type}", font_size)
        w_text, h_text = draw.textsize(self.text, font=font)
        draw.text((
            (self.width - w_text) // 2,
            (self.height - h_text) // 2),
            self.text, font=font, fill='black'
        )
        return img

    def _process_image(self, img: Image.Image):
        """
        Sequentially applies all transformation steps
        (only for GIFs).

        :param img: image to process
        :return: expanded image with a watermark
        """
        expand = self._add_borders(img)
        return self._add_watermark(expand)

    def transform(self):
        """
        Applies necessary transformation steps to get
        an intended result (GIF or JPEG).

        :return: result in bytes
        """
        new_image_bytes = io.BytesIO()
        new_image_bytes.name = ''.join([self.chat_id, '.', self.format])
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
        return new_image_bytes
