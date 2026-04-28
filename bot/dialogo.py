"""
bot/dialogo.py  ·  Motor de Diálogo del Chatbot
------------------------------------------------
Procesa el mensaje del usuario, detecta intenciones,
aplica filtros de búsqueda y genera la respuesta del bot.
Es el cerebro conversacional del chatbot.
"""

import re
import random
from core import config
from bot.ia import Predecir_Tag, Datos_De_Intents
from bot.extractor import (
    Es_Consulta_De_Seguimiento_De_Pedido, Detectar_Id_De_Producto_En_Texto,
    Extraer_Filtros, Extraer_Palabras_Clave_De_Mensaje,
    Es_Solicitud_De_Reinicio_De_Filtros, Normalizar_Texto_Base,
    Inferir_Etiqueta_De_Detalle
)
from bot.catalogo import (
    Datos_De_Productos, Buscar_Productos, Obtener_Producto_Por_Id,
    Obtener_Colores_De_Producto, Obtener_Detalle_De_Inventario,
    Categorias_Dinamicas, Indice_De_Nombres_De_Producto,
    Frecuencia_De_Tokens_De_Producto, Obtener_Colores_Por_Categoria,
    Obtener_Colores_Dinamicos
)
from bot.memoria import Obtener_Contexto, Actualizar_Contexto


# ─── Respuestas de Intents ───────────────────────────────────────────────────

def _Obtener_Respuesta_Aleatoria(Etiqueta):
    """Selecciona una respuesta aleatoria del intent correspondiente."""
    for Intent in Datos_De_Intents['intents']:
        if Intent['tag'] == Etiqueta and Intent['responses']:
            return random.choice(Intent['responses'])
    return None


def _Generar_Respuesta_Busqueda(Cantidad, Texto_Filtro, Exito=True):
    """Genera una respuesta natural para resultados de búsqueda."""
    if Exito:
        Plantillas = [
            f"¡Genial! Encontré {Cantidad} opciones{Texto_Filtro}. Te las dejé en el catálogo, dime qué te parecen.",
            f"¡Bingo! Tengo {Cantidad} productos{Texto_Filtro} listos para ti. Échales un vistazo arriba.",
            f"He filtrado el catálogo y encontré {Cantidad} artículos{Texto_Filtro}. ¿Alguno te llama la atención?",
            f"¡Listo! Aquí tienes {Cantidad} resultados{Texto_Filtro}. Desliza por el catálogo para verlos."
        ]
    else:
        Plantillas = [
            "Uy, lo siento mucho. No encontré nada con esas características exactas en este momento. ¿Probamos con otro color o modelo?",
            "Revisé el inventario pero no di con lo que buscas. ¿Te gustaría intentar una búsqueda un poco más general?",
            "Lamentablemente no tengo productos que coincidan al 100% con eso ahora mismo. ¡Pero sigo actualizando mi stock a diario!"
        ]
    return random.choice(Plantillas)


# ─── Herencia de Filtros de Contexto ─────────────────────────────────────────

def _Debe_Heredar_Filtros(Contexto, Mensaje, Cat, Color, Precio, Talla, Genero):
    """
    Determina si los filtros actuales deben heredarse del contexto anterior.
    Ejemplo: si el usuario dice "y verdes?" después de buscar zapatillas.
    """
    Filtros_Ant = Contexto.get("last_filters", {}) if isinstance(Contexto, dict) else {}
    if not isinstance(Filtros_Ant, dict) or not Filtros_Ant:
        return False

    Hay_Filtros = any([Cat, Color, Precio is not None, Talla, Genero])
    if not Hay_Filtros:
        return False

    Tokens = Normalizar_Texto_Base(Mensaje).split()
    if not Tokens:
        return False

    if Tokens[0] in {"y", "ademas", "tambien"}:
        return True

    Cat_Misma = Cat == Filtros_Ant.get("category")

    if Genero and not any([Cat and not Cat_Misma, Color, Precio is not None, Talla]) and len(Tokens) <= 6:
        return True
    if Color and not any([Cat and not Cat_Misma, Genero, Precio is not None, Talla]) and len(Tokens) <= 6:
        return True
    if Talla and not any([Cat and not Cat_Misma, Color, Genero, Precio is not None]) and len(Tokens) <= 6:
        return True
    if Precio is not None and not any([Cat and not Cat_Misma, Color, Genero, Talla]) and len(Tokens) <= 6:
        return True

    return False


def _Heredar_Filtros(Contexto, Cat, Color, Precio, Talla, Genero, Palabras_Clave):
    """Hereda filtros del contexto anterior, priorizando los nuevos."""
    Filtros_Ant = Contexto.get("last_filters", {}) if isinstance(Contexto, dict) else {}
    if not isinstance(Filtros_Ant, dict):
        Filtros_Ant = {}

    Cambio_Cat = Cat is not None and Filtros_Ant.get("category") is not None and Cat != Filtros_Ant.get("category")

    Cat_Final = Cat or Filtros_Ant.get("category")

    if Cambio_Cat:
        Color_Final = Color
        Talla_Final = Talla
        Genero_Final = Genero
        Keywords = Palabras_Clave if isinstance(Palabras_Clave, list) else []
    else:
        Color_Final = Color or Filtros_Ant.get("color")
        Talla_Final = Talla or Filtros_Ant.get("talla")
        Genero_Final = Genero or Filtros_Ant.get("genero")
        if not Palabras_Clave and Filtros_Ant.get("keywords"):
            Keywords = Filtros_Ant.get("keywords")
        else:
            Keywords = Palabras_Clave if isinstance(Palabras_Clave, list) else []

    Precio_Final = Precio if (Cambio_Cat or Precio is not None) else Filtros_Ant.get("max_price")

    return Cat_Final, Color_Final, Precio_Final, Talla_Final, Genero_Final, Keywords


# ─── Heurísticas de Soporte ──────────────────────────────────────────────────

def _Inferir_Por_Heuristicas(Mensaje, Etiqueta):
    """Aplica reglas heurísticas para detectar intenciones de soporte."""
    Tokens = set(Mensaje.split())
    if not Tokens:
        return None

    if Tokens.intersection({"delivery", "deliverys", "envio", "envios", "domicilio", "horario", "horarios",
                            "ubicacion", "direccion", "tarjeta", "yape", "plin", "contraentrega", "factura", "boleta"}):
        return "informacion_tienda"

    if Tokens.intersection({"reclamo", "reclamos", "soporte", "devolucion", "devolver", "cambio", "garantia", "queja"}):
        return "reclamos"

    if Tokens.intersection({"comprar", "compra", "pedido"}) and Tokens.intersection({"como", "informacion", "pasos", "guia", "ayuda", "ayudame", "explicame"}):
        return "guia_compra"

    if Etiqueta in {None, "fuera_de_dominio", "saludo"} and Tokens.intersection({"ayuda", "ayudame", "ayudar", "asesor", "asesoria", "asistencia"}):
        return "saludo"

    return None


def _Es_Ayuda_General(Mensaje):
    """Detecta si el usuario pide ayuda general."""
    Tokens = set(Mensaje.split())
    return bool(Tokens.intersection({"ayuda", "ayudame", "ayudar", "asesor", "asesoria", "asistencia"}))


def _Obtener_Texto_Natural(Palabras_Clave):
    """Convierte keywords a texto natural legible (ej: 'mochila' → 'mochilas')."""
    if not isinstance(Palabras_Clave, list):
        return None

    Mapa = {
        "mochila": "mochilas", "mochilas": "mochilas",
        "gorra": "gorras", "gorras": "gorras",
        "tomatodo": "tomatodos", "tomatodos": "tomatodos",
        "accesorio": "accesorios", "accesorios": "accesorios",
        "falda": "faldas", "faldas": "faldas",
        "vestido": "vestidos", "vestidos": "vestidos",
        "zapatilla": "zapatillas", "zapatillas": "zapatillas",
        "polo": "polos", "polos": "polos",
        "pantalon": "pantalones", "pantalones": "pantalones",
        "calzado": "productos de calzado",
    }
    for P in Palabras_Clave:
        Norm = Normalizar_Texto_Base(P)
        if Norm in Mapa:
            return Mapa[Norm]
    return None


def _Es_Busqueda_Por_Subtipo(Palabras_Clave):
    """Detecta si la búsqueda es por un tipo específico de producto."""
    if not isinstance(Palabras_Clave, list):
        return False

    Especificas = {
        "mochila", "mochilas", "gorra", "gorras", "tomatodo", "tomatodos",
        "media", "medias", "calcetin", "calcetines", "falda", "faldas",
        "vestido", "vestidos", "legging", "leggings", "jogger", "joggers",
        "short", "shorts", "casaca", "casacas"
    }
    for P in Palabras_Clave:
        if Normalizar_Texto_Base(P) in Especificas:
            return True
    return False


def _Forzar_Etiqueta_Por_Contexto(Mensaje, Hay_Producto):
    """Si hay un producto en contexto, fuerza la etiqueta según palabras clave del mensaje."""
    if not Hay_Producto:
        return None

    Tokens = set(Mensaje.split())
    if not Tokens:
        return None

    if Tokens.intersection({"talla", "tallas", "stock", "disponibilidad", "disponible", "queda", "quedan"}):
        return "consultar_stock_item"
    if Tokens.intersection({"precio", "precios", "costo", "costos", "cuanto", "cuesta", "vale", "valen"}):
        return "consultar_precio_item"
    if Tokens.intersection({"color", "colores"}):
        return "colores"

    return None


# ─── Función Principal del Diálogo ───────────────────────────────────────────

def Obtener_Respuesta_Principal(Id_De_Sesion, Mensaje_Usuario):
    """
    Punto de entrada principal del motor de diálogo.
    Procesa el mensaje, detecta intención, aplica filtros y genera respuesta.
    Retorna: (respuesta, etiqueta, accion_de_filtro)
    """

    # ── 1. Predicción del modelo y contexto ──
    Etiqueta, Confianza, Margen = Predecir_Tag(Mensaje_Usuario)
    Contexto = Obtener_Contexto(Id_De_Sesion)
    Mensaje = Normalizar_Texto_Base(Mensaje_Usuario)
    Es_Ayuda = _Es_Ayuda_General(Mensaje)
    Es_Seguimiento = Es_Consulta_De_Seguimiento_De_Pedido(Mensaje_Usuario)

    # Detectar producto mencionado
    Id_Producto_Detectado = Detectar_Id_De_Producto_En_Texto(
        Mensaje_Usuario, Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto
    )
    if Id_Producto_Detectado is not None:
        Actualizar_Contexto(Id_De_Sesion, Id_De_Producto=Id_Producto_Detectado)
        Contexto = Obtener_Contexto(Id_De_Sesion)

    # Extraer filtros
    Cat, Color, Precio, Talla, Genero = Extraer_Filtros(
        Mensaje_Usuario, Categorias_Dinamicas, Obtener_Colores_Dinamicos()
    )
    Palabras_Clave = Extraer_Palabras_Clave_De_Mensaje(Mensaje_Usuario)
    Respuesta = None

    # ── 2. Reinicio de filtros ──
    if Es_Solicitud_De_Reinicio_De_Filtros(Mensaje_Usuario):
        Accion = {"category": None, "color": None, "max_price": None, "talla": None, "genero": None, "keywords": []}
        Actualizar_Contexto(Id_De_Sesion, "buscar_producto", Accion)
        return "Listo, reinicie todos los filtros y ya te muestro el catalogo completo.", "buscar_producto", Accion

    # ── 3. Herencia de filtros ──
    if _Debe_Heredar_Filtros(Contexto, Mensaje_Usuario, Cat, Color, Precio, Talla, Genero):
        Cat, Color, Precio, Talla, Genero, Palabras_Clave = _Heredar_Filtros(
            Contexto, Cat, Color, Precio, Talla, Genero, Palabras_Clave
        )

    # ── 4. Inferencia de etiqueta por contexto ──
    Hay_Producto = bool(Id_Producto_Detectado or Contexto.get("selected_product_id"))
    Etiqueta_Inferida = Inferir_Etiqueta_De_Detalle(
        Mensaje_Usuario,
        Ultima_Etiqueta=Contexto.get("last_tag"),
        Hay_Producto_En_Contexto=Hay_Producto,
        Producto_Mencionado_En_Mensaje=Id_Producto_Detectado is not None,
    )
    if Etiqueta_Inferida:
        Etiqueta = Etiqueta_Inferida

    # Corregir etiqueta si hay filtros activos
    if (Color or Precio or Genero or Cat or Talla) and Etiqueta in {"saludo", "fuera_de_dominio"}:
        if Etiqueta == "fuera_de_dominio" and Confianza > 0.6:
            pass
        else:
            Etiqueta = "buscar_producto"

    if Etiqueta == "colores" and (Precio or Genero or Cat or not Hay_Producto):
        Etiqueta = "buscar_producto"

    if Es_Seguimiento and Etiqueta in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta = "pedidos"

    # ── 5. Validación por patrones ──
    Etiquetas_Detalle = {"consultar_stock_item", "consultar_precio_item", "colores", "contexto_iniciado"}
    Etiquetas_Negocio = {
        "buscar_producto", "pedidos", "reclamos", "consulta_precio",
        "filtrar_categoria", "filtrar_genero", "informacion_tienda", "promociones",
        "guia_compra", "metodos_pago"
    }

    Es_Fuerte = (
        Etiqueta in Etiquetas_Negocio
        and Confianza >= config.Umbral_De_Confianza
        and Margen >= config.Umbral_De_Margen_Base
    )

    if Etiqueta not in Etiquetas_Detalle and (not Es_Fuerte or Etiqueta == "fuera_de_dominio"):
        Tag_Patron = None
        Max_Longitud = 0
        for Intent in Datos_De_Intents['intents']:
            for Patron in Intent['patterns']:
                Patron_Norm = Normalizar_Texto_Base(Patron)
                if Patron_Norm and Patron_Norm in Mensaje:
                    if len(Patron_Norm) <= 4 and not re.search(r'\b' + re.escape(Patron_Norm) + r'\b', Mensaje):
                        continue
                    if len(Patron_Norm) > Max_Longitud:
                        Max_Longitud = len(Patron_Norm)
                        Tag_Patron = Intent['tag']

        if Tag_Patron:
            Etiqueta = Tag_Patron

    # ── 6. Heurísticas de soporte ──
    if Mensaje in {"quiero saber mas de este producto", "quiero saber mas de este"}:
        Etiqueta = "contexto_iniciado"

    Tag_Heuristica = _Inferir_Por_Heuristicas(Mensaje, Etiqueta)
    if Tag_Heuristica:
        Etiqueta = Tag_Heuristica

    # Ajustes por subtipo de búsqueda
    Es_Subtipo = _Es_Busqueda_Por_Subtipo(Palabras_Clave)
    if Es_Subtipo and Cat:
        Cat = None
    if Es_Subtipo and Etiqueta in {"saludo", "fuera_de_dominio", None}:
        Etiqueta = "buscar_producto"
    if Etiqueta == "filtrar_categoria" and Es_Subtipo:
        Etiqueta = "buscar_producto"

    # Forzar búsqueda si hay filtros
    if (Color or Precio or Genero or Cat or Talla):
        if Etiqueta in {"saludo", "fuera_de_dominio", None, "consulta_precio"}:
            Etiqueta = "buscar_producto"
    if Precio and len(Mensaje.split()) <= 6:
        Etiqueta = "buscar_producto"

    if Es_Seguimiento and Etiqueta in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta = "pedidos"

    Etiqueta_Forzada = _Forzar_Etiqueta_Por_Contexto(Mensaje, Hay_Producto)
    if Etiqueta_Forzada:
        Etiqueta = Etiqueta_Forzada

    # ── 7. Lógica por etiqueta ──
    Accion = None
    Productos_Encontrados = []

    # ── buscar_producto ──
    if Etiqueta == "buscar_producto":
        Relajada = False
        Productos_Encontrados = Buscar_Productos(
            Categoria=Cat, Color=Color, Precio_Maximo=Precio,
            Talla=Talla, Genero=Genero, Palabras_Clave=Palabras_Clave,
            Limite=len(Datos_De_Productos),
        )

        if not Productos_Encontrados and Palabras_Clave:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                Talla=Talla, Genero=Genero, Palabras_Clave=None,
                Limite=len(Datos_De_Productos),
            )
            if Productos_Encontrados:
                Palabras_Clave = []
                Relajada = True

        if not Productos_Encontrados and not Palabras_Clave and not Cat and Color:
            Respuesta = f"Me parece genial el color {Color.lower()}, pero ¿qué buscas exactamente? ¿Zapatillas, polos, pantalones o algo más?"
            Accion = {"color": Color, "max_price": Precio, "talla": Talla, "genero": Genero}
        elif not Productos_Encontrados and not Palabras_Clave and not Cat and Talla:
            Respuesta = f"Talla {Talla}, perfecto. ¿Pero de qué producto? ¿Buscas calzado o alguna prenda en particular?"
            Accion = {"color": Color, "max_price": Precio, "talla": Talla, "genero": Genero}
        elif Productos_Encontrados:
            Texto_Natural = _Obtener_Texto_Natural(Palabras_Clave)
            Texto_Base = Texto_Natural or "productos"
            Filtro = ""
            if Color: Filtro += f" en color {Color}"
            if Cat and not Texto_Natural: Filtro += f" de {Cat.lower()}"
            if Talla: Filtro += f" talla {Talla}"
            if Genero: Filtro += f" para {Genero.lower()}"
            if Relajada:
                Respuesta = f"Encontré {len(Productos_Encontrados)} opciones relacionadas de {Texto_Base}{Filtro}. Ya te las muestro en el catálogo, indícame cuál te interesa."
            else:
                Respuesta = f"Encontré {len(Productos_Encontrados)} {Texto_Base}{Filtro}. Ya te los muestro en el catálogo, indícame cuál te interesa."
            Accion = {"category": Cat, "color": Color, "max_price": Precio, "talla": Talla, "genero": Genero, "keywords": Palabras_Clave}
        else:
            Respuesta = "No encontré productos con esas características. He reiniciado los filtros para que veas otras opciones del catálogo:"
            Accion = {"category": None, "color": None, "max_price": None, "talla": None, "genero": None, "keywords": []}

    # ── filtrar_categoria ──
    elif Etiqueta == "filtrar_categoria":
        if Cat:
            Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                Talla=Talla, Genero=Genero, Palabras_Clave=Palabras_Clave,
                Limite=len(Datos_De_Productos),
            )
            Texto_Natural = _Obtener_Texto_Natural(Palabras_Clave)
            if Texto_Natural:
                Respuesta = f"Listo! Te muestro {len(Encontrados)} {Texto_Natural}. Revisa el catalogo arriba."
            else:
                Respuesta = f"Listo! Te muestro los {len(Encontrados)} productos de {Cat}. Revisa el catalogo arriba."
            Accion = {"category": Cat, "color": Color, "max_price": Precio, "talla": Talla, "genero": Genero, "keywords": Palabras_Clave}
        else:
            Respuesta = "Claro! Que categoria te interesa? Tenemos: Calzado, Polos, Pantalones y Otros."

    # ── filtrar_genero ──
    elif Etiqueta == "filtrar_genero":
        if Genero:
            Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                Talla=Talla, Genero=Genero, Palabras_Clave=Palabras_Clave,
                Limite=len(Datos_De_Productos),
            )
            Condicion = f" para {Genero.lower()}"
            if Precio: Condicion += f" hasta S/ {Precio:.2f}"
            if Cat: Condicion += f" en {Cat}"

            if Encontrados:
                Texto_Natural = _Obtener_Texto_Natural(Palabras_Clave)
                if Texto_Natural:
                    Cantidad = Texto_Natural
                    if Cat and f" en {Cat}" in Condicion:
                        Condicion = Condicion.replace(f" en {Cat}", "")
                else:
                    Cantidad = "producto" if len(Encontrados) == 1 else "productos"
                Respuesta = f"Listo! Te muestro {len(Encontrados)} {Cantidad}{Condicion}."
                Accion = {"genero": Genero, "max_price": Precio, "category": Cat, "color": Color, "talla": Talla, "keywords": Palabras_Clave}
            else:
                Respuesta = f"No encontré productos{Condicion}. Aquí tienes otras opciones del catálogo completo:"
                Accion = {"category": None, "color": None, "max_price": None, "talla": None, "genero": None, "keywords": []}
        else:
            Respuesta = "¿Para qué genero te muestro opciones? Tengo Mujer, Hombre y Unisex."
            Accion = {"category": Cat, "color": Color, "max_price": Precio, "talla": Talla, "keywords": Palabras_Clave}

    # ── consulta_precio ──
    elif Etiqueta == "consulta_precio":
        Id_Ctx = Contexto.get("selected_product_id")
        if Id_Ctx:
            Prod = Obtener_Producto_Por_Id(Id_Ctx)
            if Prod:
                Respuesta = f"El {Prod['name']} cuesta S/ {Prod['price']:.2f}."
            else:
                Respuesta = "No encuentro el precio de ese producto en específico."
        elif Cat or Color or Genero or Palabras_Clave or Talla:
            Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                Genero=Genero, Palabras_Clave=Palabras_Clave, Limite=3,
            )
            if Encontrados:
                Respuesta = "Listo, ya te filtre esos productos en el catalogo. Indicame cual te interesa y te doy el precio exacto."
                Accion = {"category": Cat, "color": Color, "genero": Genero, "keywords": Palabras_Clave}
            else:
                Respuesta = "No encontre productos con esas caracteristicas. Prueba otra busqueda."
        else:
            Respuesta = _Obtener_Respuesta_Aleatoria(Etiqueta) or "Puedes pedirme precios por categoria o color."

    # ── pedidos ──
    elif Etiqueta == "pedidos":
        if Es_Seguimiento:
            Respuesta = (
                "Te ayudo con el seguimiento de tu pedido. En esta version aun no consulto tracking en tiempo real. "
                "Si me compartes tu numero de pedido, te indico el estado estimado y los siguientes pasos."
            )
        else:
            Respuesta = _Obtener_Respuesta_Aleatoria(Etiqueta) or "Para comprar, elige un producto y agrégalo al carrito."

    # ── colores ──
    elif Etiqueta == "colores":
        Id_Ctx = Contexto.get("selected_product_id")
        if Id_Ctx:
            Prod = Obtener_Producto_Por_Id(Id_Ctx)
            if Prod:
                Colores = Obtener_Colores_De_Producto(Prod)
                if Colores:
                    Respuesta = f"El {Prod['name']} esta disponible en estos colores: {', '.join(Colores)}."
                else:
                    Respuesta = f"El {Prod['name']} no registra colores en la base actual."
            else:
                Respuesta = "No encuentro el producto en contexto para listar sus colores."
        elif Cat:
            Colores_Cat = Obtener_Colores_Por_Categoria().get(Cat, [])
            if Colores_Cat:
                Respuesta = f"En {Cat} tenemos los colores: {', '.join(Colores_Cat)}."
            else:
                Respuesta = f"No encontré colores registrados para la categoría {Cat}."
        else:
            Respuesta = "Nuestros productos estan disponibles en: Negro, Blanco, Rojo, Azul, Gris y Verde."

    # ── disponibilidad ──
    elif Etiqueta == "disponibilidad":
        Id_Ctx = Contexto.get("selected_product_id")
        if Id_Ctx:
            Prod = Obtener_Producto_Por_Id(Id_Ctx)
            if Prod:
                T, G, Stock_Txt, Stock_Int = Obtener_Detalle_De_Inventario(Prod)
                if Stock_Int is None or Stock_Int > 0:
                    Respuesta = f"Si, tenemos disponible el {Prod['name']}. Stock: {Stock_Txt}. Genero: {G}. Tallas: {T}."
                else:
                    Respuesta = f"En este momento el {Prod['name']} no tiene stock disponible. Genero: {G}. Tallas registradas: {T}."
            else:
                Respuesta = "No encuentro el producto en contexto para validar disponibilidad."
        elif Cat or Color or Genero or Palabras_Clave or Talla:
            Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Genero=Genero,
                Palabras_Clave=Palabras_Clave, Limite=3,
            )
            if Encontrados:
                Respuesta = f"Si, tenemos {len(Encontrados)}+ productos disponibles con ese filtro. Ya te los muestro en el catalogo, indicame cual te interesa."
            else:
                Respuesta = "Actualmente no tenemos stock con esas especificaciones."
        else:
            Respuesta = _Obtener_Respuesta_Aleatoria(Etiqueta) or "Claro, dime color o categoria para revisar stock."

    # ── consultar_precio_item ──
    elif Etiqueta == "consultar_precio_item":
        Id_Ctx = Contexto.get("selected_product_id")
        if Id_Ctx:
            Prod = Obtener_Producto_Por_Id(Id_Ctx)
            if Prod:
                Respuesta = f"¡Excelente elección! El precio del {Prod['name']} es de S/ {Prod['price']:.2f}."
            else:
                Respuesta = "No encuentro el precio de ese producto en específico."
        else:
            Respuesta = "¡Claro que sí! Solo ayúdame indicando el nombre del producto que te interesa para darte el precio exacto."

    # ── consultar_stock_item ──
    elif Etiqueta == "consultar_stock_item":
        Id_Ctx = Contexto.get("selected_product_id")
        if Id_Ctx:
            Prod = Obtener_Producto_Por_Id(Id_Ctx)
            if Prod:
                T, G, Stock_Txt, _ = Obtener_Detalle_De_Inventario(Prod)
                if Talla:
                    if 'tallas' in Prod and Talla in Prod['tallas']:
                        Respuesta = f"¡Buenas noticias! Si tenemos el {Prod['name']} en talla {Talla}. Genero: {G}. Stock: {Stock_Txt}."
                    elif 'tallas' in Prod:
                        Tallas = ", ".join(Prod['tallas'])
                        Respuesta = f"Lo siento, no nos queda en talla {Talla}. Lo tenemos en: {Tallas}. Genero: {G}. Stock: {Stock_Txt}."
                    else:
                        Respuesta = f"Este producto es talla unica. Genero: {G}. Stock: {Stock_Txt}."
                else:
                    Respuesta = f"Claro, el {Prod['name']} lo tenemos en las siguientes tallas: {T}. Genero: {G}. Stock: {Stock_Txt}."
            else:
                Respuesta = "No encuentro la información de tallas de ese producto en específico."
        else:
            if Talla:
                Encontrados = Buscar_Productos(
                    Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                    Talla=Talla, Genero=Genero, Palabras_Clave=Palabras_Clave,
                    Limite=len(Datos_De_Productos),
                )
                if Encontrados:
                    Condicion = f" en talla {Talla}"
                    if Cat: Condicion += f" de {Cat.lower()}"
                    if Color: Condicion += f" color {Color.lower()}"
                    if Genero: Condicion += f" para {Genero.lower()}"
                    Respuesta = f"Listo, ya filtré productos{Condicion}. Revisa el catálogo e indícame cuál te interesa."
                    Accion = {"category": Cat, "color": Color, "max_price": Precio, "talla": Talla, "genero": Genero, "keywords": Palabras_Clave}
                    Etiqueta = "buscar_producto"
                else:
                    Respuesta = f"No encontré productos con talla {Talla} bajo los filtros actuales. ¿Quieres que ampliemos la búsqueda?"
            else:
                Respuesta = "¡Con gusto lo reviso! ¿Me podrías decir qué modelo de zapatilla o prenda estás buscando específicamente?"

    # ── Respuesta final para tags no manejados ──
    Tags_Manual = {
        "buscar_producto", "filtrar_categoria", "filtrar_genero", "consulta_precio",
        "pedidos", "colores", "disponibilidad", "consultar_precio_item", "consultar_stock_item"
    }

    if Etiqueta == "saludo" and Es_Ayuda and not any([Cat, Color, Precio, Talla, Genero]):
        Respuesta = (
            "Puedo ayudarte a buscar productos por categoria, color, talla, genero y precio. "
            "Tambien te explico delivery, metodos de pago y reclamos. "
            "Prueba por ejemplo: busco zapatillas negras talla 42 para hombre."
        )

    if Etiqueta and Etiqueta != "fuera_de_dominio" and Etiqueta not in Tags_Manual:
        if not Respuesta:
            Respuesta = _Obtener_Respuesta_Aleatoria(Etiqueta) or "No entiendo tu consulta. puedes repetirla?."
    elif Etiqueta == "fuera_de_dominio":
        Respuesta = "No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa."

    # ── Fallback general ──
    if not Respuesta:
        if Cat or Color or Genero or Palabras_Clave or Talla:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Cat, Color=Color, Precio_Maximo=Precio,
                Genero=Genero, Palabras_Clave=Palabras_Clave,
            )
            if not Productos_Encontrados and not Palabras_Clave and not Cat and Color:
                Respuesta = f"Me parece genial el color {Color.lower()}, pero ¿qué buscas exactamente? ¿Zapatillas, polos, pantalones o algo más?"
                Accion = {"color": Color, "max_price": Precio, "talla": Talla, "genero": Genero, "category": None, "keywords": []}
            elif not Productos_Encontrados and not Palabras_Clave and not Cat and Talla:
                Respuesta = f"Talla {Talla}, perfecto. ¿Pero de qué producto? ¿Buscas calzado o alguna prenda en particular?"
                Accion = {"color": Color, "max_price": Precio, "talla": Talla, "genero": Genero, "category": None, "keywords": []}
            elif not Productos_Encontrados and Palabras_Clave:
                Respuesta = "No encontré nada con esos términos. Te muestro opciones destacadas del catálogo general:"
                Accion = {"category": None, "color": None, "max_price": None, "talla": None, "genero": None, "keywords": []}
            elif Productos_Encontrados:
                Filtro = ""
                if Color: Filtro += f" en color {Color.lower()}"
                if Cat: Filtro += f" de la categoría {Cat.capitalize()}"
                if Talla: Filtro += f" talla {Talla}"
                Respuesta = _Generar_Respuesta_Busqueda(len(Productos_Encontrados), Filtro, exito=True)
                Accion = {"category": Cat, "color": Color, "talla": Talla, "genero": Genero, "max_price": Precio, "keywords": Palabras_Clave}
                Etiqueta = "buscar_producto"
            else:
                Respuesta = "No encontré productos con esas características. Mantenemos los filtros anteriores para que puedas modificarlos. ¿Deseas buscar otra cosa?"
                Accion = {"category": Cat, "color": Color, "talla": Talla, "genero": Genero, "max_price": Precio, "keywords": Palabras_Clave}
                Etiqueta = "buscar_producto"
        elif Id_Producto_Detectado is not None:
            Prod = Obtener_Producto_Por_Id(Id_Producto_Detectado)
            if Prod:
                Respuesta = f"Ya identifique el producto {Prod['name']}. ¿Quieres que te diga precio, colores o stock?"
                Etiqueta = "buscar_producto"
            else:
                Respuesta = "No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa."
        else:
            if Etiqueta == "buscar_producto":
                Respuesta = "¡Claro! Dime qué buscas y te muestro las opciones."
            else:
                Respuesta = "No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa."

    # ── 8. Actualizar contexto ──
    if Etiqueta in ["buscar_producto", "filtrar_categoria", "filtrar_genero", "colores"]:
        Actualizar_Contexto(Id_De_Sesion, Etiqueta, {
            "category": Cat, "color": Color, "max_price": Precio,
            "talla": Talla, "genero": Genero, "keywords": Palabras_Clave,
        })
    else:
        Actualizar_Contexto(Id_De_Sesion, Etiqueta, Filtros=None)

    if Accion and Productos_Encontrados:
        Accion['product_ids'] = [p['id'] for p in Productos_Encontrados]

    if Respuesta is None:
        Respuesta = "Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?"

    return Respuesta, Etiqueta, Accion
