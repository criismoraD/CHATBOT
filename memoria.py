"""
memoria.py  ·  Historial del chatbot
-------------------------------------
Guarda el contexto de sesión en MySQL (tabla sesiones_chat).
Si MySQL no está disponible, usa shelve como respaldo automático.
"""

import shelve
import config
from catalogo import Fuente_Activa_De_Catalogo, Normalizar_Fuente_De_Catalogo

# ─── Helpers MySQL ────────────────────────────────────────────────────────────

def _mysql_disponible() -> bool:
    try:
        from db import probar_conexion
        return probar_conexion()
    except Exception:
        return False


def _guardar_mensaje_mysql(sesion_id: str, rol: str, mensaje: str):
    """Persiste un mensaje individual en la tabla sesiones_chat."""
    try:
        from db import ejecutar_escritura
        ejecutar_escritura(
            "INSERT INTO sesiones_chat (sesion_id, rol, mensaje) VALUES (%s, %s, %s)",
            (sesion_id, rol, str(mensaje)),
        )
    except Exception as exc:
        print(f"[WARN] No se pudo guardar mensaje en MySQL: {exc}")


# ─── Shelve (respaldo) ────────────────────────────────────────────────────────

def Cargar_Memoria_Del_Chat_Desde_Disco():
    try:
        with shelve.open(config.Ruta_Memoria_Del_Chat) as db:
            mem = db.get("memoria_chat", {})
            if isinstance(mem, dict):
                return mem
    except Exception as exc:
        print(f"[WARN] No se pudo cargar memoria persistente: {exc}")
    return {}


def Guardar_Memoria_Del_Chat_En_Disco():
    try:
        with shelve.open(config.Ruta_Memoria_Del_Chat) as db:
            db["memoria_chat"] = Memoria_Del_Chat
    except Exception as exc:
        print(f"[WARN] No se pudo guardar memoria persistente: {exc}")


# ─── Estado en memoria ────────────────────────────────────────────────────────
Memoria_Del_Chat = Cargar_Memoria_Del_Chat_Desde_Disco()
_usar_mysql      = _mysql_disponible()


# ─── API pública ──────────────────────────────────────────────────────────────

def Actualizar_Contexto(Id_De_Sesion, Etiqueta=None, Filtros=None,
                        Id_De_Producto=None, Fuente_De_Catalogo=None,
                        Mensaje_Usuario=None, Mensaje_Bot=None):
    """
    Actualiza el contexto en RAM y persiste en MySQL o shelve.
    Nuevos parámetros opcionales:
      Mensaje_Usuario / Mensaje_Bot → guarda el turno en sesiones_chat.
    """
    if Id_De_Sesion not in Memoria_Del_Chat:
        Memoria_Del_Chat[Id_De_Sesion] = {
            "history"            : [],
            "last_tag"           : None,
            "last_filters"       : {},
            "selected_product_id": None,
            "catalog_source"     : Fuente_Activa_De_Catalogo,
        }

    ctx = Memoria_Del_Chat[Id_De_Sesion]

    if Etiqueta:
        ctx["last_tag"] = Etiqueta
        ctx["history"].append(Etiqueta)
    if Filtros is not None:
        ctx["last_filters"] = Filtros
    if Id_De_Producto is not None:
        ctx["selected_product_id"] = Id_De_Producto
    elif Filtros is not None and Etiqueta in ["buscar_producto", "filtrar_categoria", "filtrar_genero"]:
        ctx["selected_product_id"] = None
    if Fuente_De_Catalogo is not None:
        ctx["catalog_source"] = Normalizar_Fuente_De_Catalogo(Fuente_De_Catalogo)

    if len(ctx["history"]) > config.Maximo_Historial_Chat:
        ctx["history"].pop(0)

    # Persistencia
    if _usar_mysql:
        if Mensaje_Usuario:
            _guardar_mensaje_mysql(Id_De_Sesion, "user", Mensaje_Usuario)
        if Mensaje_Bot:
            _guardar_mensaje_mysql(Id_De_Sesion, "bot",  Mensaje_Bot)
    else:
        Guardar_Memoria_Del_Chat_En_Disco()


def Obtener_Contexto(Id_De_Sesion):
    return Memoria_Del_Chat.get(Id_De_Sesion, {})


def Obtener_Historial_MySQL(sesion_id: str, limite: int = 20) -> list:
    """
    Retorna los últimos mensajes de una sesión desde MySQL.
    Útil para mostrar historial en la interfaz.
    """
    if not _usar_mysql:
        return []
    try:
        from db import ejecutar_consulta
        return ejecutar_consulta(
            "SELECT rol, mensaje, creado_en FROM sesiones_chat "
            "WHERE sesion_id = %s ORDER BY creado_en DESC LIMIT %s",
            (sesion_id, limite),
        )
    except Exception as exc:
        print(f"[WARN] No se pudo obtener historial: {exc}")
        return []
