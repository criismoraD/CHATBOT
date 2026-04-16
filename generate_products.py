"""
Generador de base de datos de productos - SENATI SPORTS
Ejecuta: python generate_products.py
Genera: data/products.json (250 productos con multiples colores y tallas)
"""

import json
import random
from pathlib import Path

# --- CONFIGURACION ---
Cantidad_De_Productos_Por_Categoria = 40
Calificacion_Minima = 3.8
Calificacion_Maxima = 5.0
Stock_Minimo = 5
Stock_Maximo = 80

Colores_Disponibles = ["Negro", "Blanco", "Rojo", "Azul", "Gris", "Verde"]
Tallas_Calzado = ["36", "37", "38", "39", "40", "41", "42", "43", "44"]
Tallas_Ropa = ["XS", "S", "M", "L", "XL", "XXL"]
Tallas_Otros = ["Unico"]
Generos_Disponibles = ["Hombre", "Mujer", "Unisex"]

Categorias_De_Producto = {
    "CALZADO": {
        "types": [
            "Zapatillas para Correr",
            "Chimpunes",
            "Zapatillas Casuales",
            "Zapatillas de Trail",
            "Zapatillas de Crossfit",
            "Sandalias Deportivas",
            "Botas de Trekking",
            "Zapatillas de Basquet",
            "Zapatillas de Skate",
            "Zapatillas de Entreno",
        ],
        "tallas": Tallas_Calzado,
        "price_range": (59.99, 189.99),
        "descriptions": [
            "Amortiguacion reactiva para maximo rendimiento en cada zancada.",
            "Traccion superior en cualquier superficie para un control total.",
            "Diseno aerodinamico con suela de respuesta rapida.",
            "Tecnologia de absorcion de impacto para proteger tus articulaciones.",
            "Malla transpirable con soporte lateral reforzado.",
        ],
    },
    "POLOS": {
        "types": [
            "Polo Dry-Fit",
            "Polo de Compresion",
            "Polo de Entreno",
            "Top para Correr",
            "Polo de Algodon Deportivo",
            "Polo con Proteccion UV",
            "Bividi de Gym",
            "Polo Manga Larga",
            "Polo Termico",
            "Polo de Ciclismo",
        ],
        "tallas": Tallas_Ropa,
        "price_range": (24.99, 79.99),
        "descriptions": [
            "Tela ultra transpirable con tecnologia de secado rapido.",
            "Compresion muscular para mejorar la circulacion durante el ejercicio.",
            "Tejido antibacterial que elimina olores tras entrenamientos intensos.",
            "Costuras planas para evitar rozaduras en carreras largas.",
            "Proteccion UV 50+ para entrenamientos al aire libre.",
        ],
    },
    "PANTALONES": {
        "types": [
            "Pantalon de Entreno",
            "Short para Correr",
            "Leggings de Compresion",
            "Buzo Jogger",
            "Short de Basquet",
            "Pantalon de Yoga",
            "Bermuda Deportiva",
            "Pantalon de Trekking",
            "Short de Ciclismo",
            "Pantalon Cortaviento",
        ],
        "tallas": Tallas_Ropa,
        "price_range": (29.99, 89.99),
        "descriptions": [
            "Libertad de movimiento total para entrenamientos intensos.",
            "Tejido elastico en 4 direcciones con cintura ajustable.",
            "Bolsillos con cierre para llevar tu celular de forma segura.",
            "Corte ergonomico que se adapta a tu cuerpo en cada movimiento.",
            "Material resistente al agua para entrenar bajo lluvia.",
        ],
    },
    "OTROS": {
        "types": [
            "Gorra Visera Plana",
            "Mochila de Gym",
            "Tomatodo Termico",
            "Guantes de Entreno",
            "Reloj Deportivo",
            "Banda Elastica",
            "Tomatodo 1L",
            "Bolso Deportivo",
            "Munequera Pro",
            "Cintillo Deportivo",
        ],
        "tallas": Tallas_Otros,
        "price_range": (14.99, 129.99),
        "descriptions": [
            "Diseno ergonomico pensado para el deportista exigente.",
            "Material premium resistente al desgaste diario.",
            "Aislamiento termico que mantiene tu bebida fria por 24 horas.",
            "Ajuste personalizado para maximo confort durante el entrenamiento.",
            "Tecnologia de monitoreo de actividad y ritmo cardiaco.",
        ],
    },
}

Adjetivos_De_Modelo = ["Pro", "Elite", "Ultra", "Nitro", "Aero", "Max", "Titan", "Fury", "Volt", "Prime"]

Ruta_Carpeta_Data = Path("data")
Ruta_Archivo_Json = Ruta_Carpeta_Data / "products.json"


def Validar_Config_De_Categorias():
    """Valida que todas las categorias tengan las claves minimas requeridas."""
    Claves_Requeridas = {"types", "tallas", "price_range", "descriptions"}
    for Nombre_Categoria, Configuracion in Categorias_De_Producto.items():
        Claves_Faltantes = Claves_Requeridas.difference(Configuracion.keys())
        if Claves_Faltantes:
            Texto_De_Claves = ", ".join(sorted(Claves_Faltantes))
            raise ValueError(f"La categoria {Nombre_Categoria} no incluye: {Texto_De_Claves}")


def Elegir_Tallas_Disponibles(Lista_De_Tallas):
    Cantidad_De_Tallas = random.randint(1, len(Lista_De_Tallas))
    return sorted(random.sample(Lista_De_Tallas, Cantidad_De_Tallas))


def Elegir_Colores_Disponibles(Lista_De_Colores):
    Cantidad_De_Colores = random.randint(2, len(Lista_De_Colores))
    Colores_Muestreados = random.sample(Lista_De_Colores, Cantidad_De_Colores)
    Orden_De_Color = {Color: Indice for Indice, Color in enumerate(Lista_De_Colores)}
    return sorted(Colores_Muestreados, key=lambda Color: Orden_De_Color[Color])


def Generar_Productos(Cantidad_Por_Categoria=Cantidad_De_Productos_Por_Categoria):
    """Genera una lista de productos con nombres unicos, varios colores y stock."""
    Validar_Config_De_Categorias()

    Productos_Generados = []
    Nombres_Registrados = set()
    Id_De_Producto = 1

    for Nombre_Categoria, Configuracion in Categorias_De_Producto.items():
        Tipos_De_Producto = Configuracion["types"]
        Tallas_De_Categoria = Configuracion["tallas"]
        Precio_Minimo, Precio_Maximo = Configuracion["price_range"]
        Descripciones = Configuracion["descriptions"]

        Combinaciones_De_Nombre = [
            (Tipo, Adjetivo, Genero)
            for Tipo in Tipos_De_Producto
            for Adjetivo in Adjetivos_De_Modelo
            for Genero in Generos_Disponibles
        ]
        random.shuffle(Combinaciones_De_Nombre)

        if Cantidad_Por_Categoria > len(Combinaciones_De_Nombre):
            raise ValueError(
                f"Cantidad_Por_Categoria ({Cantidad_Por_Categoria}) excede combinaciones unicas para {Nombre_Categoria}."
            )

        for Indice in range(Cantidad_Por_Categoria):
            Tipo_De_Producto, Adjetivo_Actual, Genero_Del_Producto = Combinaciones_De_Nombre[Indice]
            Colores_Del_Producto = Elegir_Colores_Disponibles(Colores_Disponibles)
            Color_Principal = Colores_Del_Producto[0]
            Tallas_Disponibles = Elegir_Tallas_Disponibles(Tallas_De_Categoria)
            Precio_Actual = round(random.uniform(Precio_Minimo, Precio_Maximo), 2)
            Descripcion_Actual = random.choice(Descripciones)
            Calificacion_Actual = round(random.uniform(Calificacion_Minima, Calificacion_Maxima), 1)
            Stock_Actual = random.randint(Stock_Minimo, Stock_Maximo)

            Nombre_Producto = f"{Tipo_De_Producto} {Adjetivo_Actual} {Genero_Del_Producto}"
            if Nombre_Producto in Nombres_Registrados:
                Nombre_Producto = f"{Nombre_Producto} {Nombre_Categoria.title()}"
            Nombres_Registrados.add(Nombre_Producto)

            Producto = {
                "id": Id_De_Producto,
                "name": Nombre_Producto,
                "price": Precio_Actual,
                "category": Nombre_Categoria,
                "genero": Genero_Del_Producto,
                "color": Color_Principal,
                "colores": Colores_Del_Producto,
                "tallas": Tallas_Disponibles,
                "stock": Stock_Actual,
                "rating": Calificacion_Actual,
                "description": Descripcion_Actual,
            }
            Productos_Generados.append(Producto)
            Id_De_Producto += 1

    return Productos_Generados


def Guardar_Json(Productos_Generados):
    Ruta_Carpeta_Data.mkdir(parents=True, exist_ok=True)
    with Ruta_Archivo_Json.open("w", encoding="utf-8") as Archivo_Json:
        json.dump(Productos_Generados, Archivo_Json, indent=2, ensure_ascii=False)
    print(f"[OK] {Ruta_Archivo_Json.as_posix()} generado con {len(Productos_Generados)} productos.")


def Imprimir_Resumen(Productos_Generados):
    print("\n--- RESUMEN ---")
    Conteo_Por_Categoria = {}
    Conteo_Por_Color = {}
    Conteo_Por_Genero = {}

    for Producto in Productos_Generados:
        Categoria = Producto["category"]
        Conteo_Por_Categoria[Categoria] = Conteo_Por_Categoria.get(Categoria, 0) + 1
        Genero = Producto.get("genero", "No definido")
        Conteo_Por_Genero[Genero] = Conteo_Por_Genero.get(Genero, 0) + 1

        Colores_De_Producto = Producto.get("colores", [Producto.get("color")])
        for Color in Colores_De_Producto:
            if Color:
                Conteo_Por_Color[Color] = Conteo_Por_Color.get(Color, 0) + 1

    print("Por categoria:")
    for Categoria, Cantidad in sorted(Conteo_Por_Categoria.items()):
        print(f"  {Categoria}: {Cantidad} productos")

    print("\nPor color:")
    for Color, Cantidad in sorted(Conteo_Por_Color.items()):
        print(f"  {Color}: {Cantidad} productos")

    print("\nPor genero:")
    for Genero, Cantidad in sorted(Conteo_Por_Genero.items()):
        print(f"  {Genero}: {Cantidad} productos")

    print(f"\nTotal: {len(Productos_Generados)} productos")


# Alias de compatibilidad para integraciones existentes.
def generate_products():
    return Generar_Productos()


def save_json(products):
    Guardar_Json(products)


def print_summary(products):
    Imprimir_Resumen(products)


if __name__ == "__main__":
    print("Generando base de datos de productos SENATI SPORTS...")
    Productos = Generar_Productos()
    Guardar_Json(Productos)
    Imprimir_Resumen(Productos)
    print("\nListo. Ahora ejecuta 'python train_pytorch.py' para re-entrenar el modelo.")
