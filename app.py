import json
import os
import random
import re
import unicodedata
import shelve

from utils_texto import tokenizar as Tokenizar_Texto



import numpy as np
import torch
from flask import Flask, request, jsonify
from flask_cors import CORS
from model_arch import NeuralNet

app = Flask(__name__)
CORS(app)

Ruta_Modelo_Pytorch = "data/model.pth"
Ruta_Intents = "data/intents.json"
Ruta_Productos_Automaticos = "data/products.json"
Ruta_Productos_Scrapeados = "data/products_scraped.json"
Fuentes_De_Catalogo_Validas = {"auto", "scraped"}
Umbral_De_Confianza = 0.75
Umbral_De_Margen_Base = 0.08
Umbral_De_Margen_Por_Tag = {
    "buscar_producto": 0.10,
    "colores": 0.10,
    "consultar_stock_item": 0.10,
    "fuera_de_dominio": 0.12,
}
Maximo_Historial_Chat = 10
Limite_Busqueda_Por_Defecto = 20
Maximo_Limite_De_Busqueda = 50
Ruta_Memoria_Del_Chat = "data/chat_memory"

# ============================================================
# 1. CARGA DE IA Y DATOS
# ============================================================
Dispositivo = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
Modelo_IA = None
Todas_Las_Palabras = []
Etiquetas_De_Intencion = []

# Cargar modelo PyTorch
if os.path.exists(Ruta_Modelo_Pytorch):
    try:
        data_model = torch.load(Ruta_Modelo_Pytorch, map_location=Dispositivo, weights_only=False)
        Modelo_IA = NeuralNet(data_model["input_size"], data_model["hidden_size"], data_model["output_size"]).to(Dispositivo)
        Modelo_IA.load_state_dict(data_model["model_state"])
        Modelo_IA.eval()
        Todas_Las_Palabras = data_model["all_words"]
        Etiquetas_De_Intencion = data_model["tags"]
        print("[OK] Modelo PyTorch cargado.")
    except Exception as e:
        print(f"[ERROR] Modelo .pth: {e}")
else:
    print("[WARN] No se encontro model.pth. Ejecuta train_pytorch.py primero.")

# Cargar intents
with open(Ruta_Intents, 'r', encoding='utf-8') as f:
    Datos_De_Intents = json.load(f)


def Normalizar_Categoria_Producto(Categoria_Original):
    Categoria_Normalizada = str(Categoria_Original or '').strip().upper()
    if Categoria_Normalizada in {'MEDIAS', 'ACCESORIOS'}:
        return 'OTROS'
    return Categoria_Normalizada


def Normalizar_Producto_Cargado(Producto_Original):
    if not isinstance(Producto_Original, dict):
        return None

    Producto_Normalizado = dict(Producto_Original)
    Producto_Normalizado['category'] = Normalizar_Categoria_Producto(Producto_Normalizado.get('category'))
    return Producto_Normalizado

def Cargar_Lista_De_Productos_Desde_Archivo(Ruta_Archivo):
    if not os.path.exists(Ruta_Archivo):
        return []

    try:
        with open(Ruta_Archivo, 'r', encoding='utf-8') as Archivo_Productos:
            Lista_De_Productos = json.load(Archivo_Productos)
        if isinstance(Lista_De_Productos, list):
            Lista_Normalizada = []
            for Producto_Actual in Lista_De_Productos:
                Producto_Normalizado = Normalizar_Producto_Cargado(Producto_Actual)
                if Producto_Normalizado is not None:
                    Lista_Normalizada.append(Producto_Normalizado)
            return Lista_Normalizada
    except Exception as exc:
        print(f"[ERROR] No se pudo cargar {Ruta_Archivo}: {exc}")

    return []


def Normalizar_Fuente_De_Catalogo(Fuente_Solicitada):
    Fuente_En_Minusculas = str(Fuente_Solicitada or "auto").strip().lower()
    if Fuente_En_Minusculas in {"scraped", "scrapeado", "scraping", "catalogo_scrapeado"}:
        return "scraped"
    return "auto"


# Cargar catalogos de productos
Catalogos_De_Productos = {
    "auto": Cargar_Lista_De_Productos_Desde_Archivo(Ruta_Productos_Automaticos),
    "scraped": Cargar_Lista_De_Productos_Desde_Archivo(Ruta_Productos_Scrapeados),
}

if Catalogos_De_Productos["auto"]:
    print(f"[OK] Inventario auto: {len(Catalogos_De_Productos['auto'])} productos cargados.")
else:
    print("[WARN] No se encontro products.json. Generando inventario temporal...")
    try:
        from generate_products import Generar_Productos

        Catalogos_De_Productos["auto"] = Generar_Productos()
        print(f"[OK] Inventario temporal auto generado: {len(Catalogos_De_Productos['auto'])} productos.")
    except Exception as exc:
        print(f"[ERROR] No se pudo generar inventario temporal: {exc}")

if Catalogos_De_Productos["scraped"]:
    print(f"[OK] Inventario scrapeado: {len(Catalogos_De_Productos['scraped'])} productos cargados.")
else:
    print("[INFO] Aun no existe data/products_scraped.json. El switch web usara catalogo auto como fallback.")

Fuente_Activa_De_Catalogo = "auto"
Datos_De_Productos = Catalogos_De_Productos["auto"]


def Cambiar_Fuente_De_Catalogo(Fuente_Solicitada):
    global Datos_De_Productos
    global Fuente_Activa_De_Catalogo

    Fuente_Normalizada = Normalizar_Fuente_De_Catalogo(Fuente_Solicitada)
    if Fuente_Normalizada not in Fuentes_De_Catalogo_Validas:
        Fuente_Normalizada = "auto"

    Lista_De_Productos = Catalogos_De_Productos.get(Fuente_Normalizada, [])
    if not Lista_De_Productos:
        Fuente_Normalizada = "auto"
        Lista_De_Productos = Catalogos_De_Productos.get("auto", [])

    Cambio_De_Fuente = Fuente_Activa_De_Catalogo != Fuente_Normalizada
    Datos_De_Productos = Lista_De_Productos
    Fuente_Activa_De_Catalogo = Fuente_Normalizada

    if Cambio_De_Fuente or not Indice_De_Nombres_De_Producto:
        Reconstruir_Indice_De_Nombres_De_Producto()

    return Fuente_Activa_De_Catalogo

# ============================================================
# 2. FUNCIONES DE IA
# ============================================================

def Construir_Bolsa_De_Palabras(Palabras_Tokenizadas, Vocabulario_Total):
    Bolsa_De_Palabras = np.zeros(len(Vocabulario_Total), dtype=np.float32)
    for Indice, Palabra in enumerate(Vocabulario_Total):
        if Palabra in Palabras_Tokenizadas:
            Bolsa_De_Palabras[Indice] = 1.0
    return Bolsa_De_Palabras


def Predecir_Tag(Texto_Consulta):
    """Usa el modelo PyTorch para predecir el tag de una oración."""
    if not Modelo_IA:
        return None, 0.0, 0.0

    Palabras = Tokenizar_Texto(Texto_Consulta)
    Vector_Entrada = Construir_Bolsa_De_Palabras(Palabras, Todas_Las_Palabras)
    Vector_Entrada = Vector_Entrada.reshape(1, Vector_Entrada.shape[0])
    Vector_Entrada = torch.from_numpy(Vector_Entrada).to(Dispositivo)

    Salida_Modelo = Modelo_IA(Vector_Entrada)
    _, Indice_Predicho = torch.max(Salida_Modelo, dim=1)
    Etiqueta_Predicha = Etiquetas_De_Intencion[Indice_Predicho.item()]

    Probabilidades = torch.softmax(Salida_Modelo, dim=1)
    Probabilidades_Top = torch.topk(Probabilidades, k=min(2, Probabilidades.shape[1]), dim=1)
    Confianza_Predicha = Probabilidades_Top.values[0][0].item()
    Confianza_Segunda = Probabilidades_Top.values[0][1].item() if Probabilidades.shape[1] > 1 else 0.0
    Margen_De_Confianza = Confianza_Predicha - Confianza_Segunda

    return Etiqueta_Predicha, Confianza_Predicha, Margen_De_Confianza

# ============================================================
# 3. BÚSQUEDA INTELIGENTE DE PRODUCTOS
# ============================================================
Mapa_De_Colores = {
    "negro": "Negro", "negra": "Negro", "negros": "Negro", "negras": "Negro",
    "blanco": "Blanco", "blanca": "Blanco", "blancos": "Blanco", "blancas": "Blanco",
    "rojo": "Rojo", "roja": "Rojo", "rojos": "Rojo", "rojas": "Rojo",
    "azul": "Azul", "azules": "Azul",
    "gris": "Gris", "grises": "Gris",
    "verde": "Verde", "verdes": "Verde"
}

Mapa_De_Categorias = {
    "zapatillas": "CALZADO", "zapatilla": "CALZADO", "zapas": "CALZADO",
    "zapa": "CALZADO", "zapatos": "CALZADO",
    "zapato": "CALZADO", "botines": "CALZADO", "botin": "CALZADO",
    "chimpunes": "CALZADO", "chimpun": "CALZADO", "calzado": "CALZADO", "botas": "CALZADO",
    "polos": "POLOS", "polo": "POLOS", "camiseta": "POLOS",
    "camisetas": "POLOS", "jersey": "POLOS", "top": "POLOS", "bividi": "POLOS",
    "pantalones": "PANTALONES", "pantalon": "PANTALONES", "short": "PANTALONES",
    "shorts": "PANTALONES", "leggings": "PANTALONES", "buzo": "PANTALONES",
    "medias": "OTROS", "calcetines": "OTROS", "tobilleras": "OTROS",
    "accesorios": "OTROS", "accesorio": "OTROS", "otros": "OTROS", "otro": "OTROS",
    "gorra": "OTROS", "gorras": "OTROS", "mochila": "OTROS", "mochilas": "OTROS",
    "reloj": "OTROS", "guantes": "OTROS", "botella": "OTROS", "botellas": "OTROS",
    "termo": "OTROS", "termos": "OTROS"
}

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
    "quiero", "quisiera", "busco", "mostrar", "muestrame", "muestrame", "dame", "tienes", "tiene", "hay", "del",
    "de", "la", "el", "los", "las", "para", "con", "en", "por", "un", "una", "unos", "unas", "este", "esta",
    "producto", "productos", "me", "porfavor", "porfa", "por", "tengo", "soles", "sol", "precio", "presupuesto"
}
Mapa_De_Sinonimos_De_Palabras_Clave = {
    "tomatodos": "tomatodo",
    "botella": "tomatodo",
    "botellas": "tomatodo",
    "termo": "tomatodo",
    "termos": "tomatodo",
}
Indice_De_Nombres_De_Producto = []
Frecuencia_De_Tokens_De_Producto = {}


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

def Extraer_Filtros(Mensaje_Usuario):
    """Extrae categoría, color, precio y talla del mensaje del usuario."""
    Mensaje_En_Minusculas = Mensaje_Usuario.lower()
    Palabras_Separadas = Mensaje_En_Minusculas.split()
    
    Color_Detectado = None
    Categoria_Detectada = None
    Genero_Detectado = None
    Precio_Maximo_Detectado = None
    Talla_Detectada = None
    
    for Palabra in Palabras_Separadas:
        if Palabra in Mapa_De_Colores and not Color_Detectado:
            Color_Detectado = Mapa_De_Colores[Palabra]
        if Palabra in Mapa_De_Categorias and not Categoria_Detectada:
            Categoria_Detectada = Mapa_De_Categorias[Palabra]
        if Palabra in Mapa_De_Genero and not Genero_Detectado:
            Genero_Detectado = Mapa_De_Genero[Palabra]

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
    for Token in Mensaje_Normalizado.replace('-', ' ').split():
        Token_Original = Token
        if len(Token) < 3:
            continue
        Token = Mapa_De_Sinonimos_De_Palabras_Clave.get(Token, Token)
        Es_Sinonimo_Dominio = Token != Token_Original
        if Token in Palabras_Vacias_De_Busqueda:
            continue
        if (not Es_Sinonimo_Dominio) and (Token in Mapa_De_Categorias or Token in Mapa_De_Colores or Token in Mapa_De_Genero):
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


def Debe_Heredar_Filtros_De_Contexto(
    Contexto_Actual,
    Mensaje_Usuario,
    Categoria_Filtro,
    Color_Filtro,
    Precio_Maximo_Filtro,
    Talla_Filtro,
    Genero_Filtro,
):
    Filtros_Anteriores = Contexto_Actual.get("last_filters", {}) if isinstance(Contexto_Actual, dict) else {}
    if not isinstance(Filtros_Anteriores, dict) or not Filtros_Anteriores:
        return False

    Hay_Filtros_En_Mensaje = any([
        Categoria_Filtro,
        Color_Filtro,
        Precio_Maximo_Filtro is not None,
        Talla_Filtro,
        Genero_Filtro,
    ])
    if not Hay_Filtros_En_Mensaje:
        return False

    Ultimo_Tag = Contexto_Actual.get("last_tag")
    if Ultimo_Tag not in {
        "buscar_producto",
        "filtrar_categoria",
        "filtrar_genero",
        "consulta_precio",
        "consultar_stock_item",
        "colores",
    }:
        return False

    Tokens_Del_Mensaje = Normalizar_Texto_Base(Mensaje_Usuario).split()
    if len(Tokens_Del_Mensaje) <= 4:
        return True

    if Tokens_Del_Mensaje and Tokens_Del_Mensaje[0] in {"y", "ademas", "tambien"}:
        return True

    if Genero_Filtro and not any([Categoria_Filtro, Color_Filtro, Precio_Maximo_Filtro is not None, Talla_Filtro]) and len(Tokens_Del_Mensaje) <= 6:
        return True

    if Color_Filtro and not any([Categoria_Filtro, Genero_Filtro, Precio_Maximo_Filtro is not None, Talla_Filtro]) and len(Tokens_Del_Mensaje) <= 6:
        return True

    return False


def Heredar_Filtros_De_Contexto(
    Contexto_Actual,
    Categoria_Filtro,
    Color_Filtro,
    Precio_Maximo_Filtro,
    Talla_Filtro,
    Genero_Filtro,
    Palabras_Clave_Detectadas,
):
    Filtros_Anteriores = Contexto_Actual.get("last_filters", {}) if isinstance(Contexto_Actual, dict) else {}
    if not isinstance(Filtros_Anteriores, dict):
        Filtros_Anteriores = {}

    Categoria_Final = Categoria_Filtro or Filtros_Anteriores.get("category")
    Color_Final = Color_Filtro or Filtros_Anteriores.get("color")
    Precio_Maximo_Final = Precio_Maximo_Filtro if Precio_Maximo_Filtro is not None else Filtros_Anteriores.get("max_price")
    Talla_Final = Talla_Filtro or Filtros_Anteriores.get("talla")
    Genero_Final = Genero_Filtro or Filtros_Anteriores.get("genero")

    # No heredamos keywords automaticamente para evitar arrastrar ruido (ej. "soles").
    Keywords_Finales = Palabras_Clave_Detectadas if isinstance(Palabras_Clave_Detectadas, list) else []

    return (
        Categoria_Final,
        Color_Final,
        Precio_Maximo_Final,
        Talla_Final,
        Genero_Final,
        Keywords_Finales,
    )


def Buscar_Productos(Categoria=None, Color=None, Precio_Maximo=None, Talla=None, Genero=None, Palabras_Clave=None, Limite=5):
    """Busca productos filtrados por categoría, color, precio y/o talla."""
    Resultados = Datos_De_Productos
    
    if Categoria:
        Resultados = [p for p in Resultados if p['category'] == Categoria]
    if Color:
        Resultados = [
            p
            for p in Resultados
            if Color in Obtener_Colores_De_Producto(p)
        ]
    if Precio_Maximo is not None:
        Resultados = [p for p in Resultados if p['price'] <= Precio_Maximo]
    if Talla:
        # Algunos productos pueden no tener tallas definidas.
        Resultados = [p for p in Resultados if 'tallas' in p and Talla in p['tallas']]
    if Genero:
        Resultados = [p for p in Resultados if p.get('genero') == Genero]

    Lista_De_Palabras_Clave = []
    if isinstance(Palabras_Clave, str) and Palabras_Clave.strip():
        Lista_De_Palabras_Clave = Extraer_Palabras_Clave_De_Mensaje(Palabras_Clave)
    elif isinstance(Palabras_Clave, list):
        Lista_De_Palabras_Clave = [str(Palabra).lower() for Palabra in Palabras_Clave if str(Palabra).strip()]

    if Lista_De_Palabras_Clave:
        Resultados_Textuales = []
        for Producto in Resultados:
            Texto_De_Producto = " ".join([
                str(Producto.get('name', '')),
                str(Producto.get('description', '')),
                str(Producto.get('category', '')),
                str(Producto.get('genero', '')),
                " ".join(Obtener_Colores_De_Producto(Producto)),
                " ".join(Producto.get('tallas', [])) if isinstance(Producto.get('tallas'), list) else ''
            ])
            Texto_De_Producto_Normalizado = Normalizar_Texto_Base(Texto_De_Producto)
            if any(Palabra_Clave in Texto_De_Producto_Normalizado for Palabra_Clave in Lista_De_Palabras_Clave):
                Resultados_Textuales.append(Producto)
        Resultados = Resultados_Textuales
    
    if not Resultados:
        return []
    
    try:
        Limite_Seguro = max(1, int(Limite))
    except (TypeError, ValueError):
        Limite_Seguro = 5

    # Devolver hasta 'limit' productos al azar
    return random.sample(Resultados, min(Limite_Seguro, len(Resultados)))


def Obtener_Colores_De_Producto(Producto):
    Colores_Registrados = Producto.get('colores')
    if isinstance(Colores_Registrados, list) and Colores_Registrados:
        return Colores_Registrados

    Color_Unico = Producto.get('color')
    return [Color_Unico] if Color_Unico else []


def Normalizar_Texto_Base(Texto_Entrada):
    Texto_En_Minusculas = (Texto_Entrada or '').lower().strip()
    Texto_Sin_Tildes = unicodedata.normalize('NFKD', Texto_En_Minusculas)
    Texto_Sin_Tildes = ''.join(Caracter for Caracter in Texto_Sin_Tildes if not unicodedata.combining(Caracter))
    Texto_Limpio = re.sub(r'[^a-z0-9\s-]', ' ', Texto_Sin_Tildes)
    return re.sub(r'\s+', ' ', Texto_Limpio).strip()


def Reconstruir_Indice_De_Nombres_De_Producto():
    global Indice_De_Nombres_De_Producto
    global Frecuencia_De_Tokens_De_Producto
    Indice_De_Nombres_De_Producto = []
    Frecuencia_De_Tokens_De_Producto = {}

    for Producto in Datos_De_Productos:
        Nombre_De_Producto = str(Producto.get('name', '')).strip()
        if not Nombre_De_Producto:
            continue

        Nombre_Normalizado = Normalizar_Texto_Base(Nombre_De_Producto)
        Tokens_Relevantes = {
            Token
            for Token in Nombre_Normalizado.replace('-', ' ').split()
            if len(Token) > 2 and Token not in Palabras_Vacias_Entidad_Producto
        }
        if not Tokens_Relevantes:
            continue

        Indice_De_Nombres_De_Producto.append({
            'id': Producto.get('id'),
            'name_norm': Nombre_Normalizado,
            'tokens': Tokens_Relevantes,
        })

        for Token in Tokens_Relevantes:
            Frecuencia_De_Tokens_De_Producto[Token] = Frecuencia_De_Tokens_De_Producto.get(Token, 0) + 1

    Indice_De_Nombres_De_Producto.sort(key=lambda Item_Producto: len(Item_Producto['name_norm']), reverse=True)


def Detectar_Id_De_Producto_En_Texto(Mensaje_Usuario):
    Mensaje_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    if not Mensaje_Normalizado:
        return None

    # Priorizar coincidencia exacta del nombre completo dentro del mensaje.
    for Producto_Indexado in Indice_De_Nombres_De_Producto:
        Nombre_Normalizado = Producto_Indexado['name_norm']
        if len(Nombre_Normalizado) >= 6 and Nombre_Normalizado in Mensaje_Normalizado:
            return Producto_Indexado['id']

    # Soporte para nombres historicos con sufijo tipo S-5.
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

    # Fallback ponderado: permite detectar por menciones parciales o marca/modelo.
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

        # Si hay empate de variantes casi iguales, priorizar cuando hay tokens fuertes (codigo o token unico).
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


def Obtener_Producto_Por_Id(Id_De_Producto):
    return next((Producto for Producto in Datos_De_Productos if Producto.get('id') == Id_De_Producto), None)


def Obtener_Detalle_De_Inventario(Producto):
    Lista_De_Tallas = Producto.get('tallas') if isinstance(Producto.get('tallas'), list) else []
    Texto_De_Tallas = ', '.join(Lista_De_Tallas) if Lista_De_Tallas else 'Unica'
    Texto_De_Genero = Producto.get('genero') or 'Unisex'

    Stock_Producto = Producto.get('stock')
    if isinstance(Stock_Producto, (int, float)):
        Stock_Entero = max(0, int(Stock_Producto))
        Texto_De_Stock = f"{Stock_Entero} unidades"
    else:
        Texto_De_Stock = "No disponible"
        Stock_Entero = None

    return Texto_De_Tallas, Texto_De_Genero, Texto_De_Stock, Stock_Entero


Cambiar_Fuente_De_Catalogo(Fuente_Activa_De_Catalogo)

# ============================================================
# 4. MEMORIA DEL CHAT
# ============================================================
def Cargar_Memoria_Del_Chat_Desde_Disco():
    try:
        with shelve.open(Ruta_Memoria_Del_Chat) as Base_De_Memoria:
            Memoria_Cargada = Base_De_Memoria.get("memoria_chat", {})
            if isinstance(Memoria_Cargada, dict):
                return Memoria_Cargada
    except Exception as exc:
        print(f"[WARN] No se pudo cargar memoria persistente: {exc}")
    return {}


def Guardar_Memoria_Del_Chat_En_Disco():
    try:
        with shelve.open(Ruta_Memoria_Del_Chat) as Base_De_Memoria:
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
    if Fuente_De_Catalogo is not None:
        Memoria_Del_Chat[Id_De_Sesion]["catalog_source"] = Normalizar_Fuente_De_Catalogo(Fuente_De_Catalogo)
        
    if len(Memoria_Del_Chat[Id_De_Sesion]["history"]) > Maximo_Historial_Chat:
        Memoria_Del_Chat[Id_De_Sesion]["history"].pop(0)

    Guardar_Memoria_Del_Chat_En_Disco()

def Obtener_Contexto(Id_De_Sesion):
    return Memoria_Del_Chat.get(Id_De_Sesion, {})


def Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Intent):
    for intent in Datos_De_Intents['intents']:
        if intent['tag'] == Etiqueta_Intent and intent['responses']:
            return random.choice(intent['responses'])
    return None

# ============================================================
# 5. LÓGICA DE RESPUESTA PRINCIPAL
# ============================================================
def Obtener_Respuesta_Principal(Id_De_Sesion, Mensaje_Usuario):
    Etiqueta_Detectada, Confianza_Modelo, Margen_De_Confianza = Predecir_Tag(Mensaje_Usuario)
    Contexto_Actual = Obtener_Contexto(Id_De_Sesion)
    Mensaje_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    Es_Consulta_De_Seguimiento = Es_Consulta_De_Seguimiento_De_Pedido(Mensaje_Usuario)

    Id_De_Producto_Detectado = Detectar_Id_De_Producto_En_Texto(Mensaje_Usuario)
    if Id_De_Producto_Detectado is not None:
        Actualizar_Contexto(Id_De_Sesion, Id_De_Producto=Id_De_Producto_Detectado)
        Contexto_Actual = Obtener_Contexto(Id_De_Sesion)
    
    # Extraer filtros del mensaje antes
    Categoria_Filtro, Color_Filtro, Precio_Maximo_Filtro, Talla_Filtro, Genero_Filtro = Extraer_Filtros(Mensaje_Usuario)
    Palabras_Clave_Detectadas = Extraer_Palabras_Clave_De_Mensaje(Mensaje_Usuario)

    if Debe_Heredar_Filtros_De_Contexto(
        Contexto_Actual,
        Mensaje_Usuario,
        Categoria_Filtro,
        Color_Filtro,
        Precio_Maximo_Filtro,
        Talla_Filtro,
        Genero_Filtro,
    ):
        (
            Categoria_Filtro,
            Color_Filtro,
            Precio_Maximo_Filtro,
            Talla_Filtro,
            Genero_Filtro,
            Palabras_Clave_Detectadas,
        ) = Heredar_Filtros_De_Contexto(
            Contexto_Actual,
            Categoria_Filtro,
            Color_Filtro,
            Precio_Maximo_Filtro,
            Talla_Filtro,
            Genero_Filtro,
            Palabras_Clave_Detectadas,
        )

    Hay_Producto_En_Contexto = bool(Id_De_Producto_Detectado or Contexto_Actual.get("selected_product_id"))
    Etiqueta_Inferida = Inferir_Etiqueta_De_Detalle(
        Mensaje_Usuario,
        Ultima_Etiqueta=Contexto_Actual.get("last_tag"),
        Hay_Producto_En_Contexto=Hay_Producto_En_Contexto,
        Producto_Mencionado_En_Mensaje=Id_De_Producto_Detectado is not None,
    )
    if Etiqueta_Inferida:
        Etiqueta_Detectada = Etiqueta_Inferida

    # Si encontramos un color, precio o categoria específicos pero el modelo dice otra cosa genérica
    # forzamos a que actue como busqueda (Prioridad a la búsqueda real)
    if (Color_Filtro or Precio_Maximo_Filtro or Genero_Filtro) and Etiqueta_Detectada == "saludo":
        Etiqueta_Detectada = "buscar_producto"

    if Etiqueta_Detectada == "colores" and (Precio_Maximo_Filtro or Genero_Filtro) and not Hay_Producto_En_Contexto:
        Etiqueta_Detectada = "buscar_producto"

    if Es_Consulta_De_Seguimiento and Etiqueta_Detectada in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta_Detectada = "pedidos"

    # Respaldo por palabras clave cuando la prediccion del modelo es ambigua.
    Umbral_De_Margen_Actual = Umbral_De_Margen_Por_Tag.get(Etiqueta_Detectada, Umbral_De_Margen_Base)
    Prediccion_Ambigua = (
        Confianza_Modelo < Umbral_De_Confianza
        or Margen_De_Confianza < Umbral_De_Margen_Actual
    )
    if Prediccion_Ambigua and not (Categoria_Filtro or Color_Filtro or Precio_Maximo_Filtro or Talla_Filtro or Genero_Filtro):
        Etiqueta_Detectada = None
        for intent in Datos_De_Intents['intents']:
            for pattern in intent['patterns']:
                if Normalizar_Texto_Base(pattern) in Mensaje_Normalizado:
                    Etiqueta_Detectada = intent['tag']
                    break
            if Etiqueta_Detectada:
                break

    if Es_Consulta_De_Seguimiento and Etiqueta_Detectada in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta_Detectada = "pedidos"

    Accion_De_Filtro = None
    Productos_Encontrados = []
    
    # --- LÓGICA POR TAG ---
    if Etiqueta_Detectada == "buscar_producto":
        Productos_Encontrados = Buscar_Productos(
            Categoria=Categoria_Filtro,
            Color=Color_Filtro,
            Precio_Maximo=Precio_Maximo_Filtro,
            Talla=Talla_Filtro,
            Genero=Genero_Filtro,
            Palabras_Clave=Palabras_Clave_Detectadas,
        )
        if Productos_Encontrados:
            Texto_De_Filtro = ""
            if Color_Filtro: Texto_De_Filtro += f" en color {Color_Filtro}"
            if Categoria_Filtro: Texto_De_Filtro += f" de {Categoria_Filtro}"
            if Talla_Filtro: Texto_De_Filtro += f" talla {Talla_Filtro}"
            if Genero_Filtro: Texto_De_Filtro += f" para {Genero_Filtro.lower()}"
            Respuesta_Final = f"Encontre {len(Productos_Encontrados)} productos{Texto_De_Filtro}. Ya te los muestro en el catalogo, indicame cual te interesa."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }
        else:
            Respuesta_Final = "Lo siento, no encontre productos con esas caracteristicas. Prueba con otro color o categoria."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }
    
    elif Etiqueta_Detectada == "filtrar_categoria":
        if Categoria_Filtro:
            Cantidad_Productos = len([p for p in Datos_De_Productos if p['category'] == Categoria_Filtro])
            Respuesta_Final = f"Listo! Te muestro los {Cantidad_Productos} productos de {Categoria_Filtro}. Revisa el catalogo arriba."
            Accion_De_Filtro = {"category": Categoria_Filtro}
        else:
            Respuesta_Final = "Claro! Que categoria te interesa? Tenemos: Calzado, Polos, Pantalones y Otros."

    elif Etiqueta_Detectada == "filtrar_genero":
        if Genero_Filtro:
            Productos_Filtrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Talla=Talla_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=len(Datos_De_Productos),
            )
            Cantidad_Productos = len(Productos_Filtrados)

            Texto_De_Condicion = f" para {Genero_Filtro.lower()}"
            if Precio_Maximo_Filtro:
                Texto_De_Condicion += f" hasta S/ {Precio_Maximo_Filtro:.2f}"
            if Categoria_Filtro:
                Texto_De_Condicion += f" en {Categoria_Filtro}"

            if Cantidad_Productos > 0:
                Texto_Cantidad = "producto" if Cantidad_Productos == 1 else "productos"
                Respuesta_Final = f"Listo! Te muestro {Cantidad_Productos} {Texto_Cantidad}{Texto_De_Condicion}."
                Accion_De_Filtro = {
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
            else:
                Respuesta_Final = f"No encontre productos{Texto_De_Condicion} con ese termino especifico. Prueba con otra descripcion."
                Accion_De_Filtro = {
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
        else:
            Respuesta_Final = "¿Para qué genero te muestro opciones? Tengo Mujer, Hombre y Unisex."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }
    
    elif Etiqueta_Detectada == "consulta_precio":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Respuesta_Final = f"El {Producto_Seleccionado['name']} cuesta S/ {Producto_Seleccionado['price']:.2f}."
            else:
                Respuesta_Final = "No encuentro el precio de ese producto en específico."
        elif Categoria_Filtro or Color_Filtro or Genero_Filtro:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=3,
            )
            if Productos_Encontrados:
                Respuesta_Final = "Listo, ya te filtre esos productos en el catalogo. Indicame cual te interesa y te doy el precio exacto."
                Accion_De_Filtro = {
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "genero": Genero_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
            else:
                Respuesta_Final = "No encontre productos con esas caracteristicas. Prueba otra busqueda."
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Puedes pedirme precios por categoria o color."

    elif Etiqueta_Detectada == "pedidos":
        if Es_Consulta_De_Seguimiento:
            Respuesta_Final = (
                "Te ayudo con el seguimiento de tu pedido. En esta version aun no consulto tracking en tiempo real. "
                "Si me compartes tu numero de pedido, te indico el estado estimado y los siguientes pasos."
            )
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Para comprar, elige un producto y agrégalo al carrito."
    
    elif Etiqueta_Detectada == "colores":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Colores_Producto = Obtener_Colores_De_Producto(Producto_Seleccionado)
                if Colores_Producto:
                    Respuesta_Final = f"El {Producto_Seleccionado['name']} esta disponible en estos colores: {', '.join(Colores_Producto)}."
                else:
                    Respuesta_Final = f"El {Producto_Seleccionado['name']} no registra colores en la base actual."
            else:
                Respuesta_Final = "No encuentro el producto en contexto para listar sus colores."
        elif Categoria_Filtro:
            Colores_Disponibles = sorted(
                {
                    Color_Item
                    for p in Datos_De_Productos
                    if p['category'] == Categoria_Filtro
                    for Color_Item in Obtener_Colores_De_Producto(p)
                }
            )
            Respuesta_Final = f"En {Categoria_Filtro} tenemos los colores: {', '.join(Colores_Disponibles)}."
        else:
            Respuesta_Final = "Nuestros productos estan disponibles en: Negro, Blanco, Rojo, Azul, Gris y Verde."
    
    elif Etiqueta_Detectada == "disponibilidad":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Texto_De_Tallas, Texto_De_Genero, Texto_De_Stock, Stock_Entero = Obtener_Detalle_De_Inventario(Producto_Seleccionado)
                if Stock_Entero is None or Stock_Entero > 0:
                    Respuesta_Final = (
                        f"Si, tenemos disponible el {Producto_Seleccionado['name']}. "
                        f"Stock: {Texto_De_Stock}. Genero: {Texto_De_Genero}. Tallas: {Texto_De_Tallas}."
                    )
                else:
                    Respuesta_Final = (
                        f"En este momento el {Producto_Seleccionado['name']} no tiene stock disponible. "
                        f"Genero: {Texto_De_Genero}. Tallas registradas: {Texto_De_Tallas}."
                    )
            else:
                Respuesta_Final = "No encuentro el producto en contexto para validar disponibilidad."
        elif Categoria_Filtro or Color_Filtro or Genero_Filtro:
            Coincidencias_De_Stock = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=3,
            )
            if Coincidencias_De_Stock:
                Respuesta_Final = f"Si, tenemos {len(Coincidencias_De_Stock)}+ productos disponibles con ese filtro. Ya te los muestro en el catalogo, indicame cual te interesa."
            else:
                Respuesta_Final = "Actualmente no tenemos stock con esas especificaciones."
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Claro, dime color o categoria para revisar stock."

    # Manejo de contexto para consultar precio de UN producto especifico
    elif Etiqueta_Detectada == "consultar_precio_item":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Respuesta_Final = f"¡Excelente elección! El precio del {Producto_Seleccionado['name']} es de S/ {Producto_Seleccionado['price']:.2f}."
            else:
                Respuesta_Final = "No encuentro el precio de ese producto en específico."
        else:
            Respuesta_Final = "De acuerdo, pero primero dímelo, ¿De qué producto quieres saber el precio?"

    # Manejo de contexto para consultar stock de UN producto especifico
    elif Etiqueta_Detectada == "consultar_stock_item":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Texto_De_Tallas, Texto_De_Genero, Texto_De_Stock, _ = Obtener_Detalle_De_Inventario(Producto_Seleccionado)
                if Talla_Filtro:
                    if 'tallas' in Producto_Seleccionado and Talla_Filtro in Producto_Seleccionado['tallas']:
                        Respuesta_Final = (
                            f"¡Buenas noticias! Si tenemos el {Producto_Seleccionado['name']} en talla {Talla_Filtro}. "
                            f"Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                    elif 'tallas' in Producto_Seleccionado:
                        tallas = ", ".join(Producto_Seleccionado['tallas'])
                        Respuesta_Final = (
                            f"Lo siento, no nos queda en talla {Talla_Filtro}. "
                            f"Lo tenemos en: {tallas}. Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                    else:
                        Respuesta_Final = (
                            f"Este producto es talla unica. Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                else:
                    Respuesta_Final = (
                        f"Claro, el {Producto_Seleccionado['name']} lo tenemos en las siguientes tallas: {Texto_De_Tallas}. "
                        f"Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                    )
            else:
                Respuesta_Final = "No encuentro la información de tallas de ese producto en específico."
        else:
            if Talla_Filtro:
                Productos_Encontrados = Buscar_Productos(Talla=Talla_Filtro, Limite=3)
                if Productos_Encontrados:
                    Respuesta_Final = f"Listo, ya filtre productos en talla {Talla_Filtro}. Revisa el catalogo e indicame cual te interesa."
                    Accion_De_Filtro = {"talla": Talla_Filtro}
                    Etiqueta_Detectada = "buscar_producto"
                else:
                    Respuesta_Final = f"Actualmente no me queda stock en la base de datos para la talla {Talla_Filtro}."
            else:
                Respuesta_Final = "Actualmente no sé por qué producto estás preguntando. ¿Me indicas cuál?"
    
    elif Etiqueta_Detectada:
        Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "No entiendo tu consulta. puedes repetirla?."
    else:
        # Si no se detecto ningun tag, intentar buscar por filtros
        if Categoria_Filtro or Color_Filtro or Genero_Filtro or Palabras_Clave_Detectadas:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
            )
            if Productos_Encontrados:
                Respuesta_Final = "Encontre productos con esos filtros. Ya te los muestro en el catalogo, indicame cual te interesa."
                Accion_De_Filtro = {
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "genero": Genero_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
                Etiqueta_Detectada = "buscar_producto"
            else:
                Respuesta_Final = "No encontre productos con esas caracteristicas."
        elif Id_De_Producto_Detectado is not None:
            Producto_Detectado = Obtener_Producto_Por_Id(Id_De_Producto_Detectado)
            if Producto_Detectado:
                Respuesta_Final = (
                    f"Ya identifique el producto {Producto_Detectado['name']}. "
                    "¿Quieres que te diga precio, colores o stock?"
                )
                Etiqueta_Detectada = "buscar_producto"
            else:
                Respuesta_Final = "No entiendo tu consulta. Puedes preguntarme nuevamente"
        else:
            Respuesta_Final = "No entiendo tu consulta. Puedes preguntarme nuevamente"

    Actualizar_Contexto(Id_De_Sesion, Etiqueta_Detectada, {
        "category": Categoria_Filtro,
        "color": Color_Filtro,
        "max_price": Precio_Maximo_Filtro,
        "talla": Talla_Filtro,
        "genero": Genero_Filtro,
        "keywords": Palabras_Clave_Detectadas,
    })
    
    return Respuesta_Final, Etiqueta_Detectada, Accion_De_Filtro

# ============================================================
# 6. ENDPOINTS
# ============================================================
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "products_active": len(Datos_De_Productos),
        "products_auto": len(Catalogos_De_Productos.get("auto", [])),
        "products_scraped": len(Catalogos_De_Productos.get("scraped", [])),
        "catalog_source_active": Fuente_Activa_De_Catalogo,
        "ai_model": "PyTorch loaded" if Modelo_IA else "Not loaded",
        "tags": Etiquetas_De_Intencion
    })

@app.route('/chat', methods=['POST'])
def chat():
    Datos_Usuario = request.get_json(silent=True) or {}
    mensaje = str(Datos_Usuario.get('message', '')).strip()
    Id_De_Sesion_Actual = str(Datos_Usuario.get('session_id', 'default_user')).strip() or 'default_user'
    Id_De_Producto_En_Contexto = Datos_Usuario.get('context_product_id')
    Contexto_Actual = Obtener_Contexto(Id_De_Sesion_Actual)

    Fuente_Solicitada = Datos_Usuario.get('catalog_source')
    if not Fuente_Solicitada:
        Fuente_Solicitada = Contexto_Actual.get('catalog_source', 'auto')

    Fuente_Usada = Cambiar_Fuente_De_Catalogo(Fuente_Solicitada)
    Actualizar_Contexto(Id_De_Sesion_Actual, Fuente_De_Catalogo=Fuente_Usada)

    if isinstance(Id_De_Producto_En_Contexto, str) and Id_De_Producto_En_Contexto.isdigit():
        Id_De_Producto_En_Contexto = int(Id_De_Producto_En_Contexto)
    
    # Si recibimos un ID de contexto, actualizamos el estado actual del bot
    if Id_De_Producto_En_Contexto is not None:
        Actualizar_Contexto(
            Id_De_Sesion_Actual,
            Id_De_Producto=Id_De_Producto_En_Contexto,
            Fuente_De_Catalogo=Fuente_Usada,
        )
        # Si es el mensaje oculto de inicio de consulta, cortamos aquí
        if mensaje == 'quiero saber mas de este producto':
            product = Obtener_Producto_Por_Id(Id_De_Producto_En_Contexto)
            if product:
                msg = f"¡Excelente elección! Veo que te interesa el {product['name']}. ¿Qué te gustaría saber? (Ej. 'precio' o 'stock')."
            else:
                msg = "Claro, ¿En qué te ayudo con este producto?"
            return jsonify({
                "response": msg,
                "tag": "contexto_iniciado",
                "bot_name": "Asistente SENATI",
                "catalog_source": Fuente_Usada,
            })
        
    if not mensaje:
        return jsonify({"error": "No se recibio mensaje"}), 400

    Respuesta_Bot, Etiqueta_Bot, Accion_De_Filtro = Obtener_Respuesta_Principal(Id_De_Sesion_Actual, mensaje)

    Resultado_Json = {
        "response": Respuesta_Bot,
        "tag": Etiqueta_Bot,
        "bot_name": "Asistente SENATI",
        "catalog_source": Fuente_Usada,
    }

    if Accion_De_Filtro:
        Resultado_Json["filter_action"] = Accion_De_Filtro

    return jsonify(Resultado_Json)


@app.route('/products', methods=['GET'])
def Productos_Endpoint():
    Fuente_Usada = Cambiar_Fuente_De_Catalogo(request.args.get('source', 'auto'))
    return jsonify({
        "products": Datos_De_Productos,
        "count": len(Datos_De_Productos),
        "source": Fuente_Usada,
    })

@app.route('/search', methods=['POST'])
def Buscar_Endpoint():
    """Endpoint para buscar productos filtrados."""
    Datos_De_Consulta = request.get_json(silent=True) or {}
    Fuente_Usada = Cambiar_Fuente_De_Catalogo(
        Datos_De_Consulta.get('catalog_source', request.args.get('source', 'auto'))
    )
    Categoria_Consulta = Datos_De_Consulta.get('category')
    Color_Consulta = Datos_De_Consulta.get('color')
    Genero_Consulta = Datos_De_Consulta.get('genero')
    Palabras_Clave_Consulta = Datos_De_Consulta.get('keywords')

    Precio_Maximo_Consulta = Datos_De_Consulta.get('max_price')
    if Precio_Maximo_Consulta is not None:
        try:
            Precio_Maximo_Consulta = float(Precio_Maximo_Consulta)
        except (TypeError, ValueError):
            Precio_Maximo_Consulta = None

    Limite_Consulta = Datos_De_Consulta.get('limit', Limite_Busqueda_Por_Defecto)
    try:
        Limite_Consulta = int(Limite_Consulta)
    except (TypeError, ValueError):
        Limite_Consulta = Limite_Busqueda_Por_Defecto
    Limite_Consulta = max(1, min(Maximo_Limite_De_Busqueda, Limite_Consulta))
    
    Resultados_De_Busqueda = Buscar_Productos(
        Categoria=Categoria_Consulta,
        Color=Color_Consulta,
        Precio_Maximo=Precio_Maximo_Consulta,
        Genero=Genero_Consulta,
        Palabras_Clave=Palabras_Clave_Consulta,
        Limite=Limite_Consulta,
    )
    return jsonify({
        "products": Resultados_De_Busqueda,
        "count": len(Resultados_De_Busqueda),
        "source": Fuente_Usada,
    })

if __name__ == '__main__':
    server_port = int(os.getenv('SENATI_PORT', '5000'))
    debug_mode = os.getenv('SENATI_DEBUG', 'false').lower() == 'true'
    print(f">>> Servidor SENATI IA listo en http://localhost:{server_port} (debug={debug_mode})")
    app.run(port=server_port, debug=debug_mode)
