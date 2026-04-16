import random

# --- CONSTANTES DE INVENTARIO ---
Calificacion_Minima = 3.5
Calificacion_Maxima = 5.0
Stock_Minimo = 5
Stock_Maximo = 50

Colores_Disponibles = ["Negro", "Blanco", "Rojo", "Azul", "Gris", "Verde"]

Categorias_De_Producto = {
    "CALZADO": {
        "tallas": ["38", "39", "40", "41", "42", "43"],
        "descriptions": [
            "Zapatillas deportivas de alto rendimiento con amortiguación avanzada.",
            "Calzado ergonómico diseñado para máxima comodidad durante el entrenamiento.",
            "Zapatillas versátiles ideales para running y actividades al aire libre."
        ]
    },
    "POLOS": {
        "tallas": ["S", "M", "L", "XL"],
        "descriptions": [
            "Polo deportivo con tecnología de secado rápido y tejido transpirable.",
            "Camiseta ligera de algodón premium para uso deportivo o casual.",
            "Top deportivo ajustado que permite total libertad de movimiento."
        ]
    },
    "PANTALONES": {
        "tallas": ["S", "M", "L", "XL"],
        "descriptions": [
            "Pantalón deportivo resistente con bolsillos laterales y ajuste seguro.",
            "Short cómodo diseñado para entrenamientos intensos y running.",
            "Leggings elásticos con soporte optimizado para actividades de alto impacto."
        ]
    },
    "OTROS": {
        "tallas": ["Única"],
        "descriptions": [
            "Accesorio deportivo esencial para completar tu equipamiento.",
            "Producto complementario de alta durabilidad para tu rutina diaria.",
            "Accesorio diseñado para mejorar tu experiencia en cada entrenamiento."
        ]
    }
}

# --- FUNCIONES DE AYUDA PARA GENERACIÓN ---

def Elegir_Colores_Disponibles(Lista_Colores):
    """Elige una sublista aleatoria de colores."""
    Cantidad = random.randint(1, min(3, len(Lista_Colores)))
    return random.sample(Lista_Colores, Cantidad)

def Elegir_Tallas_Disponibles(Lista_Tallas):
    """Elige una sublista aleatoria de tallas y las ordena."""
    Cantidad = random.randint(1, len(Lista_Tallas))
    Seleccion = random.sample(Lista_Tallas, Cantidad)
    # Intento de orden numérico si es posible, si no, alfabético
    try:
        return sorted(Seleccion, key=lambda x: int(x) if x.isdigit() else x)
    except ValueError:
        return sorted(Seleccion)

# --- UTILIDADES DE RESUMEN ---

def Imprimir_Resumen(Lista_De_Productos):
    """Imprime un resumen estadístico de la lista de productos por categoría."""
    Conteo_Por_Categoria = {}
    for Producto in Lista_De_Productos:
        Categoria = Producto.get("category", "SIN_CATEGORIA")
        Conteo_Por_Categoria[Categoria] = Conteo_Por_Categoria.get(Categoria, 0) + 1

    print("\n--- RESUMEN SCRAPING ---")
    for Categoria, Cantidad in sorted(Conteo_Por_Categoria.items()):
        print(f"  {Categoria}: {Cantidad}")
    print(f"Total: {len(Lista_De_Productos)}")
