"""
core/procesamiento_lenguaje.py · Utilidades NLP
════════════════════════════════════════════════

Funciones de limpieza, tokenización y lematización usando spaCy.
Optimizado para el dominio de e-commerce deportivo (SENATI Sports).

FLUJO DE PROCESAMIENTO:
  1. Normalizar_Texto(texto) → minúsculas, sin tildes, sin caracteres especiales
  2. Tokenizar_Y_Lematizar(texto) → lemas + bigramas (ej: "zapatilla_correr")
     a. Reemplaza sinónimos locales (casaca→chaqueta, polo→camiseta)
     b. Limpia el texto (tildes, caracteres especiales)
     c. Procesa con spaCy (tokenización + lematización)
     d. Elimina stop words (excepto palabras clave de e-commerce)
     e. Genera bigramas para capturar contexto (ej: "talla_42")

USO:
  from core.procesamiento_lenguaje import Tokenizar_Y_Lematizar, Normalizar_Texto
  lemas = Tokenizar_Y_Lematizar("zapatillas running negras para hombre")
  # → ['zapatilla', 'correr', 'negro', 'hombre', 'zapatilla_correr', ...]
"""

import re
import unicodedata
import spacy


# ─── Carga del Modelo spaCy ──────────────────────────────────────────────────

try:
    _Modelo_NLP = spacy.load("es_core_news_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "es_core_news_sm"])
    _Modelo_NLP = spacy.load("es_core_news_sm")


# ─── Palabras Clave de E-Commerce (no se eliminan como stop words) ────────────

_PALABRAS_CLAVE_ECOMMERCE = {"con", "sin", "para", "de", "mujer", "hombre", "talla", "hasta", "menos", "mas"}

for _Palabra in _PALABRAS_CLAVE_ECOMMERCE:
    _Modelo_NLP.vocab[_Palabra].is_stop = False


# ─── Diccionario de Sinónimos Locales ────────────────────────────────────────

_DICCIONARIO_DE_SINONIMOS = {
    "casaca": "chaqueta",
    "casacas": "chaqueta",
    "chaquetas": "chaqueta",
    "polera": "sudadera",
    "poleras": "sudadera",
    "polo": "camiseta",
    "polos": "camiseta",
    "playera": "camiseta",
    "playeras": "camiseta",
    "zapatillas": "zapatilla",
    "tenis": "zapatilla",
}


# ─── Funciones Públicas ──────────────────────────────────────────────────────

def Normalizar_Texto(Texto: str) -> str:
    """Normaliza un texto eliminando tildes, caracteres especiales y normalizando espacios."""
    Texto = unicodedata.normalize('NFD', Texto.lower())
    Texto = ''.join(Caracter for Caracter in Texto if unicodedata.category(Caracter) != 'Mn')
    Texto = re.sub(r'[^a-z0-9\s-]', ' ', Texto)
    return re.sub(r'\s+', ' ', Texto).strip()


def _Normalizar_Sinonimos_Locales(Texto: str) -> str:
    """Reemplaza sinónimos locales por su forma canónica antes de lematizar."""
    Texto_Normalizado = str(Texto or "")
    for Termino_Original, Termino_Canonico in _DICCIONARIO_DE_SINONIMOS.items():
        Patron = rf"\b{re.escape(Termino_Original)}\b"
        Texto_Normalizado = re.sub(Patron, Termino_Canonico, Texto_Normalizado, flags=re.IGNORECASE)
    return Texto_Normalizado


def Tokenizar_Y_Lematizar(Texto: str) -> list[str]:
    """
    Limpia, elimina stop words (respetando excepciones de e-commerce)
    y devuelve lemas + bigramas del texto.
    """
    Texto_Normalizado = _Normalizar_Sinonimos_Locales(Texto)
    Texto_Limpio = Normalizar_Texto(Texto_Normalizado)
    Doc = _Modelo_NLP(Texto_Limpio)

    # Extraer lemas (sin stop words ni puntuación, mínimo 2 caracteres)
    Tokens = []
    for Token in Doc:
        if not Token.is_stop and not Token.is_punct and len(Token.text) > 1:
            Tokens.append(Token.lemma_)

    # Agregar bigramas para mayor contexto semántico
    Bigramas = [f"{Tokens[i]}_{Tokens[i+1]}" for i in range(len(Tokens) - 1)]
    return Tokens + Bigramas
