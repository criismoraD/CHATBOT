import unittest
from unittest.mock import MagicMock, patch
import sys

# Mocking spacy to avoid ModuleNotFoundError and network calls during tests
mock_spacy = MagicMock()
mock_nlp = MagicMock()
mock_spacy.load.return_value = mock_nlp

# Mock vocab to support nlp.vocab[palabra].is_stop = False
class Mock_Vocab(dict):
    def __getitem__(self, item):
        if item not in self:
            self[item] = MagicMock()
        return super().__getitem__(item)

mock_nlp.vocab = Mock_Vocab()

sys.modules["spacy"] = mock_spacy

# Import the module to test
import utils_nlp

class Test_Utils_Nlp(unittest.TestCase):

    def setUp(self):
        # Clear the mock nlp calls before each test
        mock_nlp.reset_mock()
        # Set the mock nlp object in the module
        utils_nlp.nlp = mock_nlp

    def _Crear_Mock_Token(self, text, lemma, is_stop=False, is_punct=False):
        """Helper to create a mock spaCy token."""
        token = MagicMock()
        token.text = text
        token.lemma_ = lemma
        token.is_stop = is_stop
        token.is_punct = is_punct
        return token

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Vacio(self, mock_limpiar):
        """Test with an empty string."""
        mock_limpiar.return_value = ""
        mock_nlp.return_value = []
        resultado = utils_nlp.tokenizar_y_lematizar("")
        self.assertEqual(resultado, [])

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Puntuacion(self, mock_limpiar):
        """Test with only punctuation and special characters."""
        mock_limpiar.return_value = ""
        mock_nlp.return_value = []
        resultado = utils_nlp.tokenizar_y_lematizar("!!! @#$")
        self.assertEqual(resultado, [])

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Stop_Words(self, mock_limpiar):
        """Test that stop words are correctly filtered out."""
        mock_limpiar.return_value = "el la"
        t1 = self._Crear_Mock_Token("el", "el", is_stop=True)
        t2 = self._Crear_Mock_Token("la", "la", is_stop=True)
        mock_nlp.return_value = [t1, t2]

        resultado = utils_nlp.tokenizar_y_lematizar("el la")
        self.assertEqual(resultado, [])

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Tokens_Cortos(self, mock_limpiar):
        """Test that tokens with length <= 1 are filtered out."""
        mock_limpiar.return_value = "a b"
        t1 = self._Crear_Mock_Token("a", "a")
        t2 = self._Crear_Mock_Token("b", "b")
        mock_nlp.return_value = [t1, t2]

        resultado = utils_nlp.tokenizar_y_lematizar("a b")
        self.assertEqual(resultado, [])

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Caso_Normal(self, mock_limpiar):
        """Test a normal sentence with expected tokens and bigrams."""
        mock_limpiar.return_value = "pantalones azules"
        t1 = self._Crear_Mock_Token("pantalones", "pantalon")
        t2 = self._Crear_Mock_Token("azules", "azul")
        mock_nlp.return_value = [t1, t2]

        resultado = utils_nlp.tokenizar_y_lematizar("pantalones azules")
        # Expected: tokens [pantalon, azul] + bigram [pantalon_azul]
        self.assertEqual(resultado, ["pantalon", "azul", "pantalon_azul"])

    @patch("utils_nlp.limpiar_texto")
    def test_Tokenizar_Y_Lematizar_Mezclado(self, mock_limpiar):
        """Test a mix of valid tokens, stop words, and short tokens."""
        mock_limpiar.return_value = "el polo y la falda"
        t1 = self._Crear_Mock_Token("el", "el", is_stop=True)
        t2 = self._Crear_Mock_Token("polo", "polo")
        t3 = self._Crear_Mock_Token("y", "y", is_stop=True)
        t4 = self._Crear_Mock_Token("la", "la", is_stop=True)
        t5 = self._Crear_Mock_Token("falda", "falda")
        mock_nlp.return_value = [t1, t2, t3, t4, t5]

        resultado = utils_nlp.tokenizar_y_lematizar("el polo y la falda")
        self.assertEqual(resultado, ["polo", "falda", "polo_falda"])

if __name__ == "__main__":
    unittest.main()
