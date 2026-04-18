import re
import unicodedata
from thefuzz import process
from utils_nlp import limpiar_texto as Normalizar_Texto_Base_NLP

Mapa_De_Genero = {
    "mujer": "Mujer", "mujeres": "Mujer", "dama": "Mujer", "damas": "Mujer",
    "hombre": "Hombre", "hombres": "Hombre", "varon": "Hombre", "caballero": "Hombre",
    "unisex": "Unisex"
}

Patron_De_Talla = re.compile(r'(?:talla|en)\s+(xs|s|m|l|xl|xxl|\d{2})')
Patron_De_Precio = re.compile(r'(?:menos de|bajo|hasta|max|maximo|menor a|menores a|menores que|presupuesto de|presupuesto|<=)\s*(\d+)')
Patron_De_Precio_Directo = re.compile(r'(?<!\d)(\d{2,4})(?:\s*(?:soles?|s/?\.?))')
Palabras_Vacias_Entidad_Producto = {
    "de", "del", "la", "el", "los", "las", "para", "con", "en", "por", "y", "o", "un", "una", "unos", "unas"
}
Palabras_Vacias_De_Busqueda = {
    "quiero", "quisiera", "busco", "mostrar", "muestrame", "dame", "tienes", "tiene", "hay", "del", "devolver", "devolucion",
    "de", "la", "el", "los", "las", "para", "con", "en", "por", "un", "una", "unos", "unas", "este", "esta",
    "producto", "productos", "me", "porfavor", "porfa", "por", "tengo", "soles", "sol", "precio", "presupuesto",
    "ver", "comprar", "saber", "conseguir", "alguna", "algun", "algo", "estan", "hola", "buenas", "buenos", "dias", "tardes", "noches",
    "todo", "todos", "toda", "todas", "mejor", "que"
}
Mapa_De_Sinonimos_De_Palabras_Clave = {
    "zapatillas": "zapatilla",
    "zapas": "zapatilla",
    "polos": "polo",
    "pantalones": "pantalon",
    "faldas": "falda",
    "vestidos": "vestido",
    "leggings": "legging",
    "joggers": "jogger",
    "shorts": "short",
    "gorras": "gorra",
    "mochilas": "mochila",
    "casacas": "casaca",
    "medias": "media",
    "calcetines": "calcetin",
    "tomatodos": "tomatodo",
    "botella": "tomatodo",
    "botellas": "tomatodo",
    "termo": "tomatodo",
    "termos": "tomatodo",
}


def Normalizar_Texto_Base_De_Categoria(Texto_Entrada):
    Texto_En_Minusculas = str(Texto_Entrada or '').strip().lower()
    Texto_Sin_Acentos = ''.join(
        Caracter for Caracter in unicodedata.normalize('NFD', Texto_En_Minusculas)
        if unicodedata.category(Caracter) != 'Mn'
    )
    return re.sub(r'\s+', ' ', Texto_Sin_Acentos).strip()


def Inferir_Categoria_Desde_Nombre(Nombre_De_Producto):
    Nombre_Normalizado = Normalizar_Texto_Base_De_Categoria(Nombre_De_Producto)
    if not Nombre_Normalizado:
        return None

    Tokens_Del_Nombre = set(re.findall(r'[a-z0-9]+', Nombre_Normalizado))
    if not Tokens_Del_Nombre:
        return None

    Reglas_De_Categoria = (
        ('CALZADO', ('zapatilla', 'zapatillas', 'zapato', 'zapatos', 'botin', 'botines', 'chimpun', 'chimpunes', 'tenis')),
        ('PANTALONES', ('pantalon', 'pantalones', 'short', 'shorts', 'legging', 'leggings', 'jogger', 'joggers', 'buzo', 'buzos', 'falda', 'faldas', 'vestido', 'vestidos')),
        ('POLOS', ('polo', 'polos', 'camiseta', 'camisetas', 'jersey', 'bividi', 'top')),
        ('OTROS', ('mochila', 'mochilas', 'maletin', 'maletines', 'gorra', 'gorras', 'media', 'medias', 'calcetin', 'calcetines', 'botella', 'botellas', 'termo', 'termos', 'accesorio', 'accesorios')),
    )

    for Categoria_De_Regla, Palabras_Clave in Reglas_De_Categoria:
        if any(Palabra_Clave in Tokens_Del_Nombre for Palabra_Clave in Palabras_Clave):
            return Categoria_De_Regla

    return None


def Normalizar_Categoria_Producto(Categoria_Original, Nombre_De_Producto=None):
    Categoria_Detectada_Por_Nombre = Inferir_Categoria_Desde_Nombre(Nombre_De_Producto)
    if Categoria_Detectada_Por_Nombre:
        return Categoria_Detectada_Por_Nombre

    Categoria_Normalizada = str(Categoria_Original or '').strip().upper()
    if Categoria_Normalizada in {'MEDIAS', 'ACCESORIOS'}:
        return 'OTROS'
    return Categoria_Normalizada


def Normalizar_Texto_Base(Texto_Entrada):
    return Normalizar_Texto_Base_NLP(Texto_Entrada or '')


def Es_Consulta_De_Seguimiento_De_Pedido(Mensaje_Usuario):
    Texto_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Texto_Normalizado:
        return False

    if not re.search(r'\b(pedido|orden|compra|envio)\b', Texto_Normalizado):
        return False

    Tokens_Del_Mensaje = set(Texto_Normalizado.split())
    Indicadores_De_Seguimiento = {
        "rastrear", "rastreo", "seguimiento", "estado", "donde", "ubicacion", "ubica",
        "demora", "demoro", "llega", "llegara", "tracking", "guia"
    }
    if Tokens_Del_Mensaje.intersection(Indicadores_De_Seguimiento):
        return True

    Patrones_De_Seguimiento = [
        r'donde\s+esta\s+mi\s+(pedido|orden|envio)',
        r'estado\s+de\s+mi\s+(pedido|orden|envio)',
        r'seguimiento\s+de\s+mi\s+(pedido|orden|envio)',
        r'rastre(?:ar|o)\s+mi\s+(pedido|orden|envio)',
    ]
    return any(re.search(Patron, Texto_Normalizado) for Patron in Patrones_De_Seguimiento)


def Es_Solicitud_De_Reinicio_De_Filtros(Mensaje_Usuario):
    Texto_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Texto_Normalizado:
        return False

    Patrones_De_Reinicio = [
        r'\b(muestrame|mostrar|ensename|dame|quiero|ver)\s+(todo|todos|toda|todas)\b',
        r'\b(todo|todos|toda|todas)\s+los?\s+(productos|articulos|catalogo)\b',
        r'\b(reiniciar|limpiar|quitar)\s+filtros?\b',
        r'\b(busquemos|buscar|muestrame)\s+otra\s+cosa\b',
    ]
    return any(re.search(Patron, Texto_Normalizado) for Patron in Patrones_De_Reinicio)

def Extraer_Filtros(Mensaje_Usuario, Categorias_Dinamicas, Colores_Dinamicos):
    """Extrae categoría, color, precio y talla del mensaje del usuario usando thefuzz."""
    Mensaje_En_Minusculas = Mensaje_Usuario.lower()
    Palabras_Separadas = Mensaje_En_Minusculas.split()

    Color_Detectado = None
    Categoria_Detectada = None
    Genero_Detectado = None
    Precio_Maximo_Detectado = None
    Talla_Detectada = None

    for Palabra in Palabras_Separadas:
        if Palabra in Mapa_De_Genero and not Genero_Detectado:
            Genero_Detectado = Mapa_De_Genero[Palabra]

    Sinonimos_De_Categorias = {
        "zapatillas": "CALZADO", "zapatilla": "CALZADO", "zapas": "CALZADO", "zapatos": "CALZADO", "zapato": "CALZADO",
        "botines": "CALZADO", "botin": "CALZADO", "chimpunes": "CALZADO", "botas": "CALZADO",
        "polo": "POLOS", "camiseta": "POLOS", "camisetas": "POLOS", "jersey": "POLOS", "bividi": "POLOS",
        "pantalon": "PANTALONES", "pantalones": "PANTALONES", "short": "PANTALONES", "shorts": "PANTALONES", "leggings": "PANTALONES", "buzo": "PANTALONES",
        "falda": "PANTALONES", "faldas": "PANTALONES", "vestido": "PANTALONES", "vestidos": "PANTALONES",
        "medias": "OTROS", "calcetines": "OTROS", "tobilleras": "OTROS", "accesorios": "OTROS", "accesorio": "OTROS",
        "gorra": "OTROS", "gorras": "OTROS", "mochila": "OTROS", "mochilas": "OTROS", "reloj": "OTROS", "guantes": "OTROS",
        "botella": "OTROS", "termo": "OTROS"
    }

    Sinonimos_De_Colores = {
        "negra": "Negro", "negros": "Negro", "negras": "Negro",
        "blanca": "Blanco", "blancos": "Blanco", "blancas": "Blanco",
        "roja": "Rojo", "rojos": "Rojo", "rojas": "Rojo",
        "azules": "Azul",
        "grises": "Gris",
        "verdes": "Verde"
    }

    Opciones_Categorias = list(Categorias_Dinamicas) + list(Sinonimos_De_Categorias.keys())
    if Opciones_Categorias:
        for Palabra in Palabras_Separadas:
            if len(Palabra) <= 2 or Palabra in Palabras_Vacias_De_Busqueda:
                continue
            if not Categoria_Detectada:
                Match_Cat = process.extractOne(Palabra, Opciones_Categorias)
                if Match_Cat and Match_Cat[1] >= 80 and (len(Palabra) / len(Match_Cat[0]) >= 0.5):
                    if Match_Cat[0] in Sinonimos_De_Categorias:
                        Categoria_Detectada = Sinonimos_De_Categorias[Match_Cat[0]]
                    else:
                        Categoria_Detectada = Match_Cat[0]
                    break

    Opciones_Colores = list(Colores_Dinamicos) + list(Sinonimos_De_Colores.keys())
    if Opciones_Colores:
        for Palabra in Palabras_Separadas:
            if len(Palabra) <= 2 or Palabra in Palabras_Vacias_De_Busqueda:
                continue
            if not Color_Detectado:
                Match_Color = process.extractOne(Palabra, Opciones_Colores)
                if Match_Color and Match_Color[1] >= 90 and (len(Palabra) / len(Match_Color[0]) >= 0.5):
                    if Match_Color[0] in Sinonimos_De_Colores:
                        Color_Detectado = Sinonimos_De_Colores[Match_Color[0]]
                    else:
                        Color_Detectado = Match_Color[0]
                    break

    Coincidencia_De_Talla = Patron_De_Talla.search(Mensaje_En_Minusculas)
    if Coincidencia_De_Talla:
        Talla_Detectada = Coincidencia_De_Talla.group(1).upper()
        if Talla_Detectada.isdigit():
            Talla_Detectada = str(Talla_Detectada)

    Coincidencia_De_Precio = Patron_De_Precio.search(Mensaje_En_Minusculas)
    if Coincidencia_De_Precio:
        Precio_Maximo_Detectado = float(Coincidencia_De_Precio.group(1))
    else:
        Coincidencia_De_Precio_Directo = Patron_De_Precio_Directo.search(Mensaje_En_Minusculas)
        if Coincidencia_De_Precio_Directo:
            Precio_Maximo_Detectado = float(Coincidencia_De_Precio_Directo.group(1))

    return Categoria_Detectada, Color_Detectado, Precio_Maximo_Detectado, Talla_Detectada, Genero_Detectado

def Extraer_Palabras_Clave_De_Mensaje(Mensaje_Usuario):
    Mensaje_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    Palabras_Clave = []
    
    # Ruidos de presupuesto y colores comunes para excluir de keywords de búsqueda pura
    Ruidos_Excluir = {
        "menos", "hasta", "max", "maximo", "min", "minimo", "presupuesto",
        "sole", "sol", "soles", "precio", "precios", "costo", "costos",
        "cuanto", "cuesta", "vale", "valen", "color", "colores",
        "negro", "negra", "negros", "negras", "blanco", "blanca", "blancos", "blancas",
        "rojo", "roja", "rojos", "rojas", "azul", "azules", "gris", "grises", "verde", "verdes"
    }
    
    for Token in Mensaje_Normalizado.replace('-', ' ').split():
        Token_Original = Token
        if len(Token) < 3:
            continue
        
        Token = Mapa_De_Sinonimos_De_Palabras_Clave.get(Token, Token)
        if Token in Palabras_Vacias_De_Busqueda:
            continue
        if Token in Ruidos_Excluir:
            continue
            
        # Evitar duplicar genero como keyword si ya es entidad
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


def Detectar_Id_De_Producto_En_Texto(Mensaje_Usuario, Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto):
    Mensaje_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Mensaje_Normalizado:
        return None

    for Producto_Indexado in Indice_De_Nombres_De_Producto:
        Nombre_Normalizado = Producto_Indexado['name_norm']
        if len(Nombre_Normalizado) >= 6 and Nombre_Normalizado in Mensaje_Normalizado:
            return Producto_Indexado['id']

    Coincidencia_De_Codigo = re.search(r'\bs\s*-?\s*(\d{1,4})\b', Mensaje_Normalizado)
    if Coincidencia_De_Codigo:
        Codigo_Buscado = f"s-{Coincidencia_De_Codigo.group(1)}"
        for Producto_Indexado in Indice_De_Nombres_De_Producto:
            if Codigo_Buscado in Producto_Indexado['name_norm']:
                return Producto_Indexado['id']

    Palabras_Del_Mensaje = {
        Token
        for Token in Mensaje_Normalizado.replace('-', ' ').split()
        if len(Token) > 2 and Token not in Palabras_Vacias_Entidad_Producto
    }
    if not Palabras_Del_Mensaje:
        return None

    Mejor_Id = None
    Mejor_Puntaje = 0.0
    Segundo_Puntaje = 0.0
    for Producto_Indexado in Indice_De_Nombres_De_Producto:
        Tokens_De_Producto = Producto_Indexado['tokens']
        Coincidencias = Palabras_Del_Mensaje & Tokens_De_Producto
        if len(Coincidencias) < 2:
            continue

        Puntaje = len(Coincidencias) / len(Tokens_De_Producto)
        if Puntaje > Mejor_Puntaje:
            Segundo_Puntaje = Mejor_Puntaje
            Mejor_Puntaje = Puntaje
            Mejor_Id = Producto_Indexado['id']
        elif Puntaje > Segundo_Puntaje:
            Segundo_Puntaje = Puntaje

    if Mejor_Id is not None and Mejor_Puntaje >= 0.60 and (Mejor_Puntaje - Segundo_Puntaje) >= 0.15:
        return Mejor_Id

    Mejor_Id = None
    Mejor_Peso = 0.0
    Segundo_Peso = 0.0
    Tokens_Del_Mejor = set()

    for Producto_Indexado in Indice_De_Nombres_De_Producto:
        Tokens_De_Producto = Producto_Indexado['tokens']
        Coincidencias = Palabras_Del_Mensaje & Tokens_De_Producto
        if not Coincidencias:
            continue

        Peso_De_Coincidencia = 0.0
        for Token in Coincidencias:
            Frecuencia = max(1, Frecuencia_De_Tokens_De_Producto.get(Token, 1))
            Peso_De_Coincidencia += 1.0 / Frecuencia

        if len(Coincidencias) >= 2:
            Peso_De_Coincidencia += 0.12
        if any(Frecuencia_De_Tokens_De_Producto.get(Token, 99) <= 3 and len(Token) >= 5 for Token in Coincidencias):
            Peso_De_Coincidencia += 0.18

        if Peso_De_Coincidencia > Mejor_Peso:
            Segundo_Peso = Mejor_Peso
            Mejor_Peso = Peso_De_Coincidencia
            Mejor_Id = Producto_Indexado['id']
            Tokens_Del_Mejor = set(Coincidencias)
        elif Peso_De_Coincidencia > Segundo_Peso:
            Segundo_Peso = Peso_De_Coincidencia

    if Mejor_Id is not None and Mejor_Peso >= 0.34:
        if (Mejor_Peso - Segundo_Peso) >= 0.08:
            return Mejor_Id

        Tiene_Token_Con_Digitos = any(re.search(r'\d', Token) for Token in Tokens_Del_Mejor)
        Tiene_Token_Unico = any(Frecuencia_De_Tokens_De_Producto.get(Token, 99) == 1 for Token in Tokens_Del_Mejor)
        if len(Tokens_Del_Mejor) >= 2 and (Tiene_Token_Con_Digitos or Tiene_Token_Unico):
            return Mejor_Id

    return None

def Inferir_Etiqueta_De_Detalle(Mensaje_Usuario, Ultima_Etiqueta=None, Hay_Producto_En_Contexto=False, Producto_Mencionado_En_Mensaje=False):
    if not Hay_Producto_En_Contexto:
        return None

    Texto_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    Palabras_Del_Mensaje = set(Texto_Normalizado.split())

    Indicadores_De_Stock = {"talla", "tallas", "stock", "disponibilidad", "disponible", "queda", "quedan", "tiene", "tienen"}
    Indicadores_De_Precio = {"precio", "precios", "costo", "costos", "cuanto", "cuesta", "vale", "valen"}

    if Palabras_Del_Mensaje.intersection(Indicadores_De_Stock):
        return "consultar_stock_item"
    if Palabras_Del_Mensaje.intersection(Indicadores_De_Precio):
        return "consultar_precio_item"

    if Palabras_Del_Mensaje.intersection({"color", "colores"}):
        return "colores"

    Indicadores_De_Consulta_General = {"categoria", "categorias", "genero"}
    if Palabras_Del_Mensaje.intersection(Indicadores_De_Consulta_General):
        return None

    if Producto_Mencionado_En_Mensaje and Ultima_Etiqueta in {"consultar_stock_item", "consultar_precio_item"}:
        return Ultima_Etiqueta

    return None
