import unittest

from schemas.order import OrderCreateRequest


class OrderCreateRequestTest(unittest.TestCase):
    def test_accepts_legacy_direct_order_payload(self):
        request = OrderCreateRequest.model_validate(
            {
                "product_id": 2,
                "dates": ["2026-06-12"],
                "quantity": 1,
                "identity_id": 5,
            }
        )

        self.assertEqual(len(request.items), 1)
        self.assertEqual(request.items[0].product_id, 2)
        self.assertEqual(request.items[0].quantity, 1)
        self.assertEqual(request.items[0].identity_ids, [5])
        self.assertTrue(request.disclaimer_signed)

    def test_keeps_explicit_legacy_disclaimer_value(self):
        request = OrderCreateRequest.model_validate(
            {
                "product_id": 2,
                "dates": ["2026-06-12"],
                "quantity": 1,
                "disclaimer_signed": False,
            }
        )

        self.assertFalse(request.disclaimer_signed)


if __name__ == "__main__":
    unittest.main()
