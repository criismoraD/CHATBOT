"""
catalogo.py  ·  Gestión del catálogo de productos
--------------------------------------------------
Fuente de datos: MySQL (config.DB_FUENTE_CATALOGO = "mysql")
Respaldo automático: products_scraped.json si MySQL no está disponible.
Toda la lógica de búsqueda (TF-IDF, léxica, filtros) se mantiene intacta.
"""

import os
import json
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from utils_nlp import tokenizar_y_lematizar as Tokenizar_Texto
from extractor import (
    Normalizar_Categoria_Producto,
    Normalizar_Texto_Base,
    Palabras_Vacias_Entidad_Producto,
    Extraer_Palabras_Clave_De_Mensaje,
)

# ─── Estado global ────────────────────────────────────────────────────────────
Catalogos_De_Productos      = {"scraped": []}
Datos_De_Productos          = []
Fuente_Activa_De_Catalogo   = "scraped"
Colores_Dinamicos           = set()
Categorias_Dinamicas        = set()
Indice_De_Nombres_De_Producto  = []
Frecuencia_De_Tokens_De_Producto = {}
Vectorizador_TFIDF          = None
Matriz_TFIDF_Productos      = None
Lista_Textos_Productos      = []


# ─── Carga desde MySQL ────────────────────────────────────────────────────────

def _fila_mysql_a_producto(fila: dict) -> dict:
    """Convierte una fila de la vista vista_productos_completa al formato interno."""
    colores_str = fila.get("colores") or ""
    tallas_str  = fila.get("tallas")  or ""

    colores = [c.strip() for c in colores_str.split(",") if c.strip()] if colores_str else []
    tallas  = [t.strip() for t in tallas_str.split(",")  if t.strip()] if tallas_str  else []

    return {
        "id"         : fila["id"],
        "name"       : fila["nombre"],
        "price"      : float(fila["precio"]),
        "category"   : fila["categoria"],
        "genero"     : fila.get("genero"),
        "color"      : fila.get("color_principal"),
        "colores"    : colores,
        "tallas"     : tallas,
        "stock"      : int(fila.get("stock") or 0),
        "rating"     : float(fila["rating"]) if fila.get("rating") is not None else None,
        "description": fila.get("descripcion"),
        "image"      : fila.get("imagen_url"),
    }


def Cargar_Productos_Desde_MySQL() -> list:
    """Carga todos los productos desde la vista MySQL."""
    try:
        from db import ejecutar_consulta
        filas = ejecutar_consulta("SELECT * FROM vista_productos_completa ORDER BY id")
        if filas:
            productos = [_fila_mysql_a_producto(f) for f in filas]
            print(f"[OK] MySQL: {len(productos)} productos cargados.")
            return productos
        print("[WARN] MySQL devolvió 0 productos.")
    except Exception as exc:
        print(f"[WARN] No se pudo cargar desde MySQL: {exc}")
    return []


# ─── Carga desde JSON (respaldo) ─────────────────────────────────────────────

def Normalizar_Producto_Cargado(Producto_Original):
    if not isinstance(Producto_Original, dict):
        return None
    Producto_Normalizado = dict(Producto_Original)
    Producto_Normalizado['category'] = Normalizar_Categoria_Producto(
        Producto_Normalizado.get('category'),
        Producto_Normalizado.get('name'),
    )
    return Producto_Normalizado


def Cargar_Lista_De_Productos_Desde_Archivo(Ruta_Archivo):
    if not os.path.exists(Ruta_Archivo):
        return []
    try:
        with open(Ruta_Archivo, 'r', encoding='utf-8') as f:
            lista = json.load(f)
        if isinstance(lista, list):
            return [p for p in (Normalizar_Producto_Cargado(x) for x in lista) if p]
    except Exception as exc:
        print(f"[ERROR] No se pudo cargar {Ruta_Archivo}: {exc}")
    return []


# ─── Cambio de fuente ─────────────────────────────────────────────────────────

def Normalizar_Fuente_De_Catalogo(Fuente_Solicitada):
    return "scraped"


def Cambiar_Fuente_De_Catalogo(Fuente_Solicitada):
    global Datos_De_Productos, Fuente_Activa_De_Catalogo
    Fuente_Normalizada  = Normalizar_Fuente_De_Catalogo(Fuente_Solicitada)
    Lista_De_Productos  = Catalogos_De_Productos.get(Fuente_Normalizada, [])
    Cambio_De_Fuente    = Fuente_Activa_De_Catalogo != Fuente_Normalizada
    Datos_De_Productos  = Lista_De_Productos
    Fuente_Activa_De_Catalogo = Fuente_Normalizada
    if Cambio_De_Fuente or not Indice_De_Nombres_De_Producto:
        Reconstruir_Indice_De_Nombres_De_Producto()
    return Fuente_Activa_De_Catalogo


# ─── Helpers de colores ───────────────────────────────────────────────────────

def Obtener_Colores_De_Producto(Producto):
    colores = Producto.get('colores')
    if isinstance(colores, list) and colores:
        return colores
    color = Producto.get('color')
    return [color] if color else []


def Obtener_Colores_Filtrables_De_Producto(Producto):
    disponibles = set()
    cp = str(Producto.get('color') or '').strip()
    if cp:
        disponibles.add(cp)
    colores = Producto.get('colores')
    if isinstance(colores, list):
        for c in colores:
            if c:
                disponibles.add(str(c).strip())
    return list(disponibles)


# ─── Índice léxico y motor semántico ─────────────────────────────────────────

def Extraer_Entidades_Dinamicas():
    global Colores_Dinamicos, Categorias_Dinamicas
    Colores_Dinamicos.clear()
    Categorias_Dinamicas.clear()
    for prod in Datos_De_Productos:
        cat = prod.get("category")
        if cat:
            Categorias_Dinamicas.add(cat)
        for col in Obtener_Colores_De_Producto(prod):
            if col:
                Colores_Dinamicos.add(col)


def Reconstruir_Indice_De_Nombres_De_Producto():
    global Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto
    Indice_De_Nombres_De_Producto    = []
    Frecuencia_De_Tokens_De_Producto = {}
    for Producto in Datos_De_Productos:
        nombre = str(Producto.get('name', '')).strip()
        if not nombre:
            continue
        nombre_norm = Normalizar_Texto_Base(nombre)
        tokens = {
            t for t in nombre_norm.replace('-', ' ').split()
            if len(t) > 2 and t not in Palabras_Vacias_Entidad_Producto
        }
        if not tokens:
            continue
        Indice_De_Nombres_De_Producto.append({
            'id': Producto.get('id'),
            'name_norm': nombre_norm,
            'tokens': tokens,
        })
        for t in tokens:
            Frecuencia_De_Tokens_De_Producto[t] = Frecuencia_De_Tokens_De_Producto.get(t, 0) + 1
    Indice_De_Nombres_De_Producto.sort(
        key=lambda x: len(x['name_norm']), reverse=True
    )


def Inicializar_Motor_Semantico():
    global Vectorizador_TFIDF, Matriz_TFIDF_Productos, Lista_Textos_Productos
    if not Datos_De_Productos:
        return
    Lista_Textos_Productos = []
    for prod in Datos_De_Productos:
        texto = (
            f"{prod.get('name','')} {prod.get('description','')} "
            f"{prod.get('category','')} {prod.get('genero','')}"
        )
        colores = " ".join(Obtener_Colores_De_Producto(prod))
        tallas  = " ".join(prod.get('tallas', [])) if isinstance(prod.get('tallas'), list) else ''
        lemas   = Tokenizar_Texto(f"{texto} {colores} {tallas}")
        Lista_Textos_Productos.append(" ".join(lemas))
    Vectorizador_TFIDF      = TfidfVectorizer()
    Matriz_TFIDF_Productos  = Vectorizador_TFIDF.fit_transform(Lista_Textos_Productos)


# ─── Búsqueda ─────────────────────────────────────────────────────────────────

def Generar_Variantes_Lexicas_De_Termino(Termino):
    tn = Normalizar_Texto_Base(Termino)
    variantes = {tn}
    if len(tn) > 4 and tn.endswith('es'):
        variantes.add(tn[:-2])
    if len(tn) > 3 and tn.endswith('s'):
        variantes.add(tn[:-1])
    return {v for v in variantes if v}


def Buscar_Productos_Por_Coincidencia_Lexica(Indices_Filtrados, Lista_De_Palabras_Clave):
    if not Lista_De_Palabras_Clave:
        return []
    resultados = []
    for idx in Indices_Filtrados:
        prod = Datos_De_Productos[idx]
        texto = Normalizar_Texto_Base(
            f"{prod.get('name','')} {prod.get('description','')} "
            f"{prod.get('category','')} {prod.get('genero','')} "
            f"{' '.join(Obtener_Colores_De_Producto(prod))} "
            f"{' '.join(prod.get('tallas',[])) if isinstance(prod.get('tallas'), list) else ''}"
        )
        hits = sum(
            1 for kw in Lista_De_Palabras_Clave
            if any(v in texto for v in Generar_Variantes_Lexicas_De_Termino(kw))
        )
        if hits > 0:
            resultados.append((hits, prod))
    resultados.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in resultados]


def Buscar_Productos(Categoria=None, Color=None, Precio_Maximo=None, Talla=None,
                     Genero=None, Palabras_Clave=None, Limite=5):
    try:
        limite = max(1, int(Limite))
    except (TypeError, ValueError):
        limite = 5

    # Construir lista de palabras clave
    kws = []
    if isinstance(Palabras_Clave, str) and Palabras_Clave.strip():
        kws = Extraer_Palabras_Clave_De_Mensaje(Palabras_Clave)
    elif isinstance(Palabras_Clave, list):
        kws = [Normalizar_Texto_Base(p) for p in Palabras_Clave
               if isinstance(p, str) and Normalizar_Texto_Base(p)]

    indices = list(range(len(Datos_De_Productos)))

    if Categoria:
        indices = [i for i in indices if Datos_De_Productos[i]['category'] == Categoria]
    if Color:
        indices = [i for i in indices if Color in Obtener_Colores_Filtrables_De_Producto(Datos_De_Productos[i])]
    if Precio_Maximo is not None:
        indices = [i for i in indices if Datos_De_Productos[i]['price'] <= Precio_Maximo]
    if Talla:
        indices = [i for i in indices
                   if 'tallas' in Datos_De_Productos[i] and Talla in Datos_De_Productos[i]['tallas']]
    if Genero:
        indices = [i for i in indices if Datos_De_Productos[i].get('genero') == Genero]

    if not indices:
        return []

    if kws and Vectorizador_TFIDF is not None:
        vec   = Vectorizador_TFIDF.transform([" ".join(Tokenizar_Texto(" ".join(kws)))])
        sims  = cosine_similarity(vec, Matriz_TFIDF_Productos[indices]).flatten()
        orden = np.argsort(sims)[::-1]
        res   = [Datos_De_Productos[indices[i]] for i in orden if sims[i] > 0.03]
        if not res:
            res = Buscar_Productos_Por_Coincidencia_Lexica(indices, kws)
    elif kws:
        res = Buscar_Productos_Por_Coincidencia_Lexica(indices, kws)
    else:
        res = [Datos_De_Productos[i] for i in indices]
        random.shuffle(res)

    return res[:limite]


def Obtener_Producto_Por_Id(Id_De_Producto):
    return next((p for p in Datos_De_Productos if p.get('id') == Id_De_Producto), None)


def Obtener_Detalle_De_Inventario(Producto):
    tallas  = Producto.get('tallas') if isinstance(Producto.get('tallas'), list) else []
    txt_tallas  = ', '.join(tallas) if tallas else 'Unica'
    txt_genero  = Producto.get('genero') or 'Unisex'
    stock = Producto.get('stock')
    if isinstance(stock, (int, float)):
        stock_int  = max(0, int(stock))
        txt_stock  = f"{stock_int} unidades"
    else:
        txt_stock  = "No disponible"
        stock_int  = None
    return txt_tallas, txt_genero, txt_stock, stock_int


# ─── Inicialización al importar ───────────────────────────────────────────────

def _inicializar():
    """Intenta cargar desde MySQL; si falla, usa el JSON como respaldo."""
    productos = []

    if getattr(config, 'DB_FUENTE_CATALOGO', 'json') == 'mysql':
        productos = Cargar_Productos_Desde_MySQL()

    if not productos:
        print("[INFO] Usando respaldo JSON...")
        productos = Cargar_Lista_De_Productos_Desde_Archivo(config.Ruta_Productos_Scrapeados)
        if productos:
            print(f"[OK] JSON: {len(productos)} productos cargados.")
        else:
            print("[WARN] Sin productos disponibles.")

    Catalogos_De_Productos["scraped"] = productos
    Cambiar_Fuente_De_Catalogo(Fuente_Activa_De_Catalogo)
    Extraer_Entidades_Dinamicas()
    Inicializar_Motor_Semantico()


_inicializar()
