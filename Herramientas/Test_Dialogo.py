import unittest
from unittest.mock import MagicMock
import sys

import torch
import numpy
# Quitamos los mocks de torch y numpy para que el modelo IA en las pruebas cargue de verdad y haga inferencia
mock_modules = [
    "flask", "flask_cors", "faster_whisper"
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import extractor
import dialogo
import memoria
import catalogo

class TestFiltrosYDialogos(unittest.TestCase):

    def setUp(self):
        memoria.Memoria_Del_Chat.clear()

    def test_extraccion_filtros_no_matchea_y_con_jersey(self):
        msg = "y verdes ?"
        cat, col, prec, talla, gen = extractor.Extraer_Filtros(msg, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)

        self.assertIsNone(cat, f"No debería extraer categoría para 'y verdes ?' pero extrajo {cat}")
        self.assertEqual(col, "Verde")

    def test_herencia_de_contexto(self):
        session = "test_1"
        # 1. Ask for red shoes
        memoria.Actualizar_Contexto(session, "buscar_producto", {"category": "CALZADO", "color": "Rojo"})
        ctx = memoria.Obtener_Contexto(session)

        # 2. "y verdes ?"
        msg = "y verdes ?"
        cat_filtro, col_filtro, pre_filtro, tal_filtro, gen_filtro = extractor.Extraer_Filtros(msg, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)

        self.assertTrue(dialogo.Debe_Heredar_Filtros_De_Contexto(ctx, msg, cat_filtro, col_filtro, pre_filtro, tal_filtro, gen_filtro))

        cat_final, col_final, pre_final, tal_final, gen_final, kw_final = dialogo.Heredar_Filtros_De_Contexto(
            ctx, cat_filtro, col_filtro, pre_filtro, tal_filtro, gen_filtro, []
        )

        self.assertEqual(cat_final, "CALZADO", "Debe heredar CALZADO")
        self.assertEqual(col_final, "Verde", "El nuevo filtro de color debe sobrescribir")

    def test_busqueda_ampliada_con_multiples_filtros(self):
        # Escenario:
        # 1. quiero zapatillas rojas (buscar_producto, CALZADO, Rojo)
        # 2. talla 42 (buscar_producto, hereda CALZADO, hereda Rojo, Talla 42)
        # 3. y verdes? (buscar_producto, hereda CALZADO, hereda Talla 42, reemplaza Rojo por Verde)
        session = "test_2"
        memoria.Memoria_Del_Chat.clear()

        # 1
        msg1 = "quiero zapatillas rojas"
        cat1, col1, pre1, tal1, gen1 = extractor.Extraer_Filtros(msg1, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)
        self.assertEqual(cat1, "CALZADO")
        self.assertEqual(col1, "Rojo")
        memoria.Actualizar_Contexto(session, "buscar_producto", {"category": cat1, "color": col1, "talla": tal1, "max_price": pre1, "genero": gen1})

        # 2
        msg2 = "talla 42"
        cat2, col2, pre2, tal2, gen2 = extractor.Extraer_Filtros(msg2, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)
        self.assertEqual(tal2, "42")
        ctx = memoria.Obtener_Contexto(session)
        self.assertTrue(dialogo.Debe_Heredar_Filtros_De_Contexto(ctx, msg2, cat2, col2, pre2, tal2, gen2))

        cat2_f, col2_f, pre2_f, tal2_f, gen2_f, _ = dialogo.Heredar_Filtros_De_Contexto(ctx, cat2, col2, pre2, tal2, gen2, [])
        self.assertEqual(cat2_f, "CALZADO")
        self.assertEqual(col2_f, "Rojo")
        self.assertEqual(tal2_f, "42")
        memoria.Actualizar_Contexto(session, "buscar_producto", {"category": cat2_f, "color": col2_f, "talla": tal2_f, "max_price": pre2_f, "genero": gen2_f})

        # 3
        msg3 = "y verdes?"
        cat3, col3, pre3, tal3, gen3 = extractor.Extraer_Filtros(msg3, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)
        self.assertEqual(col3, "Verde")
        ctx = memoria.Obtener_Contexto(session)
        self.assertTrue(dialogo.Debe_Heredar_Filtros_De_Contexto(ctx, msg3, cat3, col3, pre3, tal3, gen3))

        cat3_f, col3_f, pre3_f, tal3_f, gen3_f, _ = dialogo.Heredar_Filtros_De_Contexto(ctx, cat3, col3, pre3, tal3, gen3, [])
        self.assertEqual(cat3_f, "CALZADO")
        self.assertEqual(col3_f, "Verde")
        self.assertEqual(tal3_f, "42")

    def test_cambio_total_de_tema(self):
        session = "test_3"
        memoria.Memoria_Del_Chat.clear()
        memoria.Actualizar_Contexto(session, "buscar_producto", {"category": "CALZADO", "color": "Rojo", "talla": "42"})

        msg = "tienes buzos?"
        cat, col, pre, tal, gen = extractor.Extraer_Filtros(msg, catalogo.Categorias_Dinamicas, catalogo.Colores_Dinamicos)
        self.assertEqual(cat, "PANTALONES")

        ctx = memoria.Obtener_Contexto(session)
        debe_heredar = dialogo.Debe_Heredar_Filtros_De_Contexto(ctx, msg, cat, col, pre, tal, gen)

        # Si debe_heredar es True (porque len(tokens) <= 4), entonces Heredar_Filtros_De_Contexto
        # necesita NO sobreescribir color o talla de otra categoria si no es explicitamente pedido,
        # PERO para simplificar en dialogo.py podemos decir que NO herede si la categoría cambia
        # o limpiar los incompatibles.

        # En este test esperamos que si se cambian los filtros no se hereden los viejos colores
        cat_f, col_f, pre_f, tal_f, gen_f, kw_f = dialogo.Heredar_Filtros_De_Contexto(ctx, cat, col, pre, tal, gen, [])
        self.assertEqual(cat_f, "PANTALONES")
        # El test deberia asegurar que col_f no sea Rojo y tal_f no sea 42
        self.assertIsNone(col_f)
        self.assertIsNone(tal_f)

    def test_interacciones_variadas(self):
        session = "test_largo"
        memoria.Memoria_Del_Chat.clear()

        # 1. zapatillas rojas (CALZADO, Rojo)
        msg1 = "tienes zapatillas rojas?"
        ans1, tag1, ctx1 = dialogo.Obtener_Respuesta_Principal(session, msg1)
        self.assertEqual(ctx1["category"], "CALZADO")
        self.assertEqual(ctx1["color"], "Rojo")

        # 2. soporte / ayuda -> tag 'reclamos' o 'fuera_de_dominio', etc. Should not clear filter yet (unless restart filter explicit)
        msg2 = "necesito ayuda con mi cuenta"
        ans2, tag2, ctx2 = dialogo.Obtener_Respuesta_Principal(session, msg2)
        # Should detect tag like 'reclamos' or 'fuera_de_dominio' based on training, here we don't care about the tag,
        # but the context filters should be preserved if not overridden.
        self.assertNotIn(tag2, ["buscar_producto", "colores"])

        # 3. "y verdes?" -> debe volver a buscar producto con CALZADO y Verde
        msg3 = "y verdes?"
        ans3, tag3, ctx3 = dialogo.Obtener_Respuesta_Principal(session, msg3)
        self.assertEqual(tag3, "buscar_producto")
        self.assertEqual(ctx3["category"], "CALZADO")
        self.assertEqual(ctx3["color"], "Verde")

    def test_interrupcion_de_memoria_por_otras_intenciones(self):
        # 1. zapatillas rojas (buscar_producto)
        # 2. soporte / reclamos (fuera de dominio o reclamos)
        # 3. y verdes? (buscar_producto, debe heredar zapatillas)
        session = "test_largo"
        memoria.Memoria_Del_Chat.clear()

        # 1. zapatillas rojas
        msg1 = "tienes zapatillas rojas?"
        ans1, tag1, ctx1 = dialogo.Obtener_Respuesta_Principal(session, msg1)
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["category"], "CALZADO")
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["color"], "Rojo")

        # 2. soporte
        msg2 = "necesito ayuda con mi cuenta"
        ans2, tag2, ctx2 = dialogo.Obtener_Respuesta_Principal(session, msg2)
        # filters in memory should remain intact
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["category"], "CALZADO")
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["color"], "Rojo")

        # 3. y verdes
        msg3 = "y verdes?"
        ans3, tag3, ctx3 = dialogo.Obtener_Respuesta_Principal(session, msg3)
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["category"], "CALZADO")
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["color"], "Verde")


    def test_reinicio_de_filtros(self):
        # 1. zapatillas rojas (buscar_producto)
        # 2. reinicia filtros / busquemos otra cosa
        # 3. zapatos
        session = "test_reinicio"
        memoria.Memoria_Del_Chat.clear()

        # 1. zapatillas rojas
        msg1 = "quiero zapatos rojos"
        ans1, tag1, ctx1 = dialogo.Obtener_Respuesta_Principal(session, msg1)
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["category"], "CALZADO")
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["color"], "Rojo")

        # 2. busquemos otra cosa
        msg2 = "busquemos otra cosa"
        ans2, tag2, ctx2 = dialogo.Obtener_Respuesta_Principal(session, msg2)
        # The filter action returned should have empty keywords and None category
        self.assertEqual(tag2, "buscar_producto")
        self.assertIsNone(memoria.Obtener_Contexto(session)["last_filters"]["category"])

        # 3. polos
        msg3 = "polos verdes"
        ans3, tag3, ctx3 = dialogo.Obtener_Respuesta_Principal(session, msg3)
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["category"], "POLOS")
        self.assertEqual(memoria.Obtener_Contexto(session)["last_filters"]["color"], "Verde")

if __name__ == '__main__':
    unittest.main()

    def test_interacciones_extensas(self):
        session = "test_muy_largo"
        memoria.Memoria_Del_Chat.clear()

        # 1. pantalones azules
        msg1 = "pantalones azules"
        ans1, tag1, ctx1 = dialogo.Obtener_Respuesta_Principal(session, msg1)
        self.assertEqual(ctx1["category"], "PANTALONES")

        # 2. talla s
        msg2 = "talla s"
        ans2, tag2, ctx2 = dialogo.Obtener_Respuesta_Principal(session, msg2)
        self.assertEqual(ctx2["talla"], "S")
        self.assertEqual(ctx2["category"], "PANTALONES")

        # 3. y verdes?
        msg3 = "y verdes?"
        ans3, tag3, ctx3 = dialogo.Obtener_Respuesta_Principal(session, msg3)
        self.assertEqual(ctx3["color"], "Verde")
        self.assertEqual(ctx3["category"], "PANTALONES")

        # 4. polos
        msg4 = "polos"
        ans4, tag4, ctx4 = dialogo.Obtener_Respuesta_Principal(session, msg4)
        self.assertEqual(ctx4["category"], "POLOS")
        self.assertIsNone(ctx4["color"], "No debe heredar color verde porque cambiamos categoria explícitamente sin conectores")
        self.assertIsNone(ctx4["talla"], "No debe heredar talla S porque cambiamos categoria explícitamente sin conectores")

        # 5. y zapatillas rojas
        msg5 = "y zapatillas rojas"
        ans5, tag5, ctx5 = dialogo.Obtener_Respuesta_Principal(session, msg5)
        self.assertEqual(ctx5["category"], "CALZADO")
        self.assertEqual(ctx5["color"], "Rojo")

        # 6. promociones
        msg6 = "tienen promociones?"
        ans6, tag6, ctx6 = dialogo.Obtener_Respuesta_Principal(session, msg6)

        # 7. negros
        msg7 = "y negros?"
        ans7, tag7, ctx7 = dialogo.Obtener_Respuesta_Principal(session, msg7)
        self.assertEqual(ctx7["category"], "CALZADO")
        self.assertEqual(ctx7["color"], "Negro")

    def test_consulta_de_stock_y_luego_colores(self):
        session = "test_stock_colores"
        memoria.Memoria_Del_Chat.clear()

        # 1. zapatillas blancas
        msg1 = "quiero zapatillas blancas"
        ans1, tag1, ctx1 = dialogo.Obtener_Respuesta_Principal(session, msg1)
        self.assertEqual(ctx1["category"], "CALZADO")
        self.assertEqual(ctx1["color"], "Blanco")

        # 2. y negras?
        msg2 = "y negras?"
        ans2, tag2, ctx2 = dialogo.Obtener_Respuesta_Principal(session, msg2)
        self.assertEqual(ctx2["category"], "CALZADO")
        self.assertEqual(ctx2["color"], "Negro")

        # 3. tienes stock? (Debe consultar stock_item o disponibilidad, y en la implementacion actual,
        # si hay filtros puede buscar, o puede decir que indiquemos el item. Como hay filtros, busca productos)
        msg3 = "tienes en talla 40?"
        ans3, tag3, ctx3 = dialogo.Obtener_Respuesta_Principal(session, msg3)
        self.assertEqual(ctx3["talla"], "40")
        self.assertEqual(ctx3["category"], "CALZADO")

if __name__ == '__main__':
    unittest.main()
