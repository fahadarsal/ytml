import unittest
from parser import YTMLParser


class TestYTMLParser(unittest.TestCase):
    def test_basic_parsing(self):
        parser = YTMLParser("backend/interpretron/samples/basic.ytml")
        result = parser.parse()
        self.assertIn("segments", result)

    def test_voice_parsing(self):
        parser = YTMLParser("backend/interpretron/samples/voice.ytml")
        result = parser.parse()
        self.assertEqual(result["segments"][0]
                         ["voiceovers"][0]["text"], "Hello!")

    def test_music_parsing(self):
        parser = YTMLParser("backend/interpretron/samples/music.ytml")
        result = parser.parse()
        self.assertEqual(result["segments"][0]["music"]
                         [0]["src"], "background.mp3")

    def test_dynamic_timing(self):
        parser = YTMLParser("backend/interpretron/samples/dynamic_timing.ytml")
        result = parser.parse()
        self.assertEqual(result["segments"][0]["voiceovers"][0]["start"], 1.0)

    def test_template_expansion(self):
        parser = YTMLParser("backend/interpretron/samples/template.ytml")
        result = parser.parse()
        print(result)
        self.assertIn("<div class='logo'>My Brand</div>",
                      result["segments"][0]["frames"][0])

    def test_error_handling(self):
        parser = YTMLParser(
            "backend/interpretron/samples/invalid_template.ytml")
        with self.assertRaises(ValueError):
            parser.parse()


if __name__ == "__main__":
    unittest.main()
