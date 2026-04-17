import os
import json
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from utils_nlp import tokenizar_y_lematizar as Tokenizar_Texto
from extractor import Normalizar_Categoria_Producto, Normalizar_Texto_Base, Palabras_Vacias_Entidad_Producto, Extraer_Palabras_Clave_De_Mensaje

Catalogos_De_Productos = {"scraped": []}
Datos_De_Productos = []
Fuente_Activa_De_Catalogo = "scraped"
Colores_Dinamicos = set()
Categorias_Dinamicas = set()
Indice_De_Nombres_De_Producto = []
Frecuencia_De_Tokens_De_Producto = {}
Vectorizador_TFIDF = None
Matriz_TFIDF_Productos = None
Lista_Textos_Productos = []


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
    return "scraped"


def Cambiar_Fuente_De_Catalogo(Fuente_Solicitada):
    global Datos_De_Productos
    global Fuente_Activa_De_Catalogo

    Fuente_Normalizada = Normalizar_Fuente_De_Catalogo(Fuente_Solicitada)
    Lista_De_Productos = Catalogos_De_Productos.get(Fuente_Normalizada, [])

    Cambio_De_Fuente = Fuente_Activa_De_Catalogo != Fuente_Normalizada
    Datos_De_Productos = Lista_De_Productos
    Fuente_Activa_De_Catalogo = Fuente_Normalizada

    if Cambio_De_Fuente or not Indice_De_Nombres_De_Producto:
        Reconstruir_Indice_De_Nombres_De_Producto()

    return Fuente_Activa_De_Catalogo


def Obtener_Colores_De_Producto(Producto):
    Colores_Registrados = Producto.get('colores')
    if isinstance(Colores_Registrados, list) and Colores_Registrados:
        return Colores_Registrados

    Color_Unico = Producto.get('color')
    return [Color_Unico] if Color_Unico else []


def Obtener_Colores_Filtrables_De_Producto(Producto):
    Color_Principal = str(Producto.get('color') or '').strip()
    if Color_Principal:
        return [Color_Principal]

    Colores_Registrados = Producto.get('colores')
    if isinstance(Colores_Registrados, list) and Colores_Registrados:
        Primer_Color = str(Colores_Registrados[0]).strip()
        return [Primer_Color] if Primer_Color else []

    return []


def Extraer_Entidades_Dinamicas():
    global Colores_Dinamicos, Categorias_Dinamicas
    Colores_Dinamicos.clear()
    Categorias_Dinamicas.clear()

    for prod in Datos_De_Productos:
        cat = prod.get("category")
        if cat:
            Categorias_Dinamicas.add(cat)

        colores = Obtener_Colores_De_Producto(prod)
        for col in colores:
            if col:
                Colores_Dinamicos.add(col)


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


def Inicializar_Motor_Semantico():
    global Vectorizador_TFIDF, Matriz_TFIDF_Productos, Lista_Textos_Productos

    if not Datos_De_Productos:
        return

    Lista_Textos_Productos = []
    for prod in Datos_De_Productos:
        texto = f"{prod.get('name', '')} {prod.get('description', '')} {prod.get('category', '')} {prod.get('genero', '')}"
        colores = " ".join(Obtener_Colores_De_Producto(prod))
        tallas = " ".join(prod.get('tallas', [])) if isinstance(prod.get('tallas'), list) else ''
        texto_completo = f"{texto} {colores} {tallas}"

        lemas = Tokenizar_Texto(texto_completo)
        Lista_Textos_Productos.append(" ".join(lemas))

    Vectorizador_TFIDF = TfidfVectorizer()
    Matriz_TFIDF_Productos = Vectorizador_TFIDF.fit_transform(Lista_Textos_Productos)


def Buscar_Productos(Categoria=None, Color=None, Precio_Maximo=None, Talla=None, Genero=None, Palabras_Clave=None, Limite=5):
    try:
        Limite_Seguro = max(1, int(Limite))
    except (TypeError, ValueError):
        Limite_Seguro = 5

    Lista_De_Palabras_Clave = []
    if isinstance(Palabras_Clave, str) and Palabras_Clave.strip():
        Lista_De_Palabras_Clave = Extraer_Palabras_Clave_De_Mensaje(Palabras_Clave)
    elif isinstance(Palabras_Clave, list):
        Lista_De_Palabras_Clave = [str(Palabra).lower() for Palabra in Palabras_Clave if str(Palabra).strip()]

    Indices_Filtrados = list(range(len(Datos_De_Productos)))

    if Categoria:
        Indices_Filtrados = [i for i in Indices_Filtrados if Datos_De_Productos[i]['category'] == Categoria]
    if Color:
        Indices_Filtrados = [i for i in Indices_Filtrados if Color in Obtener_Colores_Filtrables_De_Producto(Datos_De_Productos[i])]
    if Precio_Maximo is not None:
        Indices_Filtrados = [i for i in Indices_Filtrados if Datos_De_Productos[i]['price'] <= Precio_Maximo]
    if Talla:
        Indices_Filtrados = [i for i in Indices_Filtrados if 'tallas' in Datos_De_Productos[i] and Talla in Datos_De_Productos[i]['tallas']]
    if Genero:
        Indices_Filtrados = [i for i in Indices_Filtrados if Datos_De_Productos[i].get('genero') == Genero]

    if not Indices_Filtrados:
        return []

    if Lista_De_Palabras_Clave and Vectorizador_TFIDF is not None:
        Query_Texto = " ".join(Lista_De_Palabras_Clave)
        Query_Lemas = Tokenizar_Texto(Query_Texto)
        Vector_Query = Vectorizador_TFIDF.transform([" ".join(Query_Lemas)])

        Similitudes = cosine_similarity(Vector_Query, Matriz_TFIDF_Productos[Indices_Filtrados]).flatten()
        Indices_Ordenados_Por_Similitud = np.argsort(Similitudes)[::-1]

        Resultados_Ordenados = []
        for idx in Indices_Ordenados_Por_Similitud:
            if Similitudes[idx] > 0.05:
                Resultados_Ordenados.append(Datos_De_Productos[Indices_Filtrados[idx]])

        Resultados = Resultados_Ordenados
    else:
        Resultados = [Datos_De_Productos[i] for i in Indices_Filtrados]
        random.shuffle(Resultados)

    return Resultados[:Limite_Seguro]


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


# Inicialización al cargar el módulo
Catalogos_De_Productos["scraped"] = Cargar_Lista_De_Productos_Desde_Archivo(config.Ruta_Productos_Scrapeados)

if Catalogos_De_Productos["scraped"]:
    print(f"[OK] Inventario scrapeado: {len(Catalogos_De_Productos['scraped'])} productos cargados.")
else:
    print("[WARN] Aun no existe data/products_scraped.json.")

Cambiar_Fuente_De_Catalogo(Fuente_Activa_De_Catalogo)
Extraer_Entidades_Dinamicas()
Inicializar_Motor_Semantico()
