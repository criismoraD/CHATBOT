import unittest
from unittest.mock import MagicMock
import sys

# Mocking missing dependencies before importing app.py
mock_modules = [
    "numpy", "torch", "torch.nn", "torch.utils", "torch.utils.data", "sklearn", "sklearn.model_selection", "sklearn.metrics", "sklearn.utils", "sklearn.utils.class_weight", "torch.nn", "torch.utils", "torch.utils.data", "sklearn", "sklearn.model_selection", "sklearn.metrics", "sklearn.utils", "sklearn.utils.class_weight", "flask", "flask_cors", "model_arch", "faster_whisper"
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import the function to test
from app import Obtener_Detalle_De_Inventario

class TestInventory(unittest.TestCase):

    def test_obtener_detalle_con_stock_normal(self):
        producto = {
            "name": "Producto Test",
            "tallas": ["M", "L"],
            "genero": "Hombre",
            "stock": 10
        }
        tallas, genero, stock_txt, stock_val = Obtener_Detalle_De_Inventario(producto)

        self.assertEqual(tallas, "M, L")
        self.assertEqual(genero, "Hombre")
        self.assertEqual(stock_txt, "10 unidades")
        self.assertEqual(stock_val, 10)

    def test_obtener_detalle_con_stock_vacio(self):
        # Edge case: stock 0
        producto = {
            "name": "Producto Sin Stock",
            "tallas": ["S"],
            "genero": "Mujer",
            "stock": 0
        }
        tallas, genero, stock_txt, stock_val = Obtener_Detalle_De_Inventario(producto)

        self.assertEqual(tallas, "S")
        self.assertEqual(genero, "Mujer")
        self.assertEqual(stock_txt, "0 unidades")
        self.assertEqual(stock_val, 0)

    def test_obtener_detalle_con_stock_faltante(self):
        # Edge case: stock key missing
        producto = {
            "name": "Producto Indeterminado",
            "tallas": ["L"],
            "genero": "Unisex"
        }
        tallas, genero, stock_txt, stock_val = Obtener_Detalle_De_Inventario(producto)

        self.assertEqual(stock_txt, "No disponible")
        self.assertIsNone(stock_val)

    def test_obtener_detalle_con_tallas_faltantes(self):
        # Edge case: tallas key missing
        producto = {
            "name": "Producto Talla Unica",
            "genero": "Unisex",
            "stock": 5
        }
        tallas, genero, stock_txt, stock_val = Obtener_Detalle_De_Inventario(producto)

        self.assertEqual(tallas, "Unica")
        self.assertEqual(stock_val, 5)

    def test_obtener_detalle_con_genero_faltante(self):
        # Edge case: genero key missing
        producto = {
            "name": "Producto Sin Genero",
            "tallas": ["M"],
            "stock": 3
        }
        tallas, genero, stock_txt, stock_val = Obtener_Detalle_De_Inventario(producto)

        self.assertEqual(genero, "Unisex")

if __name__ == '__main__':
    unittest.main()
