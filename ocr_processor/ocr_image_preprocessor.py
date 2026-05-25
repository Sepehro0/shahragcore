# -*- coding: utf-8 -*-
"""
OCR Image Preprocessor — Adaptive Pipeline
پیش‌پردازش تطبیقی تصویر برای OCR فارسی

اصل کلیدی: قبل از هر مرحله، کیفیت تصویر سنجیده می‌شود.
اگر تصویر از قبل کیفیت مناسبی داشته باشد، آن مرحله اعمال نمی‌شود.

نتایج تجربی نشان داد:
  - CLAHE روی اسناد روشن (background سفید): confidence را کاهش می‌دهد
  - Denoise روی تصاویر با لبه‌های تیز: متن را محو می‌کند
  - Deskew اگر skew < 1°: کاملاً غیرضروری است
  → همه مراحل باید شرطی (conditional) باشند
"""

import logging
import numpy as np
from PIL import Image
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Image Quality Assessment
# ─────────────────────────────────────────────────────────────

class ImageQuality(NamedTuple):
    brightness: float     # 0.0–1.0 | میانگین روشنایی
    contrast: float       # 0.0–1.0 | انحراف معیار نرمال
    noise_level: float    # 0.0–1.0 | برآورد نویز
    skew_angle: float     # درجه | زاویه کج‌شدگی
    is_small: bool        # آیا تصویر کوچک است
    needs_clahe: bool     # آیا کنتراست واقعاً کم است
    needs_denoise: bool   # آیا نویز واقعاً بالاست
    needs_deskew: bool    # آیا کج‌شدگی معنادار است


def assess_image_quality(image: Image.Image) -> ImageQuality:
    """
    ارزیابی کیفیت تصویر برای تصمیم‌گیری در مورد preprocessing.

    معیارهای needs_clahe:
      - contrast < 0.15 (کنتراست خیلی پایین)
      - brightness > 0.95 (سوخته/خیلی روشن) یا < 0.2 (خیلی تاریک)

    معیارهای needs_denoise:
      - noise_level > 0.06 (نویز بالا)
      - contrast > 0.1 (اگر کنتراست خیلی کم باشد، denoise فایده‌ای ندارد)

    معیارهای needs_deskew:
      - |skew_angle| > 1.0 درجه
    """
    try:
        import scipy.ndimage as ndi

        gray = np.array(image.convert("L")).astype(float)

        brightness = gray.mean() / 255.0
        contrast = gray.std() / 255.0

        # برآورد نویز: انحراف معیار باقی‌مانده بعد از Gaussian خفیف
        smooth = ndi.gaussian_filter(gray, sigma=1.0)
        residual = gray - smooth
        noise_level = float(np.std(residual) / 255.0)

        # تشخیص skew
        skew_angle = _estimate_skew(gray)

        w, h = image.size
        is_small = h < 800

        # تصمیم‌گیری: کنتراست واقعی متن (نه background)
        # در اسناد با پس‌زمینه سفید، contrast کلی پایین است اما متن تیز است
        # → فقط وقتی contrast < 0.12 باشد CLAHE لازم است
        needs_clahe = contrast < 0.12 or brightness < 0.25

        # Denoise فقط وقت نویز واقعاً بالا و کنتراست کافی باشد
        needs_denoise = noise_level > 0.06 and contrast > 0.10

        needs_deskew = abs(skew_angle) > 1.0

        logger.debug(
            f"Image quality: brightness={brightness:.3f}, contrast={contrast:.3f}, "
            f"noise={noise_level:.4f}, skew={skew_angle:.2f}° | "
            f"needs: clahe={needs_clahe}, denoise={needs_denoise}, deskew={needs_deskew}"
        )

        return ImageQuality(
            brightness=brightness,
            contrast=contrast,
            noise_level=noise_level,
            skew_angle=skew_angle,
            is_small=is_small,
            needs_clahe=needs_clahe,
            needs_denoise=needs_denoise,
            needs_deskew=needs_deskew,
        )

    except Exception as e:
        logger.warning(f"Image quality assessment failed: {e} — using safe defaults")
        return ImageQuality(
            brightness=0.5, contrast=0.3, noise_level=0.03,
            skew_angle=0.0, is_small=False,
            needs_clahe=False, needs_denoise=False, needs_deskew=False,
        )


def _estimate_skew(gray: np.ndarray) -> float:
    """تخمین زاویه کج‌شدگی با Radon transform"""
    try:
        from skimage.transform import radon
        from skimage.feature import canny

        MAX_ANGLE = 10.0
        edges = canny(gray / 255.0, sigma=2.0)
        if edges.sum() < 100:
            return 0.0

        angles = np.linspace(-MAX_ANGLE, MAX_ANGLE, 201)
        sinogram = radon(edges.astype(float), theta=90 + angles, circle=False)
        variances = sinogram.var(axis=0)
        return float(angles[variances.argmax()])
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────
# Individual Processing Steps
# ─────────────────────────────────────────────────────────────

def deskew(image: Image.Image, angle: float) -> Image.Image:
    """تصحیح کج‌شدگی با زاویه مشخص"""
    try:
        from skimage.transform import rotate

        gray = np.array(image.convert("L"))
        rotated = rotate(gray, angle, resize=False, cval=255, preserve_range=True)
        result = Image.fromarray(rotated.astype(np.uint8), mode="L").convert("RGB")
        logger.debug(f"  Deskew: rotated {angle:.2f}°")
        return result
    except Exception as e:
        logger.warning(f"  Deskew failed: {e}")
        return image


def denoise_light(image: Image.Image) -> Image.Image:
    """
    Denoise خفیف — فقط median filter ساده.
    نسبت به Gaussian denoise لبه‌های متن را بهتر نگه می‌دارد.
    """
    try:
        from PIL import ImageFilter
        return image.filter(ImageFilter.MedianFilter(size=3))
    except Exception as e:
        logger.warning(f"  Denoise failed: {e}")
        return image


def apply_clahe(image: Image.Image, clip_limit: float = 0.015) -> Image.Image:
    """
    CLAHE با clip_limit محافظه‌کارانه.
    فقط برای تصاویر واقعاً کم‌کنتراست یا خیلی تاریک.
    """
    try:
        from skimage.exposure import equalize_adapthist

        gray = np.array(image.convert("L"))
        enhanced = equalize_adapthist(gray, clip_limit=clip_limit)
        result_gray = (enhanced * 255).astype(np.uint8)
        # برگشت به RGB (EasyOCR روی RGB بهتر کار می‌کند)
        result = Image.fromarray(result_gray, mode="L").convert("RGB")
        logger.debug("  CLAHE applied")
        return result
    except Exception as e:
        logger.warning(f"  CLAHE failed: {e}")
        return image


def upscale_if_small(image: Image.Image, min_height: int = 800) -> Image.Image:
    """Upscale اگر تصویر کوچک است"""
    w, h = image.size
    if h < min_height:
        scale = min_height / h
        new_size = (int(w * scale), int(h * scale))
        logger.debug(f"  Upscaling {w}x{h} → {new_size[0]}x{new_size[1]}")
        return image.resize(new_size, Image.LANCZOS)
    return image


def binarize_sauvola(image: Image.Image) -> Image.Image:
    """
    بایناری‌سازی Sauvola — فقط برای re-OCR روی cropهای کوچک.
    برای تصویر کامل توصیه نمی‌شود.
    """
    try:
        from skimage.filters import threshold_sauvola

        gray = np.array(image.convert("L"))
        window = max(15, min(gray.shape) // 10) | 1
        thresh = threshold_sauvola(gray, window_size=window)
        binary = ((gray > thresh) * 255).astype(np.uint8)
        return Image.fromarray(binary, mode="L").convert("RGB")
    except Exception as e:
        logger.warning(f"  Sauvola failed: {e}")
        return image


# ─────────────────────────────────────────────────────────────
# Main adaptive pipeline
# ─────────────────────────────────────────────────────────────

def preprocess_for_ocr(
    image: Image.Image,
    force_deskew: Optional[bool] = None,
    force_denoise: Optional[bool] = None,
    force_clahe: Optional[bool] = None,
    min_height: int = 800,
) -> Image.Image:
    """
    Pipeline تطبیقی پیش‌پردازش تصویر برای OCR فارسی.

    هر مرحله فقط در صورت نیاز (بر اساس کیفیت تصویر) اعمال می‌شود.
    پارامترهای force_* برای override کردن تشخیص خودکار هستند.

    Args:
        image: PIL Image ورودی
        force_deskew: None=auto | True=همیشه | False=هرگز
        force_denoise: None=auto | True=همیشه | False=هرگز
        force_clahe:  None=auto | True=همیشه | False=هرگز
        min_height: حداقل ارتفاع قبل از upscale

    Returns:
        PIL Image پردازش‌شده
    """
    img = image.convert("RGB")

    # ① ارزیابی کیفیت
    quality = assess_image_quality(img)

    # ② Upscale در صورت نیاز (بی‌ضرر)
    img = upscale_if_small(img, min_height=min_height)

    # ③ Deskew فقط اگر واقعاً کج است
    do_deskew = force_deskew if force_deskew is not None else quality.needs_deskew
    if do_deskew:
        img = deskew(img, quality.skew_angle)

    # ④ Denoise فقط اگر نویز واقعاً بالاست
    do_denoise = force_denoise if force_denoise is not None else quality.needs_denoise
    if do_denoise:
        img = denoise_light(img)

    # ⑤ CLAHE فقط اگر کنتراست واقعاً کم است
    do_clahe = force_clahe if force_clahe is not None else quality.needs_clahe
    if do_clahe:
        img = apply_clahe(img)

    applied = []
    if do_deskew: applied.append(f"deskew({quality.skew_angle:.1f}°)")
    if do_denoise: applied.append("denoise")
    if do_clahe: applied.append("clahe")
    if not applied:
        logger.debug("  Preprocessing: no steps needed (image quality is sufficient)")
    else:
        logger.debug(f"  Preprocessing applied: {', '.join(applied)}")

    return img


def preprocess_crop_for_reocr(crop: Image.Image) -> Image.Image:
    """
    پیش‌پردازش برای ناحیه‌های low-confidence (re-OCR).
    روی cropهای کوچک: فقط upscale + Sauvola binarization.
    CLAHE و denoise اعمال نمی‌شود (در تجربه ضرر می‌زند).
    """
    img = upscale_if_small(crop, min_height=60)
    # Sauvola برای cropهای کوچک مفید است
    img = binarize_sauvola(img)
    return img
