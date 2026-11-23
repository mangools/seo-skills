import unittest

from support import mangools

slug = mangools._slug


class SlugTest(unittest.TestCase):
    def test_lowercases_and_keeps_letters_of_every_script_as_typed(self):
        cases = {
            "Gartenmöbel Lounge": "gartenmöbel-lounge",
            "Gartenmöbel Lounge": "gartenmöbel-lounge",
            "купити диван": "купити-диван",
        }
        for keyword, expected in cases.items():
            with self.subTest(keyword):
                self.assertEqual(slug(keyword), expected)

    def test_adds_code_when_punctuation_was_dropped(self):
        self.assertEqual(slug("c tutorial"), "c-tutorial")
        self.assertRegex(slug("c++ tutorial"), r"^c-tutorial-[0-9a-f]{6}$")

    def test_adds_code_past_sixty_characters(self):
        self.assertEqual(slug("a" * 60), "a" * 60)
        self.assertRegex(slug("a" * 61), r"^a{60}-[0-9a-f]{6}$")


if __name__ == "__main__":
    unittest.main()
