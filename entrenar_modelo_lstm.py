"""
entrenar_modelo_lstm.py · Entrenamiento del Modelo LSTM
═══════════════════════════════════════════════════════

Entrena una red neuronal LSTM bidireccional para clasificar intenciones
del chatbot a partir de los patterns definidos en data/intenciones_chatbot.json.

FLUJO DE ENTRENAMIENTO:
  1. Cargar_Intents() → lee data/intenciones_chatbot.json
  2. Preparar_Datos():
     a. Tokeniza y lematiza cada pattern con core.procesamiento_lenguaje
     b. Construye vocabulario filtrado (elimina términos muy raros)
     c. Convierte patterns a secuencias de índices (padding)
     d. Divide en train/val (80/20 estratificado)
  3. Entrenar_Modelo():
     a. DataLoader con WeightedRandomSampler (balancea clases)
     b. Modelo: Embedding → BiLSTM → Dropout → Linear
     c. Optimizador: Adam con weight decay
     d. Scheduler: ReduceLROnPlateau
     e. Early stopping por F1-macro en validación
  4. Evalúa con classification_report (precision, recall, F1)
  5. Guarda modelo en data/modelo_lstm.pth:
     - model_state, input_size, hidden_size, output_size
     - embedding_dim, all_words, tags, max_length

ARQUITECTURA DEL MODELO:
  Input → Embedding(vocab, 128) → BiLSTM(128//2, bidirectional)
  → Dropout(0.4) → Linear(hidden, num_tags) → Output

USO:
  python entrenar_modelo_lstm.py
  (solo necesario si se modificó data/intenciones_chatbot.json)
"""
import random
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path


import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight

from core.procesamiento_lenguaje import Tokenizar_Y_Lematizar as tokenizar

# --- DE model_arch.py ---
class NeuralNet(nn.Module):
    def __init__(self, vocab_size, hidden_size, num_classes, padding_idx=0, embedding_dim=128):
        super().__init__()
        self.padding_idx = padding_idx
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_idx)
        self.lstm = nn.LSTM(embedding_dim, hidden_size // 2, batch_first=True, bidirectional=True, num_layers=1)
        self.dropout = nn.Dropout(0.4)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x, longitudes=None):
        # x shape: (batch_size, sequence_length)
        out = self.embedding(x)
        # out shape: (batch_size, sequence_length, embedding_dim)

        if longitudes is None:
            longitudes = (x != self.padding_idx).sum(dim=1)

        longitudes = longitudes.clamp(min=1).to('cpu')
        Secuencias_Empaquetadas = nn.utils.rnn.pack_padded_sequence(
            out,
            longitudes,
            batch_first=True,
            enforce_sorted=False,
        )

        # Pasar por LSTM ignorando pasos de padding.
        _, (hn, cn) = self.lstm(Secuencias_Empaquetadas)

        # hn shape: (num_layers * num_directions, batch_size, hidden_size // 2)
        # Al ser 1 capa bidireccional, concatenamos las dos direcciones
        hidden = torch.cat((hn[0,:,:], hn[1,:,:]), dim=1)

        out = self.dropout(hidden)
        out = self.fc(out)
        return out


# --- CONFIGURACION ---
Ruta_Intents = Path("data/intenciones_chatbot.json")
Ruta_Modelo = Path("data/modelo_lstm.pth")
Semilla_Global = 100

Tamano_Lote = 32
Tamano_Capa_Oculta = 128
Tamano_Embedding = 128
Tasa_Aprendizaje = 0.005
Numero_De_Epocas = 40
Paciencia_EarlyStopping = 30
Weight_Decay = 1e-3
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

def Crear_Secuencia(oracion_tokenizada, indice_vocabulario, longitud_maxima):
    secuencia = []
    for palabra in oracion_tokenizada:
        indice = indice_vocabulario.get(palabra)
        if indice is not None:
            secuencia.append(indice)

    # Padding con 0 al final si es más corto, truncar si es más largo
    if len(secuencia) < longitud_maxima:
        secuencia.extend([0] * (longitud_maxima - len(secuencia)))
    else:
        secuencia = secuencia[:longitud_maxima]

    return np.array(secuencia, dtype=np.int64)

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

    vocabulario_filtrado = ["<PAD>"]  # Índice 0 para padding
    for termino, frecuencia in contador_vocabulario.items():
        if termino in {'?', '!', '.', ','}:
            continue

        frecuencia_minima = Frecuencia_Minima_NGrama if '_' in termino else Frecuencia_Minima_Unigrama
        if frecuencia >= frecuencia_minima:
            vocabulario_filtrado.append(termino)

    # Ordenamos el vocabulario excepto el PAD que debe quedar en el índice 0
    vocabulario = ["<PAD>"] + sorted(set(vocabulario_filtrado[1:]))
    indice_vocabulario = {palabra: indice for indice, palabra in enumerate(vocabulario)}

    # Calcular longitud máxima de secuencia para el padding
    longitud_maxima = max(len(palabras) for palabras, _ in pares) if pares else 10

    if not vocabulario:
        raise ValueError('El vocabulario quedo vacio tras el filtrado.')

    etiquetas = sorted(set(etiquetas))

    X = []
    y = []
    for palabras, tag in pares:
        X.append(Crear_Secuencia(palabras, indice_vocabulario, longitud_maxima))
        y.append(etiquetas.index(tag))

    return np.array(X), np.array(y), vocabulario, etiquetas, longitud_maxima

class Dataset_De_Chat(Dataset):
    def __init__(self, X, y):
        self.X = torch.from_numpy(X).long()  # Ahora es long para Embedding
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
            longitudes = (xb != 0).sum(dim=1).clamp(min=1)
            salida = modelo(xb, longitudes)
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
    modelo = NeuralNet(
        input_size,
        Tamano_Capa_Oculta,
        output_size,
        embedding_dim=Tamano_Embedding,
    ).to(dispositivo)
    
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
            longitudes = (xb != 0).sum(dim=1).clamp(min=1)
            out = modelo(xb, longitudes)
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
    X, y, vocab, tags, longitud_maxima = Preparar_Datos(intents)
    
    print(f"{len(X)} patrones totales")
    print(f"{len(tags)} intents: {tags}")
    print(f"{len(vocab)} palabras únicas")
    print(f"Longitud máxima de secuencia: {longitud_maxima}")
    
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

    train_loader = DataLoader(Dataset_De_Chat(X_train, y_train), batch_size=Tamano_Lote, sampler=sampler_balanceado, drop_last=True)
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
        "embedding_dim": Tamano_Embedding,
        "all_words": vocab,
        "tags": tags,
        "max_length": longitud_maxima
    }, Ruta_Modelo)
    print(f"\n✓ Modelo guardado en {Ruta_Modelo}")

if __name__ == "__main__":
    main()
