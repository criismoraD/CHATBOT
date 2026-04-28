"""
bot/memoria.py  ·  Memoria de Conversación del Chatbot
-------------------------------------------------------
Mantiene el contexto de cada sesión de chat:
  - Último tag detectado
  - Filtros de búsqueda activos
  - Producto seleccionado
  - Fuente de catálogo activa
"""

from core import config
from bot.catalogo_productos import Fuente_Activa_De_Catalogo, Normalizar_Fuente_De_Catalogo


# ─── Almacenamiento en Memoria ───────────────────────────────────────────────

_Memoria_Del_Chat = {}


# ─── Funciones Públicas ──────────────────────────────────────────────────────

def Actualizar_Contexto(
    Id_De_Sesion,
    Etiqueta=None,
    Filtros=None,
    Id_De_Producto=None,
    Fuente_De_Catalogo=None,
):
    """Actualiza el contexto conversacional de una sesión."""
    if Id_De_Sesion not in _Memoria_Del_Chat:
        _Memoria_Del_Chat[Id_De_Sesion] = {
            "history": [],
            "last_tag": None,
            "last_filters": {},
            "selected_product_id": None,
            "catalog_source": Fuente_Activa_De_Catalogo,
        }

    Sesion = _Memoria_Del_Chat[Id_De_Sesion]

    if Etiqueta:
        Sesion["last_tag"] = Etiqueta
        Sesion["history"].append(Etiqueta)

    if Filtros is not None:
        Sesion["last_filters"] = Filtros

    if Id_De_Producto is not None:
        Sesion["selected_product_id"] = Id_De_Producto
    elif Filtros is not None and Etiqueta in ["buscar_producto", "filtrar_categoria", "filtrar_genero"]:
        # Nueva búsqueda general → limpiar producto anterior
        Sesion["selected_product_id"] = None

    if Fuente_De_Catalogo is not None:
        Sesion["catalog_source"] = Normalizar_Fuente_De_Catalogo(Fuente_De_Catalogo)

    # Limitar historial
    if len(Sesion["history"]) > config.Maximo_Historial_Chat:
        Sesion["history"].pop(0)


def Obtener_Contexto(Id_De_Sesion):
    """Retorna el contexto conversacional actual de una sesión."""
    return _Memoria_Del_Chat.get(Id_De_Sesion, {})
