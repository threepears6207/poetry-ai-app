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
