import json
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path

import re
import unicodedata

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight

# --- DE utils_texto.py ---
def _stem_es(p):
    if p.endswith('es') and len(p) > 4: return p[:-2]
    if p.endswith('s') and len(p) > 3: return p[:-1]
    return p

STOP = {'el','la','los','las','de','del','un','una','y','o'}

def tokenizar(texto: str) -> list[str]:
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c)!= 'Mn')
    texto = re.sub(r'[^a-z0-9ñü\s]', ' ', texto)
    tokens = [t for t in re.sub(r'\s+', ' ', texto).strip().split() if t not in STOP and len(t)>1]
    tokens = [_stem_es(t) for t in tokens]
    bigramas = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
    return tokens + bigramas

# --- DE model_arch.py ---
class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.l1 = nn.Linear(input_size, hidden_size) # 128
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.l2 = nn.Linear(hidden_size, hidden_size // 2) # 64
        self.bn2 = nn.BatchNorm1d(hidden_size // 2)
        self.l3 = nn.Linear(hidden_size // 2, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        out = self.dropout(self.relu(self.bn1(self.l1(x))))
        out = self.dropout(self.relu(self.bn2(self.l2(out))))
        out = self.l3(out)
        return out


# --- CONFIGURACION ---
Ruta_Intents = Path("data/intents.json")
Ruta_Modelo = Path("data/model.pth")
Semilla_Global = 42

Tamano_Lote = 32
Tamano_Capa_Oculta = 128
Tasa_Aprendizaje = 0.001
Numero_De_Epocas = 300
Paciencia_EarlyStopping = 12
Weight_Decay = 5e-4
Frecuencia_Minima_Unigrama = 1
Frecuencia_Minima_NGrama = 2
Delta_Minima_Mejora = 1e-4

def Fijar_Semilla_Global(semilla=Semilla_Global):
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(semilla)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def Cargar_Intents():
    with Ruta_Intents.open('r', encoding='utf-8') as f:
        return json.load(f)

def Crear_Bolsa_De_Palabras(oracion_tokenizada, indice_vocabulario, tamano_vocabulario):
    # Se usa presencia binaria para quedar alineado con la inferencia en app.py.
    bolsa = np.zeros(tamano_vocabulario, dtype=np.float32)
    for palabra in set(oracion_tokenizada):
        indice = indice_vocabulario.get(palabra)
        if indice is not None:
            bolsa[indice] = 1.0
    return bolsa

def Preparar_Datos(datos_intents):
    contador_vocabulario = Counter()
    etiquetas = []
    pares = []
    for intent in datos_intents['intents']:
        tag = intent['tag']
        etiquetas.append(tag)
        for patron in intent['patterns']:
            palabras = tokenizar(patron)
            contador_vocabulario.update(palabras)
            pares.append((palabras, tag))

    vocabulario_filtrado = []
    for termino, frecuencia in contador_vocabulario.items():
        if termino in {'?', '!', '.', ','}:
            continue

        frecuencia_minima = Frecuencia_Minima_NGrama if '_' in termino else Frecuencia_Minima_Unigrama
        if frecuencia >= frecuencia_minima:
            vocabulario_filtrado.append(termino)

    vocabulario = sorted(set(vocabulario_filtrado))
    indice_vocabulario = {palabra: indice for indice, palabra in enumerate(vocabulario)}

    if not vocabulario:
        raise ValueError('El vocabulario quedo vacio tras el filtrado.')

    etiquetas = sorted(set(etiquetas))

    X = []
    y = []
    for palabras, tag in pares:
        X.append(Crear_Bolsa_De_Palabras(palabras, indice_vocabulario, len(vocabulario)))
        y.append(etiquetas.index(tag))

    return np.array(X), np.array(y), vocabulario, etiquetas

class Dataset_De_Chat(Dataset):
    def __init__(self, X, y):
        self.X = torch.from_numpy(X).float()
        self.y = torch.from_numpy(y).long()
    def __len__(self): return len(self.X)
    def __getitem__(self, i): return self.X[i], self.y[i]


def Evaluar_Modelo(modelo, data_loader, criterio, dispositivo):
    modelo.eval()
    perdida_total = 0.0
    predicciones = []
    reales = []

    with torch.no_grad():
        for xb, yb in data_loader:
            xb, yb = xb.to(dispositivo), yb.to(dispositivo)
            salida = modelo(xb)
            perdida = criterio(salida, yb)
            perdida_total += perdida.item()
            predicciones.extend(salida.argmax(1).cpu().numpy())
            reales.extend(yb.cpu().numpy())

    perdida_promedio = perdida_total / max(1, len(data_loader))
    exactitud = accuracy_score(reales, predicciones) if reales else 0.0
    f1_macro = f1_score(reales, predicciones, average='macro', zero_division=0) if reales else 0.0
    return perdida_promedio, exactitud, f1_macro, reales, predicciones

def Entrenar_Modelo(train_loader, val_loader, input_size, output_size, pesos_clase):
    dispositivo = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    modelo = NeuralNet(input_size, Tamano_Capa_Oculta, output_size).to(dispositivo)
    
    criterio = nn.CrossEntropyLoss(weight=pesos_clase.to(dispositivo))
    optimizador = torch.optim.Adam(modelo.parameters(), lr=Tasa_Aprendizaje, weight_decay=Weight_Decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizador, mode='min', factor=0.5, patience=8)
    
    mejor_val = float('inf')
    mejor_f1_macro = -1.0
    mejor_estado = None
    sin_mejora = 0
    
    print(f"\nEntrenando en {dispositivo} | Train: {len(train_loader.dataset)} | Val: {len(val_loader.dataset)}")
    print("Epoca | Train Loss | Val Loss | Val Acc | Val F1(m)")
    print("-" * 58)
    
    for epoca in range(Numero_De_Epocas):
        modelo.train()
        loss_train = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(dispositivo), yb.to(dispositivo)
            optimizador.zero_grad()
            out = modelo(xb)
            loss = criterio(out, yb)
            loss.backward()
            optimizador.step()
            loss_train += loss.item()
        loss_train /= len(train_loader)
        
        loss_val, acc_val, f1_val_macro, _, _ = Evaluar_Modelo(
            modelo,
            val_loader,
            criterio,
            dispositivo,
        )
        scheduler.step(loss_val)
        
        if (epoca+1) % 10 == 0:
            print(f"{epoca+1:5d} | {loss_train:10.4f} | {loss_val:8.4f} | {acc_val:7.2%} | {f1_val_macro:8.4f}")
        
        mejora_por_f1 = f1_val_macro > (mejor_f1_macro + Delta_Minima_Mejora)
        mejora_por_loss = abs(f1_val_macro - mejor_f1_macro) <= Delta_Minima_Mejora and loss_val < (mejor_val - Delta_Minima_Mejora)

        if mejora_por_f1 or mejora_por_loss:
            mejor_val = loss_val
            mejor_f1_macro = f1_val_macro
            mejor_estado = deepcopy(modelo.state_dict())
            sin_mejora = 0
        else:
            sin_mejora += 1
            if sin_mejora >= Paciencia_EarlyStopping:
                print(f"\nEarly stopping en época {epoca+1}")
                break

    if mejor_estado is None:
        mejor_estado = deepcopy(modelo.state_dict())

    modelo.load_state_dict(mejor_estado)
    _, _, _, reales_finales, preds_finales = Evaluar_Modelo(
        modelo,
        val_loader,
        criterio,
        dispositivo,
    )
    return modelo, reales_finales, preds_finales

def main():
    Fijar_Semilla_Global()
    intents = Cargar_Intents()
    X, y, vocab, tags = Preparar_Datos(intents)
    
    print(f"{len(X)} patrones totales")
    print(f"{len(tags)} intents: {tags}")
    print(f"{len(vocab)} palabras únicas")
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=Semilla_Global, stratify=y)
    
    pesos = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    pesos = torch.tensor(pesos, dtype=torch.float)

    conteo_por_clase = np.bincount(y_train)
    pesos_por_muestra = 1.0 / np.maximum(conteo_por_clase[y_train], 1)
    sampler_balanceado = WeightedRandomSampler(
        weights=torch.tensor(pesos_por_muestra, dtype=torch.double),
        num_samples=len(pesos_por_muestra),
        replacement=True,
    )

    train_loader = DataLoader(Dataset_De_Chat(X_train, y_train), batch_size=Tamano_Lote, sampler=sampler_balanceado)
    val_loader = DataLoader(Dataset_De_Chat(X_val, y_val), batch_size=Tamano_Lote)
    
    modelo, y_true, y_pred = Entrenar_Modelo(train_loader, val_loader, len(vocab), len(tags), pesos)
    
    print("\n" + "="*60)
    print("REPORTE VALIDACIÓN")
    print("="*60)
    print(classification_report(y_true, y_pred, target_names=tags, digits=3))
    
    torch.save({
        "model_state": modelo.state_dict(),
        "input_size": len(vocab),
        "hidden_size": Tamano_Capa_Oculta,
        "output_size": len(tags),
        "all_words": vocab,
        "tags": tags
    }, Ruta_Modelo)
    print(f"\n✓ Modelo guardado en {Ruta_Modelo}")

if __name__ == "__main__":
    main()
