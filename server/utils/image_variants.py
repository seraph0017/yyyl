"""
图片派生图生成工具。

上传图片时生成 thumb/large/banner 三套文件，供小程序按场景加载。
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


IMAGE_VARIANTS = {
    "thumb": {"max_side": 640, "quality": 72},
    "large": {"max_side": 1600, "quality": 82},
    "banner": {"max_side": 1400, "quality": 78},
}

SUPPORTED_VARIANT_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_DIMENSION = 8000
MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION


class ImageVariantError(ValueError):
    """图片无法安全生成派生图。"""


def is_supported_variant_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_VARIANT_EXTS


def variant_public_url(file_url: str, variant: str) -> str:
    """把 /images/foo.jpg 转成 /images/thumb/foo.jpg。"""
    if not file_url.startswith("/images/"):
        return file_url
    if file_url.startswith(("/images/thumb/", "/images/large/", "/images/banner/")):
        return file_url
    return file_url.replace("/images/", f"/images/{variant}/", 1)


def variant_path_for(image_path: Path, *, images_root: Path, variant: str) -> Path:
    relative_path = image_path.resolve().relative_to(images_root.resolve())
    return images_root / variant / relative_path


def _selected_variants(variants: Iterable[str] | None = None) -> list[str]:
    selected = list(variants or IMAGE_VARIANTS.keys())
    unknown = [variant for variant in selected if variant not in IMAGE_VARIANTS]
    if unknown:
        raise ImageVariantError(f"未知图片派生规格: {', '.join(unknown)}")
    return selected


def _load_normalized_image(image_path: Path) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(image_path) as raw_image:
                raw_image = ImageOps.exif_transpose(raw_image)
                width, height = raw_image.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    raise ImageVariantError("图片分辨率超过8000x8000限制")
                if width * height > MAX_IMAGE_PIXELS:
                    raise ImageVariantError("图片像素数量超过安全限制")
                raw_image.load()
                return raw_image.copy()
    except ImageVariantError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageVariantError("图片像素数量超过安全限制") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageVariantError("图片文件无法识别或已损坏") from exc


def inspect_image_size(image_path: Path) -> tuple[int, int]:
    """读取图片尺寸，同时完成安全解码校验。"""
    image = _load_normalized_image(image_path)
    try:
        return image.size
    finally:
        image.close()


def remove_image_variants(
    image_path: Path,
    *,
    images_root: Path,
    variants: Iterable[str] | None = None,
) -> None:
    """删除单张图片的 thumb/large/banner 派生文件。"""
    for variant in _selected_variants(variants):
        try:
            target_path = variant_path_for(image_path, images_root=images_root, variant=variant)
        except ValueError:
            continue
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            continue


def generate_image_variants(
    image_path: Path,
    *,
    images_root: Path,
    variants: Iterable[str] | None = None,
    overwrite: bool = True,
) -> dict[str, Path]:
    """为单张图片生成 thumb/large/banner 派生文件。"""
    if not is_supported_variant_image(image_path):
        return {}

    generated: dict[str, Path] = {}
    raw_image = _load_normalized_image(image_path)
    try:
        for variant in _selected_variants(variants):
            config = IMAGE_VARIANTS[variant]
            target_path = variant_path_for(image_path, images_root=images_root, variant=variant)
            if target_path.exists() and not overwrite:
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)

            image = raw_image.copy()
            try:
                max_side = int(config["max_side"])
                if max(image.size) > max_side:
                    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

                suffix = image_path.suffix.lower()
                if suffix in {".jpg", ".jpeg"}:
                    if image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")
                    image.save(
                        target_path,
                        format="JPEG",
                        quality=int(config["quality"]),
                        optimize=True,
                        progressive=True,
                    )
                elif suffix == ".png":
                    if image.mode not in ("RGB", "RGBA", "P", "L"):
                        image = image.convert("RGBA")
                    image.save(target_path, format="PNG", optimize=True, compress_level=9)
                elif suffix == ".webp":
                    if image.mode not in ("RGB", "RGBA"):
                        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                    image.save(
                        target_path,
                        format="WEBP",
                        quality=int(config["quality"]),
                        method=6,
                    )
                generated[variant] = target_path
            finally:
                image.close()
    finally:
        raw_image.close()
    return generated
