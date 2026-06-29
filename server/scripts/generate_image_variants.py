#!/usr/bin/env python3
"""
批量补齐图片派生图。

用法：
  cd /opt/yyyl/server
  python scripts/generate_image_variants.py

默认处理 images/ 下的原图，跳过 thumb/large/banner 和 qrcodes 目录。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.image_variants import IMAGE_VARIANTS, generate_image_variants, is_supported_variant_image, variant_path_for


SKIP_DIRS = set(IMAGE_VARIANTS) | {"qrcodes", "__pycache__"}


def iter_source_images(images_root: Path):
    for path in images_root.rglob("*"):
        if not path.is_file() or not is_supported_variant_image(path):
            continue
        relative_parts = path.relative_to(images_root).parts
        if relative_parts and relative_parts[0] in SKIP_DIRS:
            continue
        yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thumb/large/banner image variants.")
    parser.add_argument("--images-root", default="images", help="图片根目录，默认 images")
    parser.add_argument("--force", action="store_true", help="重新生成已存在的派生图")
    args = parser.parse_args()

    images_root = Path(args.images_root).resolve()
    if not images_root.is_dir():
        raise SystemExit(f"images root not found: {images_root}")

    source_images = list(iter_source_images(images_root))
    generated_count = 0
    skipped_count = 0
    failed_count = 0
    for image_path in source_images:
        missing = [
            variant
            for variant in IMAGE_VARIANTS
            if args.force or not variant_path_for(image_path, images_root=images_root, variant=variant).exists()
        ]
        if not missing:
            skipped_count += 1
            continue
        try:
            generated = generate_image_variants(
                image_path,
                images_root=images_root,
                variants=missing,
                overwrite=args.force,
            )
        except Exception as exc:
            failed_count += 1
            print(f"failed {image_path.relative_to(images_root)}: {exc}", file=sys.stderr)
            continue
        generated_count += 1
        generated_names = ",".join(generated.keys()) or "-"
        print(f"generated {image_path.relative_to(images_root)} variants={generated_names}")

    print(
        f"done source={len(source_images)} generated={generated_count} skipped={skipped_count} failed={failed_count} "
        f"root={images_root}"
    )
    if failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
