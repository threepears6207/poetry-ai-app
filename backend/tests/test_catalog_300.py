import unittest

from scripts.import_poems_to_db import (
    MAX_TITLE_HAN_CHARACTERS,
    load_default_catalogs,
    title_han_character_count,
    validate_catalog,
)


class CatalogTitleLengthTests(unittest.TestCase):
    def test_default_catalog_contains_260_unique_complete_poems(self):
        poems, duplicates, raw_count, _ = load_default_catalogs()

        self.assertEqual(raw_count, 260)
        self.assertEqual(len(poems), 260)
        self.assertEqual(duplicates, [])
        self.assertEqual(validate_catalog(poems), [])
        self.assertEqual(len({poem["id"] for poem in poems}), 260)
        self.assertTrue(
            all(
                title_han_character_count(poem["title"]) <= MAX_TITLE_HAN_CHARACTERS
                for poem in poems
            )
        )

    def test_catalog_has_no_shortened_version_of_same_poem(self):
        poems, _, _, _ = load_default_catalogs()

        def normalized(value):
            return "".join(str(value).split()).replace("（节选）", "").replace("（扩展理解）", "")

        for index, left in enumerate(poems):
            for right in poems[index + 1:]:
                if normalized(left["title"]) != normalized(right["title"]):
                    continue
                if normalized(left["author"]) != normalized(right["author"]):
                    continue
                left_content = normalized("".join(left["content"]))
                right_content = normalized("".join(right["content"]))
                shorter, longer = sorted((left_content, right_content), key=len)
                self.assertFalse(
                    len(shorter) < len(longer) and shorter in longer,
                    f"发现同诗短版本：{left['id']} 与 {right['id']}",
                )


if __name__ == "__main__":
    unittest.main()
