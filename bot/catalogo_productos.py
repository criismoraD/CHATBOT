"""
bot/catalogo.py  ·  Catálogo de Productos
------------------------------------------
Gestiona la carga, indexación y búsqueda de productos.
Soporta búsqueda semántica (TF-IDF) y coincidencia léxica.
"""

import os
import json
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core import config
from core import db
from core.procesamiento_lenguaje import Tokenizar_Y_Lematizar
from bot.extractor_entidades import (
    Normalizar_Categoria_Producto, Normalizar_Texto_Base,
    Palabras_Vacias_Entidad_Producto, Extraer_Palabras_Clave_De_Mensaje
)


# ─── Estado Global del Catálogo ──────────────────────────────────────────────

Catalogos_De_Productos = {"scraped": []}
Datos_De_Productos = []
Fuente_Activa_De_Catalogo = "scraped"

_Colores_Dinamicos = set()
Categorias_Dinamicas = set()
Indice_De_Nombres_De_Producto = []
Diccionario_Productos_Por_Id = {}
_Diccionario_Colores_Por_Categoria = {}
Frecuencia_De_Tokens_De_Producto = {}

_Vectorizador_TFIDF = None
_Matriz_TFIDF_Productos = None
_Lista_Textos_Productos = []


# ─── Normalización de Productos ──────────────────────────────────────────────

def _Normalizar_Producto(Producto_Original):
    """Normaliza un producto individual (categoría desde nombre)."""
    if not isinstance(Producto_Original, dict):
        return None

    Producto = dict(Producto_Original)
    Producto['category'] = Normalizar_Categoria_Producto(
        Producto.get('category'),
        Producto.get('name'),
    )
    return Producto


# ─── Carga desde Base de Datos ───────────────────────────────────────────────

def _Cargar_Productos_Desde_BD():
    """Carga todos los productos desde la vista MySQL y los normaliza."""
    try:
        Filas = db.Ejecutar_Consulta("SELECT * FROM vista_productos_completa")
        if not Filas:
            return []

        Lista_Normalizada = []
        for Fila in Filas:
            # Parsear colores
            Colores_Str = Fila.get("colores")
            if Colores_Str:
                Colores = [c.strip() for c in str(Colores_Str).split(',') if c.strip()]
            else:
                Colores = []

            Color_Principal = Fila.get("color_principal") or (Colores[0] if Colores else "")

            # Parsear tallas
            Tallas_Str = Fila.get("tallas")
            if Tallas_Str:
                Tallas = [t.strip() for t in str(Tallas_Str).split(',') if t.strip()]
            else:
                Tallas = []

            Producto = {
                "id": Fila.get("id"),
                "name": Fila.get("nombre"),
                "price": float(Fila.get("precio")) if Fila.get("precio") is not None else 0.0,
                "category": Fila.get("categoria"),
                "genero": Fila.get("genero"),
                "color": Color_Principal,
                "colores": Colores,
                "tallas": Tallas,
                "stock": Fila.get("stock"),
                "rating": float(Fila.get("rating")) if Fila.get("rating") is not None else 0.0,
                "description": Fila.get("descripcion") or "",
                "image": Fila.get("imagen_url") or ""
            }

            Producto_Normalizado = _Normalizar_Producto(Producto)
            if Producto_Normalizado is not None:
                Lista_Normalizada.append(Producto_Normalizado)

        return Lista_Normalizada
    except Exception as Error:
        print(f"[ERROR DB] No se pudo cargar catálogo desde MySQL: {Error}")
        return []


# ─── Gestión de Fuente de Catálogo ───────────────────────────────────────────

def Normalizar_Fuente_De_Catalogo(Fuente_Solicitada):
    """Normaliza la fuente del catálogo (actualmente solo 'scraped')."""
    return "scraped"


def Cambiar_Fuente_De_Catalogo(Fuente_Solicitada):
    """Cambia la fuente activa del catálogo y reconstruye índices si es necesario."""
    global Datos_De_Productos, Fuente_Activa_De_Catalogo

    Fuente_Normalizada = Normalizar_Fuente_De_Catalogo(Fuente_Solicitada)
    Lista_De_Productos = Catalogos_De_Productos.get(Fuente_Normalizada, [])

    Cambio = Fuente_Activa_De_Catalogo != Fuente_Normalizada
    Datos_De_Productos = Lista_De_Productos
    Fuente_Activa_De_Catalogo = Fuente_Normalizada

    if Cambio or not Indice_De_Nombres_De_Producto:
        Reconstruir_Indice_De_Nombres()
        Reconstruir_Diccionario_De_Productos()
        Reconstruir_Diccionario_De_Colores()

    return Fuente_Activa_De_Catalogo


# ─── Helpers de Colores ──────────────────────────────────────────────────────

def Obtener_Colores_De_Producto(Producto):
    """Retorna la lista de colores de un producto."""
    Colores = Producto.get('colores')
    if isinstance(Colores, list) and Colores:
        return Colores
    Color_Unico = Producto.get('color')
    return [Color_Unico] if Color_Unico else []


def _Obtener_Colores_Filtrables(Producto):
    """Retorna el set de colores disponibles para filtrar (principal + adicionales)."""
    Colores = set()
    Principal = str(Producto.get('color') or '').strip()
    if Principal:
        Colores.add(Principal)
    for c in (Producto.get('colores') or []):
        if c:
            Colores.add(str(c).strip())
    return list(Colores)


# ─── Extracción de Entidades Dinámicas ───────────────────────────────────────

def Extraer_Entidades_Dinamicas():
    """Escanea todos los productos para extraer colores y categorías únicas."""
    global _Colores_Dinamicos, Categorias_Dinamicas
    _Colores_Dinamicos.clear()
    Categorias_Dinamicas.clear()

    for Producto in Datos_De_Productos:
        Cat = Producto.get("category")
        if Cat:
            Categorias_Dinamicas.add(Cat)
        for Color in Obtener_Colores_De_Producto(Producto):
            if Color:
                _Colores_Dinamicos.add(Color)


# ─── Reconstrucción de Índices ───────────────────────────────────────────────

def Reconstruir_Diccionario_De_Productos():
    """Reconstruye el diccionario id → producto."""
    global Diccionario_Productos_Por_Id
    Diccionario_Productos_Por_Id = {}
    for Producto in Datos_De_Productos:
        Id = Producto.get('id')
        if Id is not None and Id not in Diccionario_Productos_Por_Id:
            Diccionario_Productos_Por_Id[Id] = Producto


def Reconstruir_Diccionario_De_Colores():
    """Reconstruye el mapeo categoría → lista de colores disponibles."""
    global _Diccionario_Colores_Por_Categoria
    _Diccionario_Colores_Por_Categoria = {}
    for Producto in Datos_De_Productos:
        Cat = Producto.get('category')
        if Cat:
            if Cat not in _Diccionario_Colores_Por_Categoria:
                _Diccionario_Colores_Por_Categoria[Cat] = set()
            for Color in Obtener_Colores_De_Producto(Producto):
                _Diccionario_Colores_Por_Categoria[Cat].add(Color)
    for Cat in _Diccionario_Colores_Por_Categoria:
        _Diccionario_Colores_Por_Categoria[Cat] = sorted(list(_Diccionario_Colores_Por_Categoria[Cat]))


def Reconstruir_Indice_De_Nombres():
    """Reconstruye el índice de nombres de productos para detección por texto."""
    global Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto
    Indice_De_Nombres_De_Producto = []
    Frecuencia_De_Tokens_De_Producto = {}

    for Producto in Datos_De_Productos:
        Nombre = str(Producto.get('name', '')).strip()
        if not Nombre:
            continue

        Nombre_Normalizado = Normalizar_Texto_Base(Nombre)
        Tokens = {
            T for T in Nombre_Normalizado.replace('-', ' ').split()
            if len(T) > 2 and T not in Palabras_Vacias_Entidad_Producto
        }
        if not Tokens:
            continue

        Indice_De_Nombres_De_Producto.append({
            'id': Producto.get('id'),
            'name_norm': Nombre_Normalizado,
            'tokens': Tokens,
        })

        for Token in Tokens:
            Frecuencia_De_Tokens_De_Producto[Token] = Frecuencia_De_Tokens_De_Producto.get(Token, 0) + 1

    Indice_De_Nombres_De_Producto.sort(key=lambda x: len(x['name_norm']), reverse=True)


# ─── Motor Semántico (TF-IDF) ───────────────────────────────────────────────

def Inicializar_Motor_Semantico():
    """Construye la matriz TF-IDF sobre las descripciones de productos."""
    global _Vectorizador_TFIDF, _Matriz_TFIDF_Productos, _Lista_Textos_Productos

    if not Datos_De_Productos:
        return

    _Lista_Textos_Productos = []
    for Producto in Datos_De_Productos:
        Texto = (
            f"{Producto.get('name', '')} {Producto.get('description', '')} "
            f"{Producto.get('category', '')} {Producto.get('genero', '')}"
        )
        Colores = " ".join(Obtener_Colores_De_Producto(Producto))
        Tallas = " ".join(Producto.get('tallas', [])) if isinstance(Producto.get('tallas'), list) else ''
        Texto_Completo = f"{Texto} {Colores} {Tallas}"

        Lemas = Tokenizar_Y_Lematizar(Texto_Completo)
        _Lista_Textos_Productos.append(" ".join(Lemas))

    _Vectorizador_TFIDF = TfidfVectorizer()
    _Matriz_TFIDF_Productos = _Vectorizador_TFIDF.fit_transform(_Lista_Textos_Productos)


# ─── Búsqueda Léxica ─────────────────────────────────────────────────────────

def _Generar_Variantes_Lexicas(Termino):
    """Genera variantes de un término (singular/plural + sinónimos)."""
    Normalizado = Normalizar_Texto_Base(Termino)
    Variantes = {Normalizado}
    if len(Normalizado) > 4 and Normalizado.endswith('es'):
        Variantes.add(Normalizado[:-2])
    if len(Normalizado) > 3 and Normalizado.endswith('s'):
        Variantes.add(Normalizado[:-1])

    Sinonimos = {
        'pantalon': ['leggin', 'legging', 'jogger', 'buzo'],
        'pantalones': ['leggins', 'leggings', 'joggers', 'buzos'],
        'zapatilla': ['calzado', 'zapato', 'tenis'],
        'zapatillas': ['calzados', 'zapatos', 'tenis'],
    }
    for v in list(Variantes):
        if v in Sinonimos:
            Variantes.update(Sinonimos[v])

    return {v for v in Variantes if v}


def _Buscar_Por_Coincidencia_Lexica(Indices, Palabras_Clave):
    """Búsqueda de respaldo usando coincidencia léxica exacta."""
    if not Palabras_Clave:
        return []

    Resultados = []
    for Indice in Indices:
        Producto = Datos_De_Productos[Indice]
        Texto = Normalizar_Texto_Base(
            f"{Producto.get('name', '')} {Producto.get('description', '')} "
            f"{Producto.get('genero', '')} "
            f"{' '.join(Obtener_Colores_De_Producto(Producto))} "
            f"{' '.join(Producto.get('tallas', [])) if isinstance(Producto.get('tallas'), list) else ''}"
        )
        Coincidencias = sum(
            1 for P in Palabras_Clave
            if any(V in Texto for V in _Generar_Variantes_Lexicas(P))
        )
        if Coincidencias > 0:
            Resultados.append((Coincidencias, Producto))

    Resultados.sort(key=lambda x: x[0], reverse=True)
    return [P for _, P in Resultados]


# ─── Búsqueda Principal ─────────────────────────────────────────────────────

def Buscar_Productos(
    Categoria=None,
    Color=None,
    Precio_Maximo=None,
    Talla=None,
    Genero=None,
    Palabras_Clave=None,
    Limite=5,
):
    """
    Busca productos aplicando filtros y búsqueda semántica/ léxica.
    Retorna hasta `Limite` productos ordenados por relevancia.
    """
    try:
        Limite_Seguro = max(1, int(Limite))
    except (TypeError, ValueError):
        Limite_Seguro = 5

    # Preparar palabras clave
    Lista_Palabras = []
    if isinstance(Palabras_Clave, str) and Palabras_Clave.strip():
        Lista_Palabras = Extraer_Palabras_Clave_De_Mensaje(Palabras_Clave)
    elif isinstance(Palabras_Clave, list):
        Lista_Palabras = [
            Normalizar_Texto_Base(P) for P in Palabras_Clave
            if isinstance(P, str) and Normalizar_Texto_Base(P)
        ]

    # Aplicar filtros
    Indices = list(range(len(Datos_De_Productos)))
    if Categoria:
        Indices = [i for i in Indices if Datos_De_Productos[i]['category'] == Categoria]
    if Color:
        Indices = [i for i in Indices if Color in _Obtener_Colores_Filtrables(Datos_De_Productos[i])]
    if Precio_Maximo is not None:
        Indices = [i for i in Indices if Datos_De_Productos[i]['price'] <= Precio_Maximo]
    if Talla:
        Indices = [i for i in Indices if 'tallas' in Datos_De_Productos[i] and Talla in Datos_De_Productos[i]['tallas']]
    if Genero:
        Indices = [i for i in Indices if Datos_De_Productos[i].get('genero') == Genero]

    if not Indices:
        return []

    # Búsqueda semántica (TF-IDF) o léxica
    if Lista_Palabras and _Vectorizador_TFIDF is not None:
        Query_Lemas = Tokenizar_Y_Lematizar(" ".join(Lista_Palabras))
        Vector_Query = _Vectorizador_TFIDF.transform([" ".join(Query_Lemas)])
        Similitudes = cosine_similarity(Vector_Query, _Matriz_TFIDF_Productos[Indices]).flatten()
        Orden = np.argsort(Similitudes)[::-1]

        Resultados = [Datos_De_Productos[Indices[i]] for i in Orden if Similitudes[i] > 0.03]
        if not Resultados:
            Resultados = _Buscar_Por_Coincidencia_Lexica(Indices, Lista_Palabras)
    elif Lista_Palabras:
        Resultados = _Buscar_Por_Coincidencia_Lexica(Indices, Lista_Palabras)
    else:
        Resultados = [Datos_De_Productos[i] for i in Indices]
        random.shuffle(Resultados)

    return Resultados[:Limite_Seguro]


# ─── Consultas Directas ─────────────────────────────────────────────────────

def Obtener_Producto_Por_Id(Id_De_Producto):
    """Retorna un producto por su ID o None."""
    return Diccionario_Productos_Por_Id.get(Id_De_Producto)


def Obtener_Detalle_De_Inventario(Producto):
    """Retorna (tallas, género, stock_texto, stock_entero) de un producto."""
    Tallas = Producto.get('tallas') if isinstance(Producto.get('tallas'), list) else []
    Texto_Tallas = ', '.join(Tallas) if Tallas else 'Unica'
    Texto_Genero = Producto.get('genero') or 'Unisex'

    Stock = Producto.get('stock')
    if isinstance(Stock, (int, float)):
        Stock_Entero = max(0, int(Stock))
        Texto_Stock = f"{Stock_Entero} unidades"
    else:
        Texto_Stock = "No disponible"
        Stock_Entero = None

    return Texto_Tallas, Texto_Genero, Texto_Stock, Stock_Entero


def Decrementar_Stock_En_Cache(Id_Producto, Cantidad):
    """Reduce el stock en memoria tras una compra."""
    for Producto in Datos_De_Productos:
        if Producto.get('id') == Id_Producto:
            Stock_Actual = Producto.get('stock')
            if isinstance(Stock_Actual, (int, float)):
                Producto['stock'] = max(0, int(Stock_Actual) - Cantidad)
            break


def Obtener_Colores_Por_Categoria():
    """Retorna el diccionario de colores agrupados por categoría."""
    return _Diccionario_Colores_Por_Categoria


def Obtener_Colores_Dinamicos():
    """Retorna el set de colores detectados en el catálogo."""
    return _Colores_Dinamicos


# ─── Inicialización al Importar ──────────────────────────────────────────────

Catalogos_De_Productos["scraped"] = _Cargar_Productos_Desde_BD()

if Catalogos_De_Productos["scraped"]:
    print(f"[OK] Inventario MySQL: {len(Catalogos_De_Productos['scraped'])} productos cargados.")
else:
    print("[WARN] Aun no hay productos en MySQL (vista_productos_completa).")

Cambiar_Fuente_De_Catalogo(Fuente_Activa_De_Catalogo)
Extraer_Entidades_Dinamicas()
Inicializar_Motor_Semantico()
