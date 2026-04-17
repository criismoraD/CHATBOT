import spacy
import re
import unicodedata

# Cargar el modelo de español de spaCy
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "es_core_news_sm"])
    nlp = spacy.load("es_core_news_sm")

# Palabras que NO queremos que se eliminen porque son importantes para e-commerce
PALABRAS_CLAVE_ECOMMERCE = {"con", "sin", "para", "de", "mujer", "hombre", "talla", "hasta", "menos", "mas"}

# Actualizar el vocabulario de stop words de spaCy
for palabra in PALABRAS_CLAVE_ECOMMERCE:
    nlp.vocab[palabra].is_stop = False

def limpiar_texto(texto: str) -> str:
    """Normaliza un texto eliminando tildes y caracteres especiales."""
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9\s-]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def tokenizar_y_lematizar(texto: str) -> list[str]:
    """
    Recibe un texto, lo limpia, elimina stop words (respetando excepciones de e-commerce),
    y devuelve la lista de lemas de las palabras resultantes, más los bigramas.
    """
    texto_limpio = limpiar_texto(texto)
    doc = nlp(texto_limpio)

    # Extraemos lemas, omitiendo stop words y puntuación, quedándonos solo con tokens de al menos 2 letras
    tokens = []
    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 1:
            tokens.append(token.lemma_)

    # Agregamos bigramas
    bigramas = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
    return tokens + bigramas
