"""
Scraper de catalogo para SENATI SPORTS.

Ejemplo de uso:
python scrape_products.py \
  --url "https://tienda-ejemplo.com/catalogo" \
  --selector-producto ".product-card" \
  --selector-nombre ".product-title" \
  --selector-imagen "img" \
  --selector-categoria ".product-category" \
  --limite 120

Genera por defecto: data/products_scraped.json
"""

import argparse
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from Utils_Inventario import (
    Calificacion_Maxima,
    Calificacion_Minima,
    Categorias_De_Producto,
    Colores_Disponibles,
    Elegir_Colores_Disponibles,
    Elegir_Tallas_Disponibles,
    Imprimir_Resumen,
    Stock_Maximo,
    Stock_Minimo,
)

Ruta_Salida_Por_Defecto = Path("data/products_scraped.json")
Ruta_Carpeta_Imagenes_Por_Defecto = Path("data/product_images_scraped")
Timeout_Por_Defecto = 20

Cabeceras_Http = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://irun.pe/",
    "Connection": "keep-alive"
}
Mapa_De_Categoria_Por_Keyword = {
    "zapat": "CALZADO",
    "zapato": "CALZADO",
    "botin": "CALZADO",
    "bota": "CALZADO",
    "sneaker": "CALZADO",
    "shoe": "CALZADO",
    "polo": "POLOS",
    "camis": "POLOS",
    "jersey": "POLOS",
    "shirt": "POLOS",
    "top": "POLOS",
    "pantal": "PANTALONES",
    "short": "PANTALONES",
    "jogger": "PANTALONES",
    "legging": "PANTALONES",
    "trouser": "PANTALONES",
    "medias": "OTROS",
    "calcetin": "OTROS",
    "sock": "OTROS",
    "acces": "OTROS",
    "gorra": "OTROS",
    "mochila": "OTROS",
    "guante": "OTROS",
    "botella": "OTROS",
    "tomatodo": "OTROS",
}

Urls_Irun_Por_Defecto = [
    # Mujer
    "https://irun.pe/catalogo/mujer/",
    "https://irun.pe/catalogo/zapatillas-mujer/",
    "https://irun.pe/catalogo/zapatillas-urbanas-para-mujer/",
    "https://irun.pe/catalogo/zapatillas-outdoor-para-mujer/",
    "https://irun.pe/catalogo/zapatillas-running-para-mujer/",
    "https://irun.pe/catalogo/zapatillas-training-para-mujer/",
    "https://irun.pe/catalogo/textil-ropa-deportiva-de-mujeres/",
    "https://irun.pe/catalogo/textil-casacas-deportivas-para-mujer/",
    "https://irun.pe/catalogo/textil-conjuntos-deportivos-para-mujer/",
    "https://irun.pe/catalogo/textil-pantalones-y-leggins-deportivos-para-mujer/",
    "https://irun.pe/catalogo/textil-polos-deportivos-para-mujer/",
    "https://irun.pe/catalogo/textil-shorts-deportivos-para-mujer/",
    "https://irun.pe/catalogo/textil-tops-deportivos-para-mujer/",
    # Hombre
    "https://irun.pe/catalogo/hombre/",
    "https://irun.pe/catalogo/zapatillas-hombre/",
    "https://irun.pe/catalogo/zapatillas-de-basquet/",
    "https://irun.pe/catalogo/zapatillas-de-futbol-para-hombre/",
    "https://irun.pe/catalogo/zapatillas-urbanas-para-hombre/",
    "https://irun.pe/catalogo/zapatillas-outdoor-para-hombre/",
    "https://irun.pe/catalogo/zapatillas-running-para-hombre/",
    "https://irun.pe/catalogo/zapatillas-training-para-hombre/",
    "https://irun.pe/catalogo/textil-ropa-deportiva-de-hombres/",
    "https://irun.pe/catalogo/textil-camiseta-deportiva-para-hombre/",
    "https://irun.pe/catalogo/textil-casaca-deportiva-para-hombre/",
    "https://irun.pe/catalogo/textil-conjuntos-deportivos/",
    "https://irun.pe/catalogo/textil-pantalones-y-joggers-deportivos-para-hombre/",
    "https://irun.pe/catalogo/polos-urbano/",
    "https://irun.pe/catalogo/textil-shorts-deportivos-para-hombre/",
    # Juvenil
    "https://irun.pe/catalogo/juvenil/",
    "https://irun.pe/catalogo/zapatillas-juvenil/",
    "https://irun.pe/catalogo/zapatillas-de-futbol-juvenil/",
    "https://irun.pe/catalogo/zapatillas-urbanas-juvenil/",
    "https://irun.pe/catalogo/zapatillas-outdoor-juvenil/",
    "https://irun.pe/catalogo/zapatillas-running-juvenil/",
    "https://irun.pe/catalogo/zapatillas-training-juvenil/",
    # Ninos
    "https://irun.pe/catalogo/ninos/",
    "https://irun.pe/catalogo/zapatillas-ninos/",
    "https://irun.pe/catalogo/zapatillas-de-futbol-para-ninos/",
    "https://irun.pe/catalogo/zapatillas-urbanas-bebe/",
    "https://irun.pe/catalogo/zapatillas-urbanas-ninos/",
    # Textil y accesorios
    "https://irun.pe/catalogo/textil/",
    "https://irun.pe/catalogo/accesorios-deportivos/",
    "https://irun.pe/catalogo/accesorios-deportivos-canguros/",
    "https://irun.pe/catalogo/accesorios-deportivos-maletines-deportivos/",
    "https://irun.pe/catalogo/accesorios-deportivos-mochilas/",
]


def Normalizar_Texto(Texto_Entrada):
    Texto_En_Minusculas = str(Texto_Entrada or "").lower().strip()
    Texto_Sin_Tildes = unicodedata.normalize("NFKD", Texto_En_Minusculas)
    Texto_Sin_Tildes = "".join(
        Caracter for Caracter in Texto_Sin_Tildes if not unicodedata.combining(Caracter)
    )
    return re.sub(r"\s+", " ", Texto_Sin_Tildes).strip()


def Inferir_Categoria_Estandar(Categoria_Original, Nombre_Producto, Categoria_Por_Defecto=None):
    Categoria_Normalizada = str(Categoria_Original or "").strip().upper()
    if Categoria_Normalizada in Categorias_De_Producto:
        return Categoria_Normalizada

    Candidatos_De_Texto = [
        Normalizar_Texto(Categoria_Original),
        Normalizar_Texto(Nombre_Producto),
    ]

    for Texto_Candidato in Candidatos_De_Texto:
        for Keyword, Categoria in Mapa_De_Categoria_Por_Keyword.items():
            if Keyword in Texto_Candidato:
                return Categoria

    return Categoria_Por_Defecto if Categoria_Por_Defecto in Categorias_De_Producto else "OTROS"


def Inferir_Genero_Desde_Nombre(Nombre_Producto):
    Texto_Normalizado = Normalizar_Texto(Nombre_Producto)

    Tiene_Hombre = bool(re.search(r"\bhombre(?:s)?\b", Texto_Normalizado))
    Tiene_Mujer = bool(re.search(r"\bmujer(?:es)?\b", Texto_Normalizado))

    if Tiene_Hombre and not Tiene_Mujer:
        return "Hombre"
    if Tiene_Mujer and not Tiene_Hombre:
        return "Mujer"
    return "Unisex"


def Extraer_Texto_Selector(Contenedor, Selector_Css, Selectores_Alternos=None):
    Lista_De_Selectores = []
    if Selector_Css:
        Lista_De_Selectores.append(Selector_Css)
    if isinstance(Selectores_Alternos, list):
        Lista_De_Selectores.extend(Selectores_Alternos)

    for Selector_Actual in Lista_De_Selectores:
        Nodo = Contenedor.select_one(Selector_Actual)
        if not Nodo:
            continue

        Texto = Nodo.get_text(" ", strip=True)
        if Texto:
            return Texto

    return ""


def Extraer_Url_Imagen(Contenedor, Selector_Css_Imagen, Url_Base):
    Nodo_Imagen = None

    if Selector_Css_Imagen:
        Nodo_Imagen = Contenedor.select_one(Selector_Css_Imagen)
    if not Nodo_Imagen:
        Nodo_Imagen = Contenedor.find("img")
    if not Nodo_Imagen:
        return None

    Atributos_Prioritarios = [
        "src",
        "data-src",
        "data-original",
        "data-lazy-src",
        "srcset",
        "data-srcset",
    ]

    for Atributo in Atributos_Prioritarios:
        Valor = (Nodo_Imagen.get(Atributo) or "").strip()
        if not Valor:
            continue

        if "srcset" in Atributo:
            Valor = Valor.split(",")[0].strip().split(" ")[0]

        if not Valor or Valor.startswith("data:"):
            continue

        return urljoin(Url_Base, Valor)

    return None


def Sanear_Texto_Archivo(Texto_Entrada):
    Texto = Normalizar_Texto(Texto_Entrada)
    Texto = re.sub(r"[^a-z0-9]+", "-", Texto)
    return Texto.strip("-") or "producto"


def Obtener_Extension_De_Imagen(Url_Imagen, Tipo_De_Contenido):
    Path_Url = Path(urlparse(Url_Imagen).path)
    Extension = Path_Url.suffix.lower()

    Extensiones_Permitidas = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if Extension in Extensiones_Permitidas:
        return Extension

    if "png" in (Tipo_De_Contenido or ""):
        return ".png"
    if "webp" in (Tipo_De_Contenido or ""):
        return ".webp"
    if "gif" in (Tipo_De_Contenido or ""):
        return ".gif"

    return ".jpg"


def Descargar_Imagen(Url_Imagen, Nombre_Producto, Ruta_Carpeta_Imagenes, Sesion_Http, Timeout_Request):
    try:
        Respuesta = Sesion_Http.get(Url_Imagen, timeout=Timeout_Request)
        Respuesta.raise_for_status()
    except requests.RequestException:
        return Url_Imagen

    Tipo_De_Contenido = (Respuesta.headers.get("Content-Type") or "").lower()
    if "image" not in Tipo_De_Contenido:
        return Url_Imagen

    Ruta_Carpeta_Imagenes.mkdir(parents=True, exist_ok=True)

    Hash_Corto = hashlib.sha1(Url_Imagen.encode("utf-8")).hexdigest()[:10]
    Nombre_Base = Sanear_Texto_Archivo(Nombre_Producto)
    Extension = Obtener_Extension_De_Imagen(Url_Imagen, Tipo_De_Contenido)
    Nombre_Archivo = f"{Nombre_Base}-{Hash_Corto}{Extension}"
    Ruta_Destino = Ruta_Carpeta_Imagenes / Nombre_Archivo

    if not Ruta_Destino.exists():
        Ruta_Destino.write_bytes(Respuesta.content)

    return Ruta_Destino.as_posix()


def Asegurar_Nombre_Unico(Nombre_Producto, Nombres_Registrados):
    Nombre_Base = str(Nombre_Producto or "").strip()
    if not Nombre_Base:
        Nombre_Base = "Producto sin nombre"

    if Nombre_Base not in Nombres_Registrados:
        Nombres_Registrados.add(Nombre_Base)
        return Nombre_Base

    Contador = 2
    while True:
        Nombre_Alterno = f"{Nombre_Base} ({Contador})"
        if Nombre_Alterno not in Nombres_Registrados:
            Nombres_Registrados.add(Nombre_Alterno)
            return Nombre_Alterno
        Contador += 1


def Construir_Producto_Estandar(
    Id_De_Producto,
    Nombre_Producto,
    Categoria_Original,
    Url_Imagen,
    Categoria_Por_Defecto,
    Descargar_Imagenes,
    Ruta_Carpeta_Imagenes,
    Sesion_Http,
    Timeout_Request,
):
    Categoria_Estandar = Inferir_Categoria_Estandar(
        Categoria_Original,
        Nombre_Producto,
        Categoria_Por_Defecto=Categoria_Por_Defecto,
    )
    Configuracion = Categorias_De_Producto[Categoria_Estandar]

    Colores_Del_Producto = Elegir_Colores_Disponibles(Colores_Disponibles)
    Color_Principal = Colores_Del_Producto[0]
    Tallas_Disponibles = Elegir_Tallas_Disponibles(Configuracion["tallas"])

    # Se usa un precio base por defecto ya que el rango se elimino de las utilidades
    Precio_Actual = round(random.uniform(50.0, 200.0), 2)

    Genero_Del_Producto = Inferir_Genero_Desde_Nombre(Nombre_Producto)
    Stock_Actual = random.randint(Stock_Minimo, Stock_Maximo)
    Calificacion_Actual = round(random.uniform(Calificacion_Minima, Calificacion_Maxima), 1)
    Descripcion_Actual = random.choice(Configuracion["descriptions"])

    Imagen_Final = Url_Imagen
    if Descargar_Imagenes and Url_Imagen:
        Imagen_Final = Descargar_Imagen(
            Url_Imagen,
            Nombre_Producto,
            Ruta_Carpeta_Imagenes,
            Sesion_Http,
            Timeout_Request,
        )

    return {
        "id": Id_De_Producto,
        "name": Nombre_Producto,
        "price": Precio_Actual,
        "category": Categoria_Estandar,
        "genero": Genero_Del_Producto,
        "color": Color_Principal,
        "colores": Colores_Del_Producto,
        "tallas": Tallas_Disponibles,
        "stock": Stock_Actual,
        "rating": Calificacion_Actual,
        "description": Descripcion_Actual,
        "image": Imagen_Final,
    }


def Scrapear_Catalogo_Desde_Url(
    Url_Catalogo,
    Selector_Producto,
    Selector_Nombre,
    Selector_Imagen,
    Selector_Categoria,
    Limite,
    Omitir_Sin_Imagen,
    Sesion_Http,
    Timeout_Request,
):
    try:
        Respuesta = Sesion_Http.get(Url_Catalogo, timeout=Timeout_Request)
        Respuesta.raise_for_status()
    except requests.RequestException as Error_De_Red:
        print(f"[WARN] No se pudo leer {Url_Catalogo}: {Error_De_Red}")
        return []

    Sopa = BeautifulSoup(Respuesta.text, "html.parser")
    Tarjetas = Sopa.select(Selector_Producto)

    Selectores_Alternos_De_Producto = [
        ".cart-product",
        ".card-product",
        "li.product-item",
        ".product-item",
        "article.product",
        ".products .product",
    ]

    if not Tarjetas:
        Selector_Alterno_Usado = None
        for Selector_Alterno in Selectores_Alternos_De_Producto:
            Tarjetas = Sopa.select(Selector_Alterno)
            if Tarjetas:
                Selector_Alterno_Usado = Selector_Alterno
                break

        if Selector_Alterno_Usado:
            print(
                "[INFO] "
                f"No se encontraron tarjetas con '{Selector_Producto}'. "
                f"Usando selector alterno '{Selector_Alterno_Usado}'."
            )
        else:
            print(
                f"[WARN] La URL {Url_Catalogo} no devolvio tarjetas con selector: {Selector_Producto}"
            )
            return []

    Titulo_De_Pagina = Extraer_Texto_Selector(
        Sopa,
        "h1",
        Selectores_Alternos=[".page-title", ".titulo", "title"],
    )

    Productos_Raw = []
    Omitidos_Sin_Nombre = 0
    Omitidos_Sin_Imagen = 0

    for Tarjeta in Tarjetas:
        if len(Productos_Raw) >= Limite:
            break

        Nombre_Producto = Extraer_Texto_Selector(
            Tarjeta,
            Selector_Nombre,
            Selectores_Alternos=[
                ".card-product-title",
                ".product-item-link",
                ".product-title",
                "h2 a",
                "h3 a",
                "a[title]",
            ],
        )
        Categoria_Original = Extraer_Texto_Selector(
            Tarjeta,
            Selector_Categoria,
            Selectores_Alternos=[".card-product-cat", ".product-category", ".categoria"],
        ) or Titulo_De_Pagina
        Url_Imagen = Extraer_Url_Imagen(Tarjeta, Selector_Imagen, Url_Catalogo)

        if not Nombre_Producto:
            Omitidos_Sin_Nombre += 1
            continue

        if Omitir_Sin_Imagen and not Url_Imagen:
            Omitidos_Sin_Imagen += 1
            continue

        Productos_Raw.append(
            {
                "name": Nombre_Producto,
                "categoria": Categoria_Original,
                "image": Url_Imagen,
            }
        )

    print(
        "[INFO] "
        f"{Url_Catalogo} -> extraidos={len(Productos_Raw)} "
        f"sin_nombre={Omitidos_Sin_Nombre} sin_imagen={Omitidos_Sin_Imagen}"
    )
    return Productos_Raw


def Guardar_Productos_Json(Lista_De_Productos, Ruta_Salida):
    Ruta_Salida.parent.mkdir(parents=True, exist_ok=True)
    with Ruta_Salida.open("w", encoding="utf-8") as Archivo_Json:
        json.dump(Lista_De_Productos, Archivo_Json, indent=2, ensure_ascii=False)
    print(f"[OK] Archivo generado: {Ruta_Salida.as_posix()} ({len(Lista_De_Productos)} productos)")




def Parsear_Argumentos():
    Parser = argparse.ArgumentParser(
        description="Scrapea productos y genera data/products_scraped.json",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    Parser.add_argument(
        "--url",
        action="append",
        required=False,
        help="URL del catalogo. Puedes repetir --url varias veces. Si no envias --url, se usa el listado iRun por defecto.",
    )
    Parser.add_argument(
        "--selector-producto",
        required=True,
        help="Selector CSS para la tarjeta/contenedor de producto.",
    )
    Parser.add_argument(
        "--selector-nombre",
        required=True,
        help="Selector CSS (dentro de la tarjeta) para el nombre.",
    )
    Parser.add_argument(
        "--selector-imagen",
        default="img",
        help="Selector CSS (dentro de la tarjeta) para la imagen.",
    )
    Parser.add_argument(
        "--selector-categoria",
        default="",
        help="Selector CSS (dentro de la tarjeta) para categoria.",
    )
    Parser.add_argument(
        "--categoria-por-defecto",
        default="",
        help="Categoria fallback: CALZADO, POLOS, PANTALONES u OTROS.",
    )
    Parser.add_argument(
        "--limite-por-url",
        type=int,
        default=5,
        help="Maximo de productos a extraer por cada URL.",
    )
    Parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Maximo de productos a generar en total. Si no se indica, se calcula como URLs x limite-por-url.",
    )
    Parser.add_argument(
        "--timeout",
        type=int,
        default=Timeout_Por_Defecto,
        help="Timeout HTTP por request (segundos).",
    )
    Parser.add_argument(
        "--descargar-imagenes",
        action="store_true",
        help="Descarga imagenes localmente en data/product_images_scraped.",
    )
    Parser.add_argument(
        "--permitir-sin-imagen",
        action="store_true",
        help="Si se activa, no se omiten productos sin imagen.",
    )
    Parser.add_argument(
        "--salida",
        default=str(Ruta_Salida_Por_Defecto),
        help="Ruta del JSON de salida.",
    )
    Parser.add_argument(
        "--carpeta-imagenes",
        default=str(Ruta_Carpeta_Imagenes_Por_Defecto),
        help="Carpeta de imagenes cuando se usa --descargar-imagenes.",
    )

    return Parser.parse_args()


def main():
    Argumentos = Parsear_Argumentos()

    Urls_A_Scrapear = [
        str(Url_Actual).strip()
        for Url_Actual in (Argumentos.url or [])
        if str(Url_Actual or "").strip()
    ]
    if not Urls_A_Scrapear:
        Urls_A_Scrapear = list(Urls_Irun_Por_Defecto)
        print(
            f"[INFO] No se recibio --url. Usando listado iRun por defecto ({len(Urls_A_Scrapear)} URLs)."
        )

    Limite_Por_Url = max(1, int(Argumentos.limite_por_url))
    if Argumentos.limite is None:
        Limite_Total = max(1, len(Urls_A_Scrapear) * Limite_Por_Url)
    else:
        Limite_Total = max(1, int(Argumentos.limite))

    Categoria_Por_Defecto = str(Argumentos.categoria_por_defecto or "").strip().upper()
    if Categoria_Por_Defecto and Categoria_Por_Defecto not in Categorias_De_Producto:
        Categorias_Validas = ", ".join(Categorias_De_Producto.keys())
        raise ValueError(
            "Categoria por defecto invalida. "
            f"Usa una de estas: {Categorias_Validas}"
        )

    Ruta_Salida = Path(Argumentos.salida)
    Ruta_Carpeta_Imagenes = Path(Argumentos.carpeta_imagenes)

    Sesion_Http = requests.Session()
    Sesion_Http.headers.update(Cabeceras_Http)

    Productos_Generados = []
    Nombres_Registrados = set()
    Id_De_Producto = 1

    for Url_Catalogo in Urls_A_Scrapear:
        if len(Productos_Generados) >= Limite_Total:
            break

        Cupo_Disponible = Limite_Total - len(Productos_Generados)
        Limite_Para_Esta_Url = min(Cupo_Disponible, Limite_Por_Url)
        if Limite_Para_Esta_Url <= 0:
            break

        Productos_Raw = Scrapear_Catalogo_Desde_Url(
            Url_Catalogo=Url_Catalogo,
            Selector_Producto=Argumentos.selector_producto,
            Selector_Nombre=Argumentos.selector_nombre,
            Selector_Imagen=Argumentos.selector_imagen,
            Selector_Categoria=Argumentos.selector_categoria,
            Limite=Limite_Para_Esta_Url,
            Omitir_Sin_Imagen=not Argumentos.permitir_sin_imagen,
            Sesion_Http=Sesion_Http,
            Timeout_Request=max(5, Argumentos.timeout),
        )

        for Producto_Raw in Productos_Raw:
            if len(Productos_Generados) >= Limite_Total:
                break

            Nombre_Unico = Asegurar_Nombre_Unico(
                Producto_Raw["name"],
                Nombres_Registrados,
            )

            Producto_Normalizado = Construir_Producto_Estandar(
                Id_De_Producto=Id_De_Producto,
                Nombre_Producto=Nombre_Unico,
                Categoria_Original=Producto_Raw.get("categoria"),
                Url_Imagen=Producto_Raw.get("image"),
                Categoria_Por_Defecto=Categoria_Por_Defecto,
                Descargar_Imagenes=Argumentos.descargar_imagenes,
                Ruta_Carpeta_Imagenes=Ruta_Carpeta_Imagenes,
                Sesion_Http=Sesion_Http,
                Timeout_Request=max(5, Argumentos.timeout),
            )

            Productos_Generados.append(Producto_Normalizado)
            Id_De_Producto += 1

    if not Productos_Generados:
        raise RuntimeError(
            "No se generaron productos. Revisa URL/selectores o usa --permitir-sin-imagen."
        )

    Guardar_Productos_Json(Productos_Generados, Ruta_Salida)
    Imprimir_Resumen(Productos_Generados)
    print("\nListo. Puedes alternar en la web entre catalogo automatico y scrapeado.")


if __name__ == "__main__":
    main()
