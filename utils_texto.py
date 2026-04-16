# utils_texto.py - V2
import re, unicodedata

def _stem_es(p):
    if p.endswith('es') and len(p) > 4: return p[:-2]
    if p.endswith('s') and len(p) > 3: return p[:-1]
    return p

STOP = {'el','la','los','las','de','del','un','una','y','o'} # <— quité 'que','me','te'

def tokenizar(texto: str) -> list[str]:
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c)!= 'Mn')
    texto = re.sub(r'[^a-z0-9ñü\s]', ' ', texto)
    tokens = [t for t in re.sub(r'\s+', ' ', texto).strip().split() if t not in STOP and len(t)>1] # <— len>1 para guardar "no","si"
    tokens = [_stem_es(t) for t in tokens]
    bigramas = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
    return tokens + bigramas