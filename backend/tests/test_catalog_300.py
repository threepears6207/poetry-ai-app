import unittest

from scripts.import_poems_to_db import load_default_catalogs, validate_catalog


class Catalog300Tests(unittest.TestCase):
    def test_default_catalog_contains_300_unique_complete_poems(self):
        poems, duplicates, raw_count, _ = load_default_catalogs()

        self.assertEqual(raw_count, 300)
        self.assertEqual(len(poems), 300)
        self.assertEqual(duplicates, [])
        self.assertEqual(validate_catalog(poems), [])
        self.assertEqual(
            {poem["id"] for poem in poems},
            {f"poem_{index:03d}" for index in range(1, 301)},
        )


if __name__ == "__main__":
    unittest.main()
