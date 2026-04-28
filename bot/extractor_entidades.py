"""
bot/extractor.py  ·  Extracción de Entidades y Filtros del Mensaje
-------------------------------------------------------------------
Detecta del mensaje del usuario:
  - Categoría de producto (CALZADO, POLos, PANTALONES, OTROS)
  - Color
  - Talla
  - Precio máximo
  - Género
  - Palabras clave de búsqueda
  - ID de producto mencionado
  - Intención de seguimiento de pedido
"""

import re
import unicodedata
from thefuzz import process
from core.procesamiento_lenguaje import Normalizar_Texto as _Normalizar_Texto_Base_NLP


# ─── Mapas de Correspondencia ────────────────────────────────────────────────

Mapa_De_Genero = {
    "mujer": "Mujer", "mujeres": "Mujer", "dama": "Mujer", "damas": "Mujer",
    "hombre": "Hombre", "hombres": "Hombre", "varon": "Hombre", "caballero": "Hombre",
    "unisex": "Unisex"
}

_Sinonimos_De_Categorias = {
    "zapatillas": "CALZADO", "zapatilla": "CALZADO", "zapas": "CALZADO",
    "zapatos": "CALZADO", "zapato": "CALZADO", "botines": "CALZADO",
    "botin": "CALZADO", "chimpunes": "CALZADO", "botas": "CALZADO",
    "polo": "POLOS", "camiseta": "POLOS", "camisetas": "POLOS",
    "jersey": "POLOS", "bividi": "POLOS",
    "pantalon": "PANTALONES", "pantalones": "PANTALONES", "short": "PANTALONES",
    "shorts": "PANTALONES", "leggings": "PANTALONES", "buzo": "PANTALONES",
    "falda": "PANTALONES", "faldas": "PANTALONES", "vestido": "PANTALONES",
    "vestidos": "PANTALONES",
    "medias": "OTROS", "calcetines": "OTROS", "tobilleras": "OTROS",
    "accesorios": "OTROS", "accesorio": "OTROS", "gorra": "OTROS",
    "gorras": "OTROS", "mochila": "OTROS", "mochilas": "OTROS",
    "reloj": "OTROS", "guantes": "OTROS", "botella": "OTROS", "termo": "OTROS"
}

_Sinonimos_De_Colores = {
    "negra": "Negro", "negros": "Negro", "negras": "Negro",
    "blanca": "Blanco", "blancos": "Blanco", "blancas": "Blanco",
    "roja": "Rojo", "rojos": "Rojo", "rojas": "Rojo",
    "azules": "Azul",
    "grises": "Gris",
    "verdes": "Verde"
}

_Sinonimos_De_Palabras_Clave = {
    "zapatillas": "zapatilla", "zapas": "zapatilla",
    "polos": "polo", "pantalones": "pantalon", "faldas": "falda",
    "vestidos": "vestido", "leggings": "legging", "joggers": "jogger",
    "shorts": "short", "gorras": "gorra", "mochilas": "mochila",
    "casacas": "casaca", "medias": "media", "calcetines": "calcetin",
    "tomatodos": "tomatodo", "botella": "tomatodo", "botellas": "tomatodo",
    "termo": "tomatodo", "termos": "tomatodo",
}


# ─── Patrones Regex ──────────────────────────────────────────────────────────

_Patron_De_Talla = re.compile(r'(?:talla|en)\s+(xs|s|m|l|xl|xxl|\d{2})')
_Patron_De_Precio = re.compile(r'(?:menos de|bajo|hasta|max|maximo|menor a|menores a|menores que|presupuesto de|presupuesto|<=)\s*(\d+)')
_Patron_De_Precio_Directo = re.compile(r'(?<!\d)(\d{2,4})(?:\s*(?:soles|s/?\.?))')


# ─── Palabras Vacías ────────────────────────────────────────────────────────

Palabras_Vacias_Entidad_Producto = {
    "de", "del", "la", "el", "los", "las", "para", "con", "en", "por",
    "y", "o", "un", "una", "unos", "unas"
}

_Palabras_Vacias_De_Busqueda = {
    "quiero", "quisiera", "busco", "mostrar", "muestrame", "dame", "tienes",
    "tiene", "hay", "del", "devolver", "devolucion", "de", "la", "el", "los",
    "las", "para", "con", "en", "por", "un", "una", "unos", "unas", "este",
    "esta", "producto", "productos", "me", "porfavor", "porfa", "tengo",
    "soles", "sol", "precio", "presupuesto", "ver", "comprar", "saber",
    "conseguir", "alguna", "algun", "algo", "estan", "hola", "buenas",
    "buenos", "dias", "tardes", "noches", "todo", "todos", "toda", "todas",
    "mejor", "que"
}


# ─── Funciones de Normalización ──────────────────────────────────────────────

def Normalizar_Texto_Base(Texto_Entrada):
    """Wrapper que delega a core.nlp.Normalizar_Texto."""
    return _Normalizar_Texto_Base_NLP(Texto_Entrada or '')


def _Normalizar_Texto_Categoria(Texto_Entrada):
    """Normaliza texto para detección de categoría (sin acentos, minúsculas)."""
    Texto = str(Texto_Entrada or '').strip().lower()
    Texto = ''.join(
        Caracter for Caracter in unicodedata.normalize('NFD', Texto)
        if unicodedata.category(Caracter) != 'Mn'
    )
    return re.sub(r'\s+', ' ', Texto).strip()


# ─── Detección de Categoría ──────────────────────────────────────────────────

def Inferir_Categoria_Desde_Nombre(Nombre_De_Producto):
    """Inferir categoría del producto a partir de su nombre."""
    Nombre_Normalizado = _Normalizar_Texto_Categoria(Nombre_De_Producto)
    if not Nombre_Normalizado:
        return None

    Tokens = set(re.findall(r'[a-z0-9]+', Nombre_Normalizado))
    if not Tokens:
        return None

    Reglas = (
        ('CALZADO', ('zapatilla', 'zapatillas', 'zapato', 'zapatos', 'botin', 'botines', 'chimpun', 'chimpunes', 'tenis')),
        ('PANTALONES', ('pantalon', 'pantalones', 'short', 'shorts', 'legging', 'leggings', 'jogger', 'joggers', 'buzo', 'buzos', 'falda', 'faldas', 'vestido', 'vestidos')),
        ('POLOS', ('polo', 'polos', 'camiseta', 'camisetas', 'jersey', 'bividi', 'top')),
        ('OTROS', ('mochila', 'mochilas', 'maletin', 'maletines', 'gorra', 'gorras', 'media', 'medias', 'calcetin', 'calcetines', 'botella', 'botellas', 'termo', 'termos', 'accesorio', 'accesorios')),
    )

    for Categoria, Palabras_Clave in Reglas:
        if any(Palabra in Tokens for Palabra in Palabras_Clave):
            return Categoria

    return None


def Normalizar_Categoria_Producto(Categoria_Original, Nombre_De_Producto=None):
    """Normaliza la categoría de un producto, infiriendo desde el nombre si es necesario."""
    Categoria_Detectada = Inferir_Categoria_Desde_Nombre(Nombre_De_Producto)
    if Categoria_Detectada:
        return Categoria_Detectada

    Categoria_Normalizada = str(Categoria_Original or '').strip().upper()
    if Categoria_Normalizada in {'MEDIAS', 'ACCESORIOS'}:
        return 'OTROS'
    return Categoria_Normalizada


# ─── Detección de Seguimiento de Pedido ──────────────────────────────────────

def Es_Consulta_De_Seguimiento_De_Pedido(Mensaje_Usuario):
    """Detecta si el usuario está preguntando por el estado de un pedido."""
    Texto = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Texto:
        return False

    if not re.search(r'\b(pedido|orden|compra|envio)\b', Texto):
        return False

    Tokens = set(Texto.split())
    Indicadores = {
        "rastrear", "rastreo", "seguimiento", "estado", "donde", "ubicacion",
        "ubica", "demora", "demoro", "llega", "llegara", "tracking", "guia"
    }
    if Tokens.intersection(Indicadores):
        return True

    Patrones = [
        r'donde\s+esta\s+mi\s+(pedido|orden|envio)',
        r'estado\s+de\s+mi\s+(pedido|orden|envio)',
        r'seguimiento\s+de\s+mi\s+(pedido|orden|envio)',
        r'rastre(?:ar|o)\s+mi\s+(pedido|orden|envio)',
    ]
    return any(re.search(P, Texto) for P in Patrones)


# ─── Reinicio de Filtros ─────────────────────────────────────────────────────

def Es_Solicitud_De_Reinicio_De_Filtros(Mensaje_Usuario):
    """Detecta si el usuario quiere ver todos los productos (reiniciar filtros)."""
    Texto = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Texto:
        return False

    Patrones = [
        r'\b(muestrame|mostrar|ensename|dame|quiero|ver)\s+(todo|todos|toda|todas)\b',
        r'\b(todo|todos|toda|todas)\s+los?\s+(productos|articulos|catalogo)\b',
        r'\b(reiniciar|limpiar|quitar)\s+filtros?\b',
        r'\b(busquemos|buscar|muestrame)\s+otra\s+cosa\b',
    ]
    return any(re.search(P, Texto) for P in Patrones)


# ─── Extracción de Filtros ───────────────────────────────────────────────────

def Extraer_Filtros(Mensaje_Usuario, Categorias_Dinamicas, Colores_Dinamicos):
    """
    Extrae del mensaje: categoría, color, precio máximo, talla y género.
    Usa fuzzy matching (thefuzz) para tolerar errores ortográficos.
    """
    Mensaje_Minusculas = Mensaje_Usuario.lower()
    Palabras = Mensaje_Minusculas.split()

    Color_Detectado = None
    Categoria_Detectada = None
    Genero_Detectado = None
    Precio_Maximo = None
    Talla_Detectada = None

    # Detectar género
    for Palabra in Palabras:
        if Palabra in Mapa_De_Genero and not Genero_Detectado:
            Genero_Detectado = Mapa_De_Genero[Palabra]

    # Detectar categoría (fuzzy)
    Opciones_Categorias = list(Categorias_Dinamicas) + list(_Sinonimos_De_Categorias.keys())
    if Opciones_Categorias:
        for Palabra in Palabras:
            if len(Palabra) <= 2 or Palabra in _Palabras_Vacias_De_Busqueda:
                continue
            if not Categoria_Detectada:
                Match = process.extractOne(Palabra, Opciones_Categorias)
                if Match and Match[1] >= 80 and (len(Palabra) / len(Match[0]) >= 0.5):
                    if Match[0] in _Sinonimos_De_Categorias:
                        Categoria_Detectada = _Sinonimos_De_Categorias[Match[0]]
                    else:
                        Categoria_Detectada = Match[0]
                    break

    # Detectar color (fuzzy)
    Opciones_Colores = list(Colores_Dinamicos) + list(_Sinonimos_De_Colores.keys())
    if Opciones_Colores:
        for Palabra in Palabras:
            if len(Palabra) <= 2 or Palabra in _Palabras_Vacias_De_Busqueda:
                continue
            if not Color_Detectado:
                Match = process.extractOne(Palabra, Opciones_Colores)
                if Match and Match[1] >= 90 and (len(Palabra) / len(Match[0]) >= 0.5):
                    if Match[0] in _Sinonimos_De_Colores:
                        Color_Detectado = _Sinonimos_De_Colores[Match[0]]
                    else:
                        Color_Detectado = Match[0]
                    break

    # Detectar talla
    Coincidencia_Talla = _Patron_De_Talla.search(Mensaje_Minusculas)
    if Coincidencia_Talla:
        Talla_Detectada = Coincidencia_Talla.group(1).upper()
        if Talla_Detectada.isdigit():
            Talla_Detectada = str(Talla_Detectada)

    # Detectar precio máximo
    Coincidencia_Precio = _Patron_De_Precio.search(Mensaje_Minusculas)
    if Coincidencia_Precio:
        Precio_Maximo = float(Coincidencia_Precio.group(1))
    else:
        Coincidencia_Directa = _Patron_De_Precio_Directo.search(Mensaje_Minusculas)
        if Coincidencia_Directa:
            Precio_Maximo = float(Coincidencia_Directa.group(1))

    return Categoria_Detectada, Color_Detectado, Precio_Maximo, Talla_Detectada, Genero_Detectado


# ─── Extracción de Palabras Clave ────────────────────────────────────────────

def Extraer_Palabras_Clave_De_Mensaje(Mensaje_Usuario):
    """Extrae palabras clave de búsqueda, excluyendo ruido y entidades ya detectadas."""
    Texto = Normalizar_Texto_Base(Mensaje_Usuario)
    Palabras_Clave = []

    _Ruidos_Excluir = {
        "menos", "hasta", "max", "maximo", "min", "minimo", "presupuesto",
        "sole", "sol", "soles", "precio", "precios", "costo", "costos",
        "cuanto", "cuesta", "vale", "valen", "color", "colores",
        "menor", "menores", "mayor", "mayores", "bajo", "bajos", "altos", "alto",
        "negro", "negra", "negros", "negras", "blanco", "blanca", "blancos", "blancas",
        "rojo", "roja", "rojos", "rojas", "azul", "azules", "gris", "grises",
        "verde", "verdes"
    }

    for Token in Texto.replace('-', ' ').split():
        if len(Token) < 3:
            continue

        Token = _Sinonimos_De_Palabras_Clave.get(Token, Token)

        if Token in _Palabras_Vacias_De_Busqueda:
            continue
        if Token in _Ruidos_Excluir:
            continue
        if Token in Mapa_De_Genero:
            continue
        if Token in {"talla", "tallas", "xs", "s", "m", "l", "xl", "xxl"}:
            continue
        if re.fullmatch(r'\d{2}', Token):
            continue
        if Token.isdigit():
            continue

        if Token not in Palabras_Clave:
            Palabras_Clave.append(Token)

    return Palabras_Clave


# ─── Detección de Producto por Texto ─────────────────────────────────────────

def Detectar_Id_De_Producto_En_Texto(Mensaje_Usuario, Indice_De_Nombres, Frecuencia_De_Tokens):
    """
    Intenta identificar un producto específico mencionado en el mensaje.
    Usa coincidencia por nombre normalizado y por tokens ponderados.
    """
    Texto = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Texto:
        return None

    # Coincidencia directa por nombre (>= 6 caracteres)
    for Producto in Indice_De_Nombres:
        if len(Producto['name_norm']) >= 6 and Producto['name_norm'] in Texto:
            return Producto['id']

    # Coincidencia por código (ej: "s-01")
    Coincidencia_Codigo = re.search(r'\bs\s*-?\s*(\d{1,4})\b', Texto)
    if Coincidencia_Codigo:
        Codigo = f"s-{Coincidencia_Codigo.group(1)}"
        for Producto in Indice_De_Nombres:
            if Codigo in Producto['name_norm']:
                return Producto['id']

    # Coincidencia por tokens (>= 2 palabras en común)
    Palabras_Mensaje = {
        T for T in Texto.replace('-', ' ').split()
        if len(T) > 2 and T not in Palabras_Vacias_Entidad_Producto
    }
    if not Palabras_Mensaje:
        return None

    # --- Primer intento: por proporción de coincidencias ---
    Mejor_Id = None
    Mejor_Puntaje = 0.0
    Segundo_Puntaje = 0.0

    for Producto in Indice_De_Nombres:
        Coincidencias = Palabras_Mensaje & Producto['tokens']
        if len(Coincidencias) < 2:
            continue

        Puntaje = len(Coincidencias) / len(Producto['tokens'])
        if Puntaje > Mejor_Puntaje:
            Segundo_Puntaje = Mejor_Puntaje
            Mejor_Puntaje = Puntaje
            Mejor_Id = Producto['id']
        elif Puntaje > Segundo_Puntaje:
            Segundo_Puntaje = Puntaje

    if Mejor_Id is not None and Mejor_Puntaje >= 0.60 and (Mejor_Puntaje - Segundo_Puntaje) >= 0.15:
        return Mejor_Id

    # --- Segundo intento: por peso IDF ---
    Mejor_Id = None
    Mejor_Peso = 0.0
    Segundo_Peso = 0.0
    Tokens_Mejor = set()

    for Producto in Indice_De_Nombres:
        Coincidencias = Palabras_Mensaje & Producto['tokens']
        if not Coincidencias:
            continue

        Peso = sum(1.0 / max(1, Frecuencia_De_Tokens.get(T, 1)) for T in Coincidencias)
        if len(Coincidencias) >= 2:
            Peso += 0.12
        if any(Frecuencia_De_Tokens.get(T, 99) <= 3 and len(T) >= 5 for T in Coincidencias):
            Peso += 0.18

        if Peso > Mejor_Peso:
            Segundo_Peso = Mejor_Peso
            Mejor_Peso = Peso
            Mejor_Id = Producto['id']
            Tokens_Mejor = set(Coincidencias)
        elif Peso > Segundo_Peso:
            Segundo_Peso = Peso

    if Mejor_Id is not None and Mejor_Peso >= 0.34:
        if (Mejor_Peso - Segundo_Peso) >= 0.08:
            return Mejor_Id

        Tiene_Digitos = any(re.search(r'\d', T) for T in Tokens_Mejor)
        Tiene_Unico = any(Frecuencia_De_Tokens.get(T, 99) == 1 for T in Tokens_Mejor)
        if len(Tokens_Mejor) >= 2 and (Tiene_Digitos or Tiene_Unico):
            return Mejor_Id

    return None


# ─── Inferencia de Etiqueta de Detalle ───────────────────────────────────────

def Inferir_Etiqueta_De_Detalle(
    Mensaje_Usuario,
    Ultima_Etiqueta=None,
    Hay_Producto_En_Contexto=False,
    Producto_Mencionado_En_Mensaje=False,
):
    """Si hay un producto en contexto, infiere si el usuario pregunta por precio, stock o color."""
    if not Hay_Producto_En_Contexto:
        return None

    Texto = Normalizar_Texto_Base(Mensaje_Usuario)
    Palabras = set(Texto.split())

    if Palabras.intersection({"talla", "tallas", "stock", "disponibilidad", "disponible", "queda", "quedan", "tiene", "tienen"}):
        return "consultar_stock_item"
    if Palabras.intersection({"precio", "precios", "costo", "costos", "cuanto", "cuesta", "vale", "valen"}):
        return "consultar_precio_item"
    if Palabras.intersection({"color", "colores"}):
        return "colores"

    if Palabras.intersection({"categoria", "categorias", "genero"}):
        return None

    if Producto_Mencionado_En_Mensaje and Ultima_Etiqueta in {"consultar_stock_item", "consultar_precio_item"}:
        return Ultima_Etiqueta

    return None
