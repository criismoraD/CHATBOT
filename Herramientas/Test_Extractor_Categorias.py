import unittest
from unittest.mock import MagicMock
import sys

# Mocking dependencies before importing extractor
mock_spacy = MagicMock()
sys.modules["spacy"] = mock_spacy
mock_thefuzz = MagicMock()
sys.modules["thefuzz"] = mock_thefuzz

import extractor

class Test_Extractor_Categorias(unittest.TestCase):

    def test_Inferir_Categoria_Calzado(self):
        """Debe inferir CALZADO para zapatillas."""
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Zapatilla Running"), "CALZADO")
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("botines de futbol"), "CALZADO")

    def test_Inferir_Categoria_Pantalones(self):
        """Debe inferir PANTALONES para pantalones y similares."""
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Pantalón deportivo"), "PANTALONES")
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("short de licra"), "PANTALONES")

    def test_Inferir_Categoria_Polos(self):
        """Debe inferir POLOS para camisetas y similares."""
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Camiseta Peru"), "POLOS")
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Bividi de algodon"), "POLOS")

    def test_Inferir_Categoria_Otros(self):
        """Debe inferir OTROS para mochilas y accesorios."""
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Mochila Urbana"), "OTROS")
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("Gorra plana"), "OTROS")

    def test_Normalizacion_Y_Acentos(self):
        """Debe manejar acentos y mayúsculas correctamente."""
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("PANTALÓN"), "PANTALONES")
        self.assertEqual(extractor.Inferir_Categoria_Desde_Nombre("zapatilla"), "CALZADO")

    def test_Casos_Borde_Vacios(self):
        """Debe retornar None para entradas vacías o sin palabras clave."""
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre(None))
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre(""))
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre("   "))
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre("Cualquier cosa"))

    def test_Evitar_Coincidencias_Parciales(self):
        """Debe evitar falsos positivos por sub-palabras (ej: 'top' en 'laptop')."""
        # 'top' es keyword de POLOS. 'laptop' no debería dispararlo.
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre("Funda para Laptop"))
        # 'short' es keyword de PANTALONES. 'shorter' (si existiera) no debería dispararlo si no es token exacto.
        self.assertIsNone(extractor.Inferir_Categoria_Desde_Nombre("Algo shorter"))

if __name__ == "__main__":
    unittest.main()
