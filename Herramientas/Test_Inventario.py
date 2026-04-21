import unittest
import sys
from unittest.mock import MagicMock

# Mocking dependencies
sys.modules['numpy'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.feature_extraction'] = MagicMock()
sys.modules['sklearn.feature_extraction.text'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()
sys.modules['sklearn.metrics.pairwise'] = MagicMock()
sys.modules['utils_nlp'] = MagicMock()
sys.modules['extractor'] = MagicMock()

import catalogo

class TestInventario(unittest.TestCase):
    def test_obtener_detalle_inventario(self):
        producto = {
            'id': 1,
            'name': 'Test',
            'tallas': ['S', 'M'],
            'genero': 'Mujer',
            'stock': 10
        }
        tallas, genero, stock_txt, stock_val = catalogo.Obtener_Detalle_De_Inventario(producto)
        self.assertEqual(tallas, 'S, M')
        self.assertEqual(genero, 'Mujer')
        self.assertEqual(stock_txt, '10 unidades')
        self.assertEqual(stock_val, 10)

    def test_obtener_detalle_inventario_sin_tallas(self):
        producto = {
            'id': 2,
            'name': 'Test 2',
            'stock': 5
        }
        tallas, genero, stock_txt, stock_val = catalogo.Obtener_Detalle_De_Inventario(producto)
        self.assertEqual(tallas, 'Unica')
        self.assertEqual(genero, 'Unisex')
        self.assertEqual(stock_val, 5)

if __name__ == '__main__':
    unittest.main()
