import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw


def generate_styled_qr(url: str, size: int = 250) -> Image.Image:

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)


    qr_image = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            back_color=(255, 255, 255),
            front_color=(0, 0, 0),
        ),
    )


    qr_image = qr_image.convert("RGBA")


    result_image = qr_image.copy()
    draw = ImageDraw.Draw(result_image)


    module_size = 10
    eye_outer_size = 7 * module_size
    eye_inner_size = 5 * module_size
    eye_dot_size = 3 * module_size


    inner_offset = (eye_outer_size - eye_inner_size) // 2
    dot_offset = (eye_outer_size - eye_dot_size) // 2


    eye_positions = [
        (17, 17),
        (qr_image.width - eye_outer_size - 18, 18),
        (17, qr_image.height - eye_outer_size - 18)
    ]


    for x, y in eye_positions:

        white_bg_size = eye_outer_size + 4
        white_bg_offset = -2
        draw.rectangle(
            [x + white_bg_offset, y + white_bg_offset,
             x + white_bg_size + white_bg_offset, y + white_bg_size + white_bg_offset],
            fill=(255, 255, 255, 255)
        )


        draw.rounded_rectangle(
            [x, y, x + eye_outer_size, y + eye_outer_size],
            radius=15,
            fill=(0, 0, 0, 255),
            outline=(0, 0, 0, 255)
        )


        draw.rounded_rectangle(
            [x + inner_offset, y + inner_offset,
             x + inner_offset + eye_inner_size, y + inner_offset + eye_inner_size],
            radius=10,
            fill=(255, 255, 255, 255),
            outline=(255, 255, 255, 255)
        )


        draw.rounded_rectangle(
            [x + dot_offset, y + dot_offset,
             x + dot_offset + eye_dot_size, y + dot_offset + eye_dot_size],
            radius=8,
            fill=(0, 91, 138, 255),
            outline=(0, 100, 255, 255)
        )

    result_image = result_image.resize((size, size), Image.Resampling.LANCZOS)

    return result_image
