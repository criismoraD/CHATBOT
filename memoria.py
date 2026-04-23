import shelve
import config
from catalogo import Fuente_Activa_De_Catalogo, Normalizar_Fuente_De_Catalogo

def Cargar_Memoria_Del_Chat_Desde_Disco():
    try:
        with shelve.open(config.Ruta_Memoria_Del_Chat) as Base_De_Memoria:
            Memoria_Cargada = Base_De_Memoria.get("memoria_chat", {})
            if isinstance(Memoria_Cargada, dict):
                return Memoria_Cargada
    except Exception as exc:
        print(f"[WARN] No se pudo cargar memoria persistente: {exc}")
    return {}

def Guardar_Memoria_Del_Chat_En_Disco():
    try:
        with shelve.open(config.Ruta_Memoria_Del_Chat) as Base_De_Memoria:
            Base_De_Memoria["memoria_chat"] = Memoria_Del_Chat
    except Exception as exc:
        print(f"[WARN] No se pudo guardar memoria persistente: {exc}")

Memoria_Del_Chat = Cargar_Memoria_Del_Chat_Desde_Disco()

def Actualizar_Contexto(Id_De_Sesion, Etiqueta=None, Filtros=None, Id_De_Producto=None, Fuente_De_Catalogo=None):
    if Id_De_Sesion not in Memoria_Del_Chat:
        Memoria_Del_Chat[Id_De_Sesion] = {
            "history": [],
            "last_tag": None,
            "last_filters": {},
            "selected_product_id": None,
            "catalog_source": Fuente_Activa_De_Catalogo,
        }

    if Etiqueta:
        Memoria_Del_Chat[Id_De_Sesion]["last_tag"] = Etiqueta
        Memoria_Del_Chat[Id_De_Sesion]["history"].append(Etiqueta)
    if Filtros is not None:
        Memoria_Del_Chat[Id_De_Sesion]["last_filters"] = Filtros
    if Id_De_Producto is not None:
        Memoria_Del_Chat[Id_De_Sesion]["selected_product_id"] = Id_De_Producto
    elif Filtros is not None and Etiqueta in ["buscar_producto", "filtrar_categoria", "filtrar_genero"]:
        # Si es una nueva búsqueda general, limpiamos el producto anterior de la memoria
        Memoria_Del_Chat[Id_De_Sesion]["selected_product_id"] = None
    if Fuente_De_Catalogo is not None:
        Memoria_Del_Chat[Id_De_Sesion]["catalog_source"] = Normalizar_Fuente_De_Catalogo(Fuente_De_Catalogo)

    if len(Memoria_Del_Chat[Id_De_Sesion]["history"]) > config.Maximo_Historial_Chat:
        Memoria_Del_Chat[Id_De_Sesion]["history"].pop(0)

    Guardar_Memoria_Del_Chat_En_Disco()

def Obtener_Contexto(Id_De_Sesion):
    return Memoria_Del_Chat.get(Id_De_Sesion, {})
