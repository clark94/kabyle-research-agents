import unittest

from kabyle_agents.lang import detect_language
from kabyle_agents.normalize import dice, normalize, tokenize


class NormalizeTests(unittest.TestCase):
    def test_kabyle_letters_fold_to_ascii_variants(self):
        self.assertEqual(normalize("ɣef"), normalize("ghef"))
        self.assertEqual(normalize("taɛrabt"), normalize("ta3rabt"))
        self.assertEqual(normalize("aẓar ṭṭṣ ḥḍṛ č ǧ"), "azar tts hdr c g")

    def test_french_accents_and_ligatures(self):
        self.assertEqual(tokenize("Médecine, cœur"), ["medecine", "coeur"])

    def test_tifinagh_meets_latin(self):
        self.assertEqual(tokenize("ⴰⵎⴰⵡⴰⵍ ⵏ ⴷⴷⵡⴰ"), ["amawal", "n", "ddwa"])

    def test_typo_similarity(self):
        self.assertGreater(dice("dictionaire", "dictionnaire"), 0.8)
        self.assertLess(dice("cuisine", "dictionnaire"), 0.3)


class LanguageTests(unittest.TestCase):
    def test_detection(self):
        self.assertEqual(detect_language("un dictionnaire de la médecine").lang, "fr")
        self.assertEqual(detect_language("a dictionary of medicine").lang, "en")
        self.assertEqual(detect_language("amawal n ddwa").lang, "kab")
        self.assertEqual(detect_language("ⴰⵎⴰⵡⴰⵍ").lang, "kab")

    def test_unknown_is_undetermined_not_guessed(self):
        self.assertEqual(detect_language("kabyle medicine").lang, "und")


if __name__ == "__main__":
    unittest.main()
