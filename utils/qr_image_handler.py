import cv2
import numpy as np
from pyzbar.pyzbar import decode


def rotate_image_with_transparency(image, angle):
    if image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = np.abs(matrix[0, 0])
    sin = np.abs(matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    matrix[0, 2] += (new_w / 2) - center[0]
    matrix[1, 2] += (new_h / 2) - center[1]
    rotated = cv2.warpAffine(image, matrix, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return rotated

def add_noise_to_center_area(image, sigma=50, area_ratio=0.6):
    h, w = image.shape[:2]
    c = image.shape[2]
    cx, cy = w // 2, h // 2
    half_w = int(w * area_ratio / 2)
    half_h = int(h * area_ratio / 2)

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[cy - half_h:cy + half_h, cx - half_w:cx + half_w] = 255
    mask_multi = cv2.merge([mask] * c)

    noise = np.random.normal(0, sigma, image.shape).astype(np.int16)
    noisy_image = image.astype(np.int16)
    noisy_image[mask_multi == 255] += noise[mask_multi == 255]
    noisy_image = np.clip(noisy_image, 0, 255).astype(np.uint8)
    return noisy_image

def darken_image(image, factor=0.85):
    darkened = cv2.convertScaleAbs(image, alpha=factor, beta=0)
    return darkened

def process_qr_image(img, padding=5):
    qr_codes = decode(img)
    if not qr_codes:
        return None, None
    qr = qr_codes[0]
    x, y, w, h = qr.rect
    x_start = max(x - padding, 0)
    y_start = max(y - padding, 0)
    x_end = min(x + w + padding, img.shape[1])
    y_end = min(y + h + padding, img.shape[0])
    qr_img = img[y_start:y_end, x_start:x_end]
    return img, qr_img


def process_qr_image2(img, padding=10):
    qr_codes = decode(img)
    if not qr_codes:
        return None, None
    qr = qr_codes[0]
    x, y, w, h = qr.rect
    x_start = max(x - padding, 0)
    y_start = max(y - padding, 0)
    x_end = min(x + w + padding, img.shape[1])
    y_end = min(y + h + padding, img.shape[0])
    qr_img = img[y_start:y_end, x_start:x_end]

    qr_rgba = cv2.cvtColor(qr_img, cv2.COLOR_BGR2BGRA)

    white_thresh = 240
    mask = cv2.inRange(qr_img, (white_thresh, white_thresh, white_thresh), (255, 255, 255))
    qr_rgba[mask == 255] = [0, 0, 0, 0]

    return img, qr_rgba



