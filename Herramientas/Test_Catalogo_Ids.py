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

class TestCatalogoIds(unittest.TestCase):
    def setUp(self):
        # Mocking Datos_De_Productos
        catalogo.Datos_De_Productos = [
            {'id': 1, 'name': 'Producto 1'},
            {'id': 2, 'name': 'Producto 2'},
            {'id': 1, 'name': 'Producto 1 Duplicado'},
        ]
        catalogo.Reconstruir_Diccionario_De_Productos()

    def test_obtener_producto_existente(self):
        producto = catalogo.Obtener_Producto_Por_Id(2)
        self.assertIsNotNone(producto)
        self.assertEqual(producto['name'], 'Producto 2')

    def test_obtener_producto_duplicado_retorna_primero(self):
        # El comportamiento original era next(...) que retorna el primero encontrado
        producto = catalogo.Obtener_Producto_Por_Id(1)
        self.assertIsNotNone(producto)
        self.assertEqual(producto['name'], 'Producto 1')

    def test_obtener_producto_no_existente(self):
        producto = catalogo.Obtener_Producto_Por_Id(999)
        self.assertIsNone(producto)

    def test_obtener_producto_id_none(self):
        producto = catalogo.Obtener_Producto_Por_Id(None)
        self.assertIsNone(producto)

if __name__ == '__main__':
    unittest.main()
