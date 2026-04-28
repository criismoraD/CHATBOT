"""
bot/ia.py  ·  Módulo de Inteligencia Artificial
------------------------------------------------
Carga el modelo PyTorch LSTM y el modelo Whisper para voz.
Expone funciones de predicción de intención y transcripción de audio.
"""

import os
import json
import threading
import torch
import numpy as np
from entrenar_modelo_lstm import NeuralNet
from core import config
from core.nlp import Tokenizar_Y_Lematizar


# ─── Estado Global del Módulo ────────────────────────────────────────────────

_Dispositivo = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
Modelo_IA = None
Modelo_Voz = None
Todas_Las_Palabras = []
Etiquetas_De_Intencion = []
Longitud_Maxima_Secuencia = 10
_Candado_De_Modelo_Voz = threading.Lock()


# ─── Modelo de Voz (Whisper) ─────────────────────────────────────────────────

def Obtener_Modelo_Voz():
    """Carga el modelo Whisper bajo demanda (thread-safe)."""
    global Modelo_Voz
    if Modelo_Voz is None:
        with _Candado_De_Modelo_Voz:
            if Modelo_Voz is None:
                from faster_whisper import WhisperModel
                Modelo_Voz = WhisperModel(
                    "base",
                    device="cuda" if torch.cuda.is_available() else "cpu",
                    compute_type="int8"
                )
                print("[OK] Modelo Whisper cargado bajo demanda.")
    return Modelo_Voz


# ─── Carga del Modelo PyTorch ────────────────────────────────────────────────

def _Cargar_Modelo_Pytorch():
    """Carga el modelo LSTM desde el archivo .pth si existe."""
    global Modelo_IA, Todas_Las_Palabras, Etiquetas_De_Intencion, Longitud_Maxima_Secuencia

    if not os.path.exists(config.Ruta_Modelo_Pytorch):
        print("[WARN] No se encontro model.pth. Ejecuta entrenar_modelo_lstm.py primero.")
        return

    try:
        Datos_Del_Modelo = torch.load(
            config.Ruta_Modelo_Pytorch,
            map_location=_Dispositivo,
            weights_only=True
        )
        Dimension_Embedding = Datos_Del_Modelo.get("embedding_dim", 128)

        Modelo_IA = NeuralNet(
            Datos_Del_Modelo["input_size"],
            Datos_Del_Modelo["hidden_size"],
            Datos_Del_Modelo["output_size"],
            embedding_dim=Dimension_Embedding,
        ).to(_Dispositivo)

        Modelo_IA.load_state_dict(Datos_Del_Modelo["model_state"])
        Modelo_IA.eval()

        Todas_Las_Palabras = Datos_Del_Modelo["all_words"]
        Etiquetas_De_Intencion = Datos_Del_Modelo["tags"]
        Longitud_Maxima_Secuencia = Datos_Del_Modelo.get("max_length", 10)

        print("[OK] Modelo PyTorch cargado.")
    except Exception as Error_De_Carga:
        print(f"[ERROR] Modelo .pth: {Error_De_Carga}")


_Cargar_Modelo_Pytorch()


# ─── Carga de Intents ────────────────────────────────────────────────────────

with open(config.Ruta_Intents, 'r', encoding='utf-8') as _Archivo:
    Datos_De_Intents = json.load(_Archivo)


# ─── Funciones de Predicción ─────────────────────────────────────────────────

def _Construir_Secuencia(Palabras_Tokenizadas, Vocabulario_Total, Longitud_Maxima):
    """Convierte tokens a índices numéricos con padding para el modelo."""
    Indice_Vocabulario = {Palabra: Indice for Indice, Palabra in enumerate(Vocabulario_Total)}
    Secuencia = []
    for Palabra in Palabras_Tokenizadas:
        Indice = Indice_Vocabulario.get(Palabra)
        if Indice is not None:
            Secuencia.append(Indice)

    if len(Secuencia) < Longitud_Maxima:
        Secuencia.extend([0] * (Longitud_Maxima - len(Secuencia)))
    else:
        Secuencia = Secuencia[:Longitud_Maxima]

    return np.array(Secuencia, dtype=np.int64)


def Predecir_Tag(Texto_Consulta):
    """
    Usa el modelo LSTM para predecir la intención (tag) de un mensaje.
    Retorna: (etiqueta, confianza, margen_de_confianza)
    """
    if not Modelo_IA:
        return None, 0.0, 0.0

    Palabras = Tokenizar_Y_Lematizar(Texto_Consulta)
    Vector_Entrada = _Construir_Secuencia(Palabras, Todas_Las_Palabras, Longitud_Maxima_Secuencia)
    Longitud_Real = max(1, int(np.count_nonzero(Vector_Entrada)))

    Vector_Entrada = Vector_Entrada.reshape(1, Vector_Entrada.shape[0])
    Tensor_Entrada = torch.from_numpy(Vector_Entrada).to(_Dispositivo)
    Tensor_Longitud = torch.tensor([Longitud_Real], dtype=torch.long, device=_Dispositivo)

    Salida = Modelo_IA(Tensor_Entrada, Tensor_Longitud)
    _, Indice_Predicho = torch.max(Salida, dim=1)
    Etiqueta_Predicha = Etiquetas_De_Intencion[Indice_Predicho.item()]

    Probabilidades = torch.softmax(Salida, dim=1)
    Top_Probabilidades = torch.topk(Probabilidades, k=min(2, Probabilidades.shape[1]), dim=1)

    Confianza = Top_Probabilidades.values[0][0].item()
    Confianza_Segunda = Top_Probabilidades.values[0][1].item() if Probabilidades.shape[1] > 1 else 0.0
    Margen = Confianza - Confianza_Segunda

    return Etiqueta_Predicha, Confianza, Margen
