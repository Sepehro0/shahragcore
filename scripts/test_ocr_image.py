# -*- coding: utf-8 -*-
"""
مقایسه OCR قبل و بعد از بهبودها + نمایش layout هدر/فوتر
"""

import sys, os, time
import numpy as np
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

IMAGE_PATH = os.path.join(PROJECT_ROOT, "archive", "data_files", "ocr-image-persian-test.jpg")
SEP = "=" * 70

def sec(t): print(f"\n{SEP}\n  {t}\n{SEP}")


# ─── BEFORE: OCR خام ───────────────────────────────────────────────────────
def run_before(img_array, reader):
    t = time.time()
    results = reader.readtext(img_array, detail=1, paragraph=False,
                              min_size=10, text_threshold=0.5,
                              low_text=0.3, link_threshold=0.3)
    elapsed = time.time() - t
    text = " ".join(tx for _, tx, conf in results if conf >= 0.5 and tx.strip())
    high_conf = [r for r in results if r[2] >= 0.5]
    return results, high_conf, text, elapsed


# ─── AFTER: OCR با pipeline کامل ──────────────────────────────────────────
def run_after(image, reader):
    from ocr_processor.ocr_image_preprocessor import (
        preprocess_for_ocr, preprocess_crop_for_reocr, assess_image_quality
    )
    from ocr_processor.ocr_text_postprocessor import (
        postprocess_ocr_text, reconstruct_rtl_lines, postprocess_token,
        detect_layout_regions
    )
    from ocr_processor.ocr_pdf_processor import BoundingBox, OCRResult

    t = time.time()
    w, h = image.size

    # ① ارزیابی کیفیت (بدون هزینه OCR)
    quality = assess_image_quality(image)
    print(f"  📊 Image quality: brightness={quality.brightness:.2f}, "
          f"contrast={quality.contrast:.2f}, noise={quality.noise_level:.4f}, "
          f"skew={quality.skew_angle:.2f}°")
    print(f"  🔧 Preprocessing needs: deskew={quality.needs_deskew}, "
          f"denoise={quality.needs_denoise}, clahe={quality.needs_clahe}")

    # ② Adaptive preprocessing
    processed = preprocess_for_ocr(image)
    img_array = np.array(processed)

    # ③ OCR اصلی
    raw_results = reader.readtext(img_array, detail=1, paragraph=False,
                                  min_size=10, text_threshold=0.5,
                                  low_text=0.3, link_threshold=0.3)

    # ④ Re-OCR با آستانه معنادار
    improved = list(raw_results)
    low_conf = [(i, r) for i, r in enumerate(raw_results)
                if 0.20 <= r[2] < 0.4 and r[1].strip()]
    reocr_count = 0
    for idx, (bbox_pts, orig_text, orig_conf) in low_conf:
        try:
            x1 = max(0, int(min(p[0] for p in bbox_pts)) - 6)
            y1 = max(0, int(min(p[1] for p in bbox_pts)) - 6)
            x2 = min(w, int(max(p[0] for p in bbox_pts)) + 6)
            y2 = min(h, int(max(p[1] for p in bbox_pts)) + 6)
            if (x2-x1) < 8 or (y2-y1) < 8: continue
            crop_arr = np.array(preprocess_crop_for_reocr(image.crop((x1,y1,x2,y2))))
            reocr = reader.readtext(crop_arr, detail=1, paragraph=False,
                                    min_size=5, text_threshold=0.3, low_text=0.2)
            if reocr:
                best = max(reocr, key=lambda r: r[2])
                _, new_text, new_conf = best
                if new_text.strip() and new_conf >= 0.45 and new_conf > orig_conf + 0.15:
                    improved[idx] = (bbox_pts, new_text, new_conf)
                    reocr_count += 1
        except Exception: pass
    print(f"  🔄 Re-OCR improved {reocr_count} regions")

    # ⑤ تبدیل به OCRResult
    ocr_objs = []
    for bbox_pts, text, conf in improved:
        text = postprocess_token(text.strip())
        if not text: continue
        xc = [p[0] for p in bbox_pts]; yc = [p[1] for p in bbox_pts]
        bbox = BoundingBox(int(min(xc)), int(min(yc)), int(max(xc)), int(max(yc)), page=1)
        ocr_objs.append(OCRResult(text=text, confidence=conf, bbox=bbox))

    # ⑥ Layout detection: header / body / footer
    layout = detect_layout_regions(ocr_objs, page_height=h, page_width=w,
                                   header_ratio=0.13, footer_ratio=0.10,
                                   use_content_hints=True)

    elapsed = time.time() - t
    high_conf = [r for r in improved if r[2] >= 0.5]
    return improved, high_conf, layout, ocr_objs, elapsed


# ─── آمار ─────────────────────────────────────────────────────────────────
def stats(label, all_r, high_r, elapsed):
    confs = [c for _,_,c in all_r]
    if not confs: return
    print(f"\n[{label}]")
    print(f"  تعداد ناحیه کل   : {len(all_r)}")
    print(f"  ناحیه conf≥0.5   : {len(high_r)}")
    print(f"  میانگین conf      : {sum(confs)/len(confs):.3f}")
    print(f"  max/min conf      : {max(confs):.3f} / {min(confs):.3f}")
    print(f"  زمان              : {elapsed:.2f}s")

# ─── main ─────────────────────────────────────────────────────────────────
def main():
    from PIL import Image
    import easyocr

    sec("بارگذاری")
    image = Image.open(IMAGE_PATH).convert("RGB")
    img_array = np.array(image)
    print(f"✅ Image: {image.size[0]}x{image.size[1]} px")
    reader = easyocr.Reader(["fa", "en"], gpu=True, verbose=False)
    print("✅ EasyOCR ready")

    # ── BEFORE ──────────────────────────────────────────────
    sec("BEFORE — OCR خام")
    r_b, h_b, text_b, t_b = run_before(img_array, reader)
    print("\n--- متن BEFORE (همه توکن‌ها join شده) ---")
    print(text_b)
    stats("BEFORE", r_b, h_b, t_b)

    # ── AFTER ───────────────────────────────────────────────
    sec("AFTER — Adaptive preprocessing + Re-OCR + Layout")
    r_a, h_a, layout, ocr_objs, t_a = run_after(image, reader)

    sec("متن AFTER — فقط Body (بدون هدر و فوتر)")
    print(layout.body_text)

    sec("هدر (Header) — شناسایی‌شده")
    print(layout.header_text if layout.header_text else "(هدری شناسایی نشد)")

    sec("فوتر (Footer) — شناسایی‌شده")
    print(layout.footer_text if layout.footer_text else "(فوتری شناسایی نشد)")

    sec("متن کامل AFTER (هدر + body + فوتر)")
    print(layout.full_text(include_header=True, include_footer=True))

    stats("AFTER", r_a, h_a, t_a)
    print(f"\n  Layout: header={layout.summary()['header_lines']} ناحیه | "
          f"body={layout.summary()['body_lines']} ناحیه | "
          f"footer={layout.summary()['footer_lines']} ناحیه")

    # ── مقایسه نهایی ────────────────────────────────────────
    sec("خلاصه مقایسه BEFORE vs AFTER")
    avg_b = sum(c for _,_,c in r_b)/len(r_b) if r_b else 0
    avg_a = sum(c for _,_,c in r_a)/len(r_a) if r_a else 0
    delta = avg_a - avg_b
    sym = "▲" if delta > 0 else ("▼" if delta < 0 else "═")
    print(f"  ناحیه کل         : {len(r_b)} → {len(r_a)}")
    print(f"  ناحیه conf≥0.5   : {len(h_b)} → {len(h_a)}")
    print(f"  میانگین conf      : {avg_b:.3f} → {avg_a:.3f}  {sym}{abs(delta):.3f}")
    print(f"  زمان              : {t_b:.2f}s → {t_a:.2f}s")
    print(f"\n  ✅ بهبود کیفی (AFTER):")
    print(f"     - متن ساختاریافته با پاراگراف‌بندی (RTL هوشمند)")
    print(f"     - حروف نرمال‌شده: ك→ک، ي→ی، ة→ه")
    print(f"     - هدر شناسایی و جدا شد: {layout.summary()['header_lines']} ناحیه")
    print(f"     - فوتر شناسایی و جدا شد: {layout.summary()['footer_lines']} ناحیه")
    print()

if __name__ == "__main__":
    main()
