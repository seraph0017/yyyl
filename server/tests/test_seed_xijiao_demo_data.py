import unittest


from seed_xijiao_demo_data import _calculate_available, _json_value


class SeedXijiaoDemoDataTest(unittest.TestCase):
    def test_json_value_keeps_non_json_strings(self):
        self.assertEqual(_json_value("forest green"), "forest green")

    def test_json_value_parses_json_strings(self):
        self.assertEqual(_json_value('{"area": "A区"}'), {"area": "A区"})

    def test_calculate_available_preserves_used_inventory(self):
        self.assertEqual(_calculate_available(total=20, sold=3, locked=2), 15)

    def test_calculate_available_never_goes_negative(self):
        self.assertEqual(_calculate_available(total=2, sold=3, locked=1), 0)


if __name__ == "__main__":
    unittest.main()
