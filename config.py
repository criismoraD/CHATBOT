# ─── Modelo y datos ──────────────────────────────────────────────────────────
Ruta_Modelo_Pytorch        = "data/model.pth"
Ruta_Intents               = "data/intents.json"
Ruta_Productos_Scrapeados  = "data/products_scraped.json"   # respaldo JSON (opcional)
Fuentes_De_Catalogo_Validas = {"scraped"}

# ─── Parámetros del chatbot ───────────────────────────────────────────────────
Umbral_De_Confianza     = 0.75
Umbral_De_Margen_Base   = 0.08
Umbral_De_Margen_Por_Tag = {
    "buscar_producto"      : 0.10,
    "colores"              : 0.10,
    "consultar_stock_item" : 0.10,
    "fuera_de_dominio"     : 0.12,
}
Maximo_Historial_Chat        = 10
Limite_Busqueda_Por_Defecto  = 20
Maximo_Limite_De_Busqueda    = 50

# ─── MySQL ────────────────────────────────────────────────────────────────────
# Puedes sobreescribir estos valores con variables de entorno:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = ""          # <- cambia por tu contraseña
DB_NAME     = "chatbot_tienda"

# Preferencia de fuente de catalogo: "mysql" (recomendado) o "json" (respaldo)
DB_FUENTE_CATALOGO = "mysql"
