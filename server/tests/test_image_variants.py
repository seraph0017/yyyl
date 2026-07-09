import tempfile
import unittest
from pathlib import Path

from PIL import Image

from utils.image_variants import (
    ImageVariantError,
    generate_image_variants,
    inspect_image_size,
    remove_image_variants,
    variant_path_for,
)


class ImageVariantsTest(unittest.TestCase):
    def test_generate_selected_variants_without_overwriting_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            images_root = Path(tmpdir)
            source = images_root / "cms" / "camp.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (1200, 800), color=(10, 80, 50)).save(source)

            thumb = variant_path_for(source, images_root=images_root, variant="thumb")
            thumb.parent.mkdir(parents=True)
            thumb.write_bytes(b"keep-existing-thumb")

            generated = generate_image_variants(
                source,
                images_root=images_root,
                variants=["large"],
                overwrite=False,
            )

            self.assertEqual(set(generated), {"large"})
            self.assertEqual(thumb.read_bytes(), b"keep-existing-thumb")
            self.assertTrue(variant_path_for(source, images_root=images_root, variant="large").exists())
            self.assertFalse(variant_path_for(source, images_root=images_root, variant="banner").exists())

    def test_invalid_image_raises_domain_error_and_cleanup_removes_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            images_root = Path(tmpdir)
            source = images_root / "cms" / "broken.jpg"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"not an image")

            thumb = variant_path_for(source, images_root=images_root, variant="thumb")
            thumb.parent.mkdir(parents=True)
            thumb.write_bytes(b"partial")

            with self.assertRaises(ImageVariantError):
                inspect_image_size(source)

            remove_image_variants(source, images_root=images_root)
            self.assertFalse(thumb.exists())

    def test_disguised_gif_is_rejected_by_content_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "fake.jpg"
            Image.new("RGB", (20, 20), color=(10, 80, 50)).save(source, format="GIF")

            with self.assertRaises(ImageVariantError) as ctx:
                inspect_image_size(source)

            self.assertIn("GIF", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
