import os
import json
import torch
import numpy as np
from train_pytorch import NeuralNet
from faster_whisper import WhisperModel
import config
from utils_nlp import tokenizar_y_lematizar as Tokenizar_Texto

Dispositivo = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
Modelo_IA = None
Todas_Las_Palabras = []
Etiquetas_De_Intencion = []
Longitud_Maxima_Secuencia = 10

Modelo_Voz = WhisperModel("tiny", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="int8")

# Cargar modelo PyTorch
if os.path.exists(config.Ruta_Modelo_Pytorch):
    try:
        data_model = torch.load(config.Ruta_Modelo_Pytorch, map_location=Dispositivo, weights_only=False)
        Modelo_IA = NeuralNet(
            data_model["input_size"],
            data_model["hidden_size"],
            data_model["output_size"]
        ).to(Dispositivo)
        Modelo_IA.load_state_dict(data_model["model_state"])
        Modelo_IA.eval()
        Todas_Las_Palabras = data_model["all_words"]
        Etiquetas_De_Intencion = data_model["tags"]
        Longitud_Maxima_Secuencia = data_model.get("max_length", 10)
        print("[OK] Modelo PyTorch cargado.")
    except Exception as e:
        print(f"[ERROR] Modelo .pth: {e}")
else:
    print("[WARN] No se encontro model.pth. Ejecuta train_pytorch.py primero.")

# Cargar intents
with open(config.Ruta_Intents, 'r', encoding='utf-8') as f:
    Datos_De_Intents = json.load(f)

def Construir_Secuencia(Palabras_Tokenizadas, Vocabulario_Total, Longitud_Maxima):
    Indice_Vocabulario = {palabra: indice for indice, palabra in enumerate(Vocabulario_Total)}
    Secuencia = []
    for Palabra in Palabras_Tokenizadas:
        indice = Indice_Vocabulario.get(Palabra)
        if indice is not None:
            Secuencia.append(indice)

    if len(Secuencia) < Longitud_Maxima:
        Secuencia.extend([0] * (Longitud_Maxima - len(Secuencia)))
    else:
        Secuencia = Secuencia[:Longitud_Maxima]

    return np.array(Secuencia, dtype=np.int64)

def Predecir_Tag(Texto_Consulta):
    """Usa el modelo PyTorch LSTM para predecir el tag de una oración."""
    if not Modelo_IA:
        return None, 0.0, 0.0

    Palabras = Tokenizar_Texto(Texto_Consulta)
    Vector_Entrada = Construir_Secuencia(Palabras, Todas_Las_Palabras, Longitud_Maxima_Secuencia)
    Vector_Entrada = Vector_Entrada.reshape(1, Vector_Entrada.shape[0])
    Vector_Entrada = torch.from_numpy(Vector_Entrada).to(Dispositivo)

    Salida_Modelo = Modelo_IA(Vector_Entrada)
    _, Indice_Predicho = torch.max(Salida_Modelo, dim=1)
    Etiqueta_Predicha = Etiquetas_De_Intencion[Indice_Predicho.item()]

    Probabilidades = torch.softmax(Salida_Modelo, dim=1)
    Probabilidades_Top = torch.topk(Probabilidades, k=min(2, Probabilidades.shape[1]), dim=1)
    Confianza_Predicha = Probabilidades_Top.values[0][0].item()
    Confianza_Segunda = Probabilidades_Top.values[0][1].item() if Probabilidades.shape[1] > 1 else 0.0
    Margen_De_Confianza = Confianza_Predicha - Confianza_Segunda

    return Etiqueta_Predicha, Confianza_Predicha, Margen_De_Confianza
