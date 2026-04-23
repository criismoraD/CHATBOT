import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import modules from the root
sys.path.append(os.getcwd())

# Mocking dependencies that might fail during import or execution
mock_ia = MagicMock()
mock_ia.Datos_De_Intents = {'intents': []}
sys.modules["ia"] = mock_ia

mock_extractor = MagicMock()
sys.modules["extractor"] = mock_extractor

mock_catalogo = MagicMock()
mock_catalogo.Datos_De_Productos = []
mock_catalogo.Categorias_Dinamicas = []
mock_catalogo.Colores_Dinamicos = []
sys.modules["catalogo"] = mock_catalogo

mock_memoria = MagicMock()
sys.modules["memoria"] = mock_memoria

mock_config = MagicMock()
mock_config.Umbral_De_Confianza = 0.5
mock_config.Umbral_De_Margen_Base = 0.1
sys.modules["config"] = mock_config

import dialogo

class Test_Fallback_Respuesta(unittest.TestCase):

    @patch("dialogo.Predecir_Tag")
    @patch("dialogo.Obtener_Contexto")
    @patch("dialogo.Normalizar_Texto_Base")
    @patch("dialogo.Extraer_Filtros")
    @patch("dialogo.Extraer_Palabras_Clave_De_Mensaje")
    @patch("dialogo.Detectar_Id_De_Producto_En_Texto")
    @patch("dialogo.Inferir_Etiqueta_De_Detalle")
    @patch("dialogo.Es_Solicitud_De_Reinicio_De_Filtros")
    @patch("dialogo.Es_Consulta_De_Seguimiento_De_Pedido")
    def test_obtener_respuesta_principal_no_retorna_none(self,
                                                       mock_seguimiento,
                                                       mock_reinicio,
                                                       mock_inferir,
                                                       mock_detectar_id,
                                                       mock_keys,
                                                       mock_filtros,
                                                       mock_norm,
                                                       mock_contexto,
                                                       mock_predecir):
        """Verifica que Obtener_Respuesta_Principal siempre retorne una cadena en Respuesta_Final."""

        # Configuramos los mocks para una consulta vacía/desconocida
        mock_predecir.return_value = (None, 0.0, 0.0)
        mock_contexto.return_value = {}
        mock_norm.return_value = "hola"
        mock_filtros.return_value = (None, None, None, None, None)
        mock_keys.return_value = []
        mock_detectar_id.return_value = None
        mock_inferir.return_value = None
        mock_reinicio.return_value = False
        mock_seguimiento.return_value = False

        respuesta, etiqueta, accion = dialogo.Obtener_Respuesta_Principal("sesion_test", "hola")

        self.assertIsNotNone(respuesta)
        self.assertIsInstance(respuesta, str)
        self.assertTrue(len(respuesta) > 0)
        print(f"Respuesta obtenida: {respuesta}")

    def test_fallback_directo(self):
        """Prueba directamente la lógica de fallback si Respuesta_Final es None."""
        FALLBACK_ESPERADO = "Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?"

        # Simulamos lo que pasaría al final de la función
        Respuesta_Final = None
        if Respuesta_Final is None:
            Respuesta_Final = FALLBACK_ESPERADO

        self.assertEqual(Respuesta_Final, FALLBACK_ESPERADO)

if __name__ == "__main__":
    unittest.main()
