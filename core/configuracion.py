"""
core/configuracion.py · Configuración Global del Chatbot
═══════════════════════════════════════════════════════

Centraliza TODAS las constantes, rutas y parámetros del sistema.
Ningún otro módulo debe tener configuración hardcodeada; todo se define aquí.

CONTENIDO:
  - Rutas de archivos (modelo LSTM, intents JSON, memoria)
  - Credenciales de MySQL (leídas de env o con defaults)
  - Nombre del bot y fuentes de catálogo
  - Umbrales de confianza del modelo de IA
  - Límites de búsqueda y historial de chat

USO:
  from core.configuracion import Nombre_Del_Bot, Umbral_De_Confianza
"""

import os


# ─── Rutas de Archivos ────────────────────────────────────────────────────────

Ruta_Modelo_Pytorch = "data/modelo_lstm.pth"
Ruta_Intents = "data/intenciones_chatbot.json"
Ruta_Productos_Scrapeados = "data/products_scraped.json"
Ruta_Memoria_Del_Chat = "data/chat_memory"


# ─── CORS ─────────────────────────────────────────────────────────────────────

def Obtener_Origenes_Cors_Permitidos():
    Valor_De_Entorno = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000"
    )
    Origenes = [Origen.strip() for Origen in Valor_De_Entorno.split(',') if Origen.strip()]
    if Origenes:
        return Origenes
    return ["http://localhost:5000", "http://127.0.0.1:5000"]


Origenes_Cors_Permitidos = Obtener_Origenes_Cors_Permitidos()


# ─── Base de Datos MySQL ─────────────────────────────────────────────────────

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "chatbot_tienda"


# ─── Bot ─────────────────────────────────────────────────────────────────────

Nombre_Del_Bot = os.getenv("BOT_NAME", "Asistente SENATI")
Fuentes_De_Catalogo_Validas = {"scraped"}


# ─── Modelo de IA ────────────────────────────────────────────────────────────

Umbral_De_Confianza = 0.75
Umbral_De_Margen_Base = 0.08
Umbral_De_Margen_Por_Tag = {
    "buscar_producto": 0.10,
    "colores": 0.10,
    "consultar_stock_item": 0.10,
    "fuera_de_dominio": 0.12,
}


# ─── Chat y Búsqueda ─────────────────────────────────────────────────────────

Maximo_Historial_Chat = 10
Limite_Busqueda_Por_Defecto = 20
Maximo_Limite_De_Busqueda = 50
