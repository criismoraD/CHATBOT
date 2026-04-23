import sys
import os
import tempfile
import threading

# Añadimos el directorio base para poder importar desde el backend local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# IMPORTANTE: Importar torch/dialogo ANTES que PyQt5 para evitar WinError 1114 en Windows
import torch
from dialogo import Obtener_Respuesta_Principal
from catalogo import Buscar_Productos, Obtener_Producto_Por_Id, Obtener_Colores_De_Producto, Obtener_Detalle_De_Inventario, Datos_De_Productos
from ia import Modelo_Voz

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QLabel, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPainterPath, QLinearGradient


# ─────────────────────────────────────────────
# SEÑALES PARA COMUNICAR HILOS CON LA GUI
# ─────────────────────────────────────────────
class WorkerSignals(QObject):
    bot_response = pyqtSignal(str, str, object)  # respuesta, etiqueta, filtros
    voice_result = pyqtSignal(str)  # texto transcrito
    voice_error = pyqtSignal(str)


# ─────────────────────────────────────────────
# CONSTANTES DE ESTILO
# ─────────────────────────────────────────────
COLOR_BG = "#0b141a"
COLOR_HEADER = "#1f2c34"
COLOR_INPUT_BAR = "#1f2c34"
COLOR_USER_BUBBLE = "#005c4b"
COLOR_BOT_BUBBLE = "#1a2730"
COLOR_TEXT = "#e9edef"
COLOR_TEXT_DIM = "#8696a0"
COLOR_ACCENT = "#00a884"
COLOR_ACCENT_HOVER = "#02cc9e"
COLOR_DANGER = "#ef4444"
COLOR_CARD_BG = "#1a2730"
COLOR_CARD_BORDER = "#2a3942"

FONT_FAMILY = "Segoe UI"


# ─────────────────────────────────────────────
# MAPA DE SUGERENCIAS CONTEXTUALES POR TAG
# ─────────────────────────────────────────────
def Obtener_Sugerencias_Por_Tag(tag, filtros=None):
    """Retorna una lista de hasta 3 botones de sugerencia según el tag de la respuesta."""
    sugerencias_base = {
        "saludo": [
            "👟 Recomiéndame zapatillas",
            "👕 Muéstrame polos",
            "👖 Quiero ver pantalones",
        ],
        "despedida": [],
        "buscar_producto": [
            "💰 ¿Cuánto cuesta?",
            "📏 ¿Qué tallas hay?",
            "🎨 ¿En qué colores viene?",
        ],
        "filtrar_categoria": [
            "🔴 Muéstrame en color rojo",
            "👫 Productos para mujer",
            "💲 Los más baratos",
        ],
        "filtrar_genero": [
            "👟 Recomiéndame zapatillas",
            "👕 Muéstrame polos",
            "💰 ¿Cuáles son los precios?",
        ],
        "consulta_precio": [
            "📏 ¿Qué tallas tienen?",
            "🎨 ¿En qué colores viene?",
            "🛒 Quiero comprar",
        ],
        "consultar_precio_item": [
            "📏 ¿Qué tallas tiene?",
            "🎨 ¿En qué colores viene?",
            "👟 Recomiéndame otros productos",
        ],
        "consultar_stock_item": [
            "💰 ¿Cuánto cuesta?",
            "🎨 ¿Qué colores hay?",
            "👟 Muéstrame más productos",
        ],
        "colores": [
            "👟 Recomiéndame zapatillas",
            "💰 ¿Cuánto cuestan?",
            "📏 ¿Qué tallas hay?",
        ],
        "pedidos": [
            "📞 Información de tienda",
            "👟 Recomiéndame un producto",
            "❓ Necesito ayuda",
        ],
        "informacion_tienda": [
            "👟 Recomiéndame zapatillas",
            "👕 Muéstrame polos",
            "📞 Reclamos o ayuda",
        ],
        "reclamos": [
            "📞 Info de la tienda",
            "👟 Recomiéndame un producto",
            "👋 Hasta luego",
        ],
        "promociones": [
            "👟 Recomiéndame zapatillas",
            "👕 Muéstrame polos",
            "💰 Precios",
        ],
        "disponibilidad": [
            "💰 ¿Cuánto cuesta?",
            "🎨 ¿Qué colores hay?",
            "👟 Recomiéndame otros",
        ],
        "agradecimiento": [
            "👟 Quiero seguir comprando",
            "📞 Info de tienda",
            "👋 Hasta luego",
        ],
        "fuera_de_dominio": [
            "👟 Recomiéndame zapatillas",
            "👕 Muéstrame polos",
            "❓ ¿Qué puedes hacer?",
        ],
    }

    sugerencias = sugerencias_base.get(tag, [
        "👟 Recomiéndame zapatillas",
        "👕 Muéstrame polos",
        "❓ Ayuda",
    ])

    return sugerencias[:3]


def Adaptar_Respuesta_Para_Desktop(texto):
    """Reemplaza referencias a 'catálogo' / 'arriba' que no aplican en la app de escritorio."""
    reemplazos = [
        ("Te los muestro en el catálogo", "Te los muestro aquí"),
        ("te los muestro en el catálogo", "te los muestro aquí"),
        ("Ya te los muestro en el catálogo", "Aquí te los muestro"),
        ("Ya te los dejé en el catálogo", "Aquí te los dejo"),
        ("Revisa el catalogo arriba", "Aquí te los muestro"),
        ("Revisa el catalogo", "Aquí están"),
        ("revisa el catalogo", "aquí están"),
        ("Mira los resultados filtrados arriba", "Te los muestro aquí abajo"),
        ("Échales un vistazo arriba", "Échalos un vistazo aquí"),
        ("Explora las opciones.", "Aquí están las opciones."),
        ("Desliza por el catálogo para verlos", "Aquí te los muestro"),
        ("catálogo actualizado", "aquí están los resultados"),
        ("catalogo", "chat"),
        ("Catálogo", "Chat"),
    ]
    resultado = texto
    for buscar, reemplazar in reemplazos:
        resultado = resultado.replace(buscar, reemplazar)
    return resultado


# ─────────────────────────────────────────────
# WIDGET: TARJETA DE PRODUCTO EN EL CHAT
# ─────────────────────────────────────────────
class ProductCard(QFrame):
    """Tarjeta compacta de producto que se muestra dentro del chat."""
    consultar_clicked = pyqtSignal(int)  # product_id

    def __init__(self, producto, parent=None):
        super().__init__(parent)
        self.producto = producto
        self.setFixedWidth(300)
        self.setStyleSheet(f"""
            ProductCard {{
                background-color: {COLOR_CARD_BG};
                border: 1px solid {COLOR_CARD_BORDER};
                border-radius: 12px;
                margin: 3px 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Nombre del producto
        nombre = QLabel(producto.get("name", "Producto"))
        nombre.setWordWrap(True)
        nombre.setStyleSheet(f"color: {COLOR_TEXT}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(nombre)

        # Categoría + Género
        cat = producto.get("category", "")
        genero = producto.get("genero", "Unisex")
        emoji_map = {"CALZADO": "👟", "POLOS": "👕", "PANTALONES": "👖", "OTROS": "🎒"}
        emoji = emoji_map.get(cat, "✨")
        meta = QLabel(f"{emoji} {cat}  •  {genero}")
        meta.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(meta)

        # Precio
        precio = producto.get("price")
        if isinstance(precio, (int, float)):
            precio_label = QLabel(f"S/ {precio:.2f}")
            precio_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: bold; font-size: 15px; background: transparent; border: none;")
            layout.addWidget(precio_label)

        # Colores
        colores = Obtener_Colores_De_Producto(producto)
        if colores:
            colores_label = QLabel(f"🎨 {', '.join(colores)}")
            colores_label.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; background: transparent; border: none;")
            layout.addWidget(colores_label)

        # Tallas
        tallas = producto.get("tallas", [])
        if tallas:
            tallas_label = QLabel(f"📏 Tallas: {', '.join(tallas)}")
            tallas_label.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; background: transparent; border: none;")
            tallas_label.setWordWrap(True)
            layout.addWidget(tallas_label)

        # Stock
        stock = producto.get("stock")
        if isinstance(stock, (int, float)):
            stock_label = QLabel(f"📦 Stock: {int(stock)} unidades")
            stock_label.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; background: transparent; border: none;")
            layout.addWidget(stock_label)

        # Botón "Consultar"
        btn_consultar = QPushButton("💬 Consultar este producto")
        btn_consultar.setCursor(Qt.PointingHandCursor)
        btn_consultar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: #111b21;
                border: none;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
                margin-top: 5px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
        """)
        btn_consultar.clicked.connect(lambda: self.consultar_clicked.emit(producto.get("id")))
        layout.addWidget(btn_consultar)


# ─────────────────────────────────────────────
# WIDGET: BURBUJA DE CHAT
# ─────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(8, 2, 8, 2)
        self.setLayout(self.main_layout)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.label.setMaximumWidth(320)

        if is_user:
            self.label.setStyleSheet(f"""
                background-color: {COLOR_USER_BUBBLE};
                color: #ffffff;
                border-radius: 14px;
                border-bottom-right-radius: 4px;
                padding: 10px 14px;
                font-size: 13px;
            """)
            self.main_layout.addStretch()
            self.main_layout.addWidget(self.label)
        else:
            self.label.setStyleSheet(f"""
                background-color: {COLOR_BOT_BUBBLE};
                color: {COLOR_TEXT};
                border-radius: 14px;
                border-bottom-left-radius: 4px;
                padding: 10px 14px;
                font-size: 13px;
            """)
            self.main_layout.addWidget(self.label)
            self.main_layout.addStretch()


# ─────────────────────────────────────────────
# WIDGET: BOTONES DE SUGERENCIA DEBAJO DEL MSG
# ─────────────────────────────────────────────
class SuggestionRow(QFrame):
    """Fila de botones de sugerencia que aparece debajo de un mensaje del bot."""
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, suggestions, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 4)
        layout.setSpacing(6)

        for text in suggestions:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_ACCENT};
                    border: 1px solid {COLOR_ACCENT};
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_ACCENT};
                    color: #111b21;
                }}
            """)
            btn.clicked.connect(lambda checked, t=text: self.suggestion_clicked.emit(t))
            layout.addWidget(btn)

        layout.addStretch()


# ─────────────────────────────────────────────
# VENTANA PRINCIPAL DEL CHATBOT
# ─────────────────────────────────────────────
class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_id = "pyqt_user_local"
        self.setWindowTitle("Asistente Virtual - SENATI SPORTS")
        self.resize(650, 650)
        self.setMinimumSize(500, 500)
        self.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_TEXT};")

        font = QFont(FONT_FAMILY, 10)
        QApplication.setFont(font)

        self.signals = WorkerSignals()
        self.signals.bot_response.connect(self._on_bot_response)
        self.signals.voice_result.connect(self._on_voice_result)
        self.signals.voice_error.connect(self._on_voice_error)

        self.is_recording = False
        self.current_suggestion_row = None  # Track last suggestion row to disable old ones

        self._build_ui()

        # Mensaje de bienvenida con sugerencias
        self._add_bot_message(
            "¡Hola! 👋 Soy tu asistente virtual de SENATI SPORTS.\n\n"
            "Puedo ayudarte a buscar productos, consultar precios, tallas, colores y mucho más.\n\n"
            "¿En qué te ayudo hoy?",
            tag="saludo"
        )

    def _build_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── HEADER ──
        self.header = QFrame()
        self.header.setFixedHeight(65)
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_HEADER};
                border-bottom: 1px solid #2a3942;
            }}
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        # Avatar circular
        avatar = QLabel("🤖")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"""
            background-color: {COLOR_ACCENT};
            border-radius: 20px;
            font-size: 20px;
        """)
        header_layout.addWidget(avatar)

        # Info del bot
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        title = QLabel("Asistente SENATI SPORTS")
        title.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 15px; font-weight: bold;")
        status = QLabel("🟢 En línea")
        status.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px;")
        info_layout.addWidget(title)
        info_layout.addWidget(status)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        # Botón Nuevo Chat
        self.clear_btn = QPushButton("🧹 Nuevo chat")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_DIM};
                border: 1px solid {COLOR_TEXT_DIM};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2a3942;
                color: {COLOR_TEXT};
            }}
        """)
        self.clear_btn.clicked.connect(self.clear_chat)
        header_layout.addWidget(self.clear_btn)

        self.main_layout.addWidget(self.header)

        # ── SCROLL AREA (MENSAJES) ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: {COLOR_BG}; }}
            QScrollBar:vertical {{
                border: none;
                background: {COLOR_BG};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: #374045;
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.messages_container = QWidget()
        self.messages_container.setStyleSheet(f"background-color: {COLOR_BG};")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(2)
        self.messages_layout.setContentsMargins(4, 8, 4, 8)

        self.scroll_area.setWidget(self.messages_container)
        self.main_layout.addWidget(self.scroll_area)

        # ── BARRA DE ENTRADA ──
        self.input_bar = QFrame()
        self.input_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_INPUT_BAR};
                border-top: 1px solid #2a3942;
            }}
        """)
        input_layout = QHBoxLayout(self.input_bar)
        input_layout.setContentsMargins(10, 8, 10, 10)
        input_layout.setSpacing(8)

        # Botón micrófono (toggle: clic para grabar, clic para detener y enviar)
        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(42, 42)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setToolTip("Clic para grabar, clic de nuevo para enviar")
        self._set_mic_style(recording=False)
        self.mic_btn.clicked.connect(self._toggle_recording)
        input_layout.addWidget(self.mic_btn)

        # Campo de entrada
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe un mensaje...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2a3942;
                color: {COLOR_TEXT};
                border-radius: 21px;
                padding: 10px 18px;
                font-size: 14px;
                border: none;
                selection-background-color: {COLOR_ACCENT};
            }}
            QLineEdit::placeholder {{
                color: {COLOR_TEXT_DIM};
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        # Botón enviar
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(42, 42)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: #111b21;
                border-radius: 21px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #2a3942;
                color: {COLOR_TEXT_DIM};
            }}
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        self.main_layout.addWidget(self.input_bar)

    # ── ESTILOS DEL MICRÓFONO ──
    def _set_mic_style(self, recording=False):
        if recording:
            self.mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_DANGER};
                    border-radius: 21px;
                    font-size: 18px;
                    border: 2px solid #ff6b6b;
                }}
            """)
            self.mic_btn.setText("⏹️")
            self.mic_btn.setToolTip("Grabando... Clic para detener y enviar")
        else:
            self.mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a3942;
                    border-radius: 21px;
                    font-size: 18px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #3a4952;
                }}
            """)
            self.mic_btn.setText("🎙️")
            self.mic_btn.setToolTip("Clic para grabar audio")

    # ── GRABACIÓN DE VOZ (TOGGLE) ──
    def _toggle_recording(self):
        """Primer clic inicia la grabación, segundo clic la detiene y envía."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self.is_recording = True
        self._set_mic_style(recording=True)
        self.audio_frames = []

        try:
            import sounddevice as sd
            self.sample_rate = 16000
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                callback=self._audio_callback
            )
            self.audio_stream.start()
        except ImportError:
            self._add_bot_message(
                "⚠️ Para usar el micrófono necesitas instalar 'sounddevice':\n\npip install sounddevice",
                tag="fuera_de_dominio"
            )
            self.is_recording = False
            self._set_mic_style(recording=False)
        except Exception as e:
            self._add_bot_message(f"⚠️ Error al iniciar el micrófono: {str(e)}", tag="fuera_de_dominio")
            self.is_recording = False
            self._set_mic_style(recording=False)

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_recording:
            self.audio_frames.append(indata.copy())

    def _stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self._set_mic_style(recording=False)

        try:
            self.audio_stream.stop()
            self.audio_stream.close()
        except Exception:
            pass

        if not self.audio_frames:
            return

        # Procesar en un hilo para no bloquear la GUI
        import numpy as np
        audio_data = np.concatenate(self.audio_frames, axis=0)

        self._add_user_message("🎙️ [Audio enviado...]")
        self._show_typing()

        def transcribe_worker():
            try:
                import soundfile as sf
                tmp_path = os.path.join(tempfile.gettempdir(), "senati_voice_tmp.wav")
                sf.write(tmp_path, audio_data, self.sample_rate)

                segments, _ = Modelo_Voz.transcribe(tmp_path, beam_size=5)
                texto = " ".join([s.text for s in segments]).strip()

                os.remove(tmp_path)

                if texto:
                    self.signals.voice_result.emit(texto)
                else:
                    self.signals.voice_error.emit("No se pudo entender el audio. Intenta de nuevo.")
            except Exception as e:
                self.signals.voice_error.emit(f"Error al procesar audio: {str(e)}")

        thread = threading.Thread(target=transcribe_worker, daemon=True)
        thread.start()

    def _on_voice_result(self, texto):
        self._remove_typing()
        self._add_user_message(f"🎙️ {texto}")
        self._process_message(texto)

    def _on_voice_error(self, error_msg):
        self._remove_typing()
        self._add_bot_message(f"⚠️ {error_msg}", tag="fuera_de_dominio")

    # ── ENVÍO DE MENSAJES ──
    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self._add_user_message(text)
        self.input_field.clear()
        self._process_message(text)

    def _process_message(self, text):
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self._show_typing()

        def worker():
            try:
                respuesta, etiqueta, filtros = Obtener_Respuesta_Principal(self.session_id, text)

                # Buscar productos relacionados para mostrar como sugerencias
                productos_relacionados = []
                tags_con_productos = {
                    "buscar_producto", "filtrar_categoria", "filtrar_genero",
                    "consulta_precio", "disponibilidad"
                }

                if etiqueta in tags_con_productos and isinstance(filtros, dict):
                    # Usar los filtros para buscar productos y mostrarlos en el chat
                    product_ids = filtros.get("product_ids", [])
                    if product_ids:
                        for pid in product_ids[:4]:
                            prod = Obtener_Producto_Por_Id(pid)
                            if prod:
                                productos_relacionados.append(prod)
                    else:
                        # Buscar directamente con los filtros del bot
                        productos_relacionados = Buscar_Productos(
                            Categoria=filtros.get("category"),
                            Color=filtros.get("color"),
                            Precio_Maximo=filtros.get("max_price"),
                            Talla=filtros.get("talla"),
                            Genero=filtros.get("genero"),
                            Palabras_Clave=filtros.get("keywords"),
                            Limite=4,
                        )

                # Adaptar texto del bot para la app de escritorio
                respuesta_adaptada = Adaptar_Respuesta_Para_Desktop(respuesta or "No pude procesar tu consulta.")

                self.signals.bot_response.emit(
                    respuesta_adaptada,
                    etiqueta or "fuera_de_dominio",
                    productos_relacionados  # Ahora pasamos la lista de productos directamente
                )
            except Exception as e:
                self.signals.bot_response.emit(
                    f"Error interno: {str(e)}",
                    "fuera_de_dominio",
                    None
                )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_bot_response(self, respuesta, etiqueta, productos_relacionados):
        self._remove_typing()

        # Mostrar productos relacionados/sugeridos como tarjetas en el chat
        tiene_productos = productos_relacionados and isinstance(productos_relacionados, list) and len(productos_relacionados) > 0

        if tiene_productos:
            # Respuesta natural antes de mostrar las tarjetas
            import random
            cantidad = len(productos_relacionados[:4])
            if cantidad == 1:
                intros = [
                    "¡Claro! Aquí te muestro una opción que encontré:",
                    "¡Mira! Esto es lo que tengo para ti:",
                    "¡Perfecto! Te encontré justo esto:",
                ]
            else:
                intros = [
                    f"¡Claro! Aquí te muestro {cantidad} opciones que encontré:",
                    f"¡Mira lo que tengo! Te encontré {cantidad} opciones:",
                    f"¡Genial! Encontré {cantidad} productos que te pueden gustar:",
                    f"¡Dale un vistazo! Estas son {cantidad} opciones para ti:",
                ]
            self._add_bot_message(random.choice(intros), tag=etiqueta)

            for producto in productos_relacionados[:4]:
                self._add_product_card(producto)

            if len(productos_relacionados) > 4:
                nota_bubble = ChatBubble(
                    f"✨ Hay más opciones disponibles, solo pídeme que te muestre más.",
                    is_user=False
                )
                self.messages_layout.addWidget(nota_bubble)
        else:
            self._add_bot_message(respuesta, tag=etiqueta)

        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input_field.setFocus()
        self._scroll_down()

    # ── AGREGAR ELEMENTOS AL CHAT ──
    def _add_user_message(self, text):
        # Deshabilitar botones de sugerencias anteriores
        self._disable_old_suggestions()
        bubble = ChatBubble(text, is_user=True)
        self.messages_layout.addWidget(bubble)
        self._scroll_down()

    def _add_bot_message(self, text, tag="saludo"):
        bubble = ChatBubble(text, is_user=False)
        self.messages_layout.addWidget(bubble)

        # Agregar sugerencias debajo del mensaje del bot
        sugerencias = Obtener_Sugerencias_Por_Tag(tag)
        if sugerencias:
            self._disable_old_suggestions()
            row = SuggestionRow(sugerencias)
            row.suggestion_clicked.connect(self._on_suggestion_clicked)
            self.current_suggestion_row = row
            self.messages_layout.addWidget(row)

        self._scroll_down()

    def _add_product_card(self, producto):
        card_wrapper = QHBoxLayout()
        card = ProductCard(producto)
        card.consultar_clicked.connect(self._on_product_consult)
        card_wrapper_widget = QWidget()
        card_wrapper = QHBoxLayout(card_wrapper_widget)
        card_wrapper.setContentsMargins(8, 2, 8, 2)
        card_wrapper.addWidget(card)
        card_wrapper.addStretch()
        self.messages_layout.addWidget(card_wrapper_widget)

    def _disable_old_suggestions(self):
        """Desactiva visualmente los botones de sugerencia anteriores."""
        if self.current_suggestion_row:
            for btn in self.current_suggestion_row.findChildren(QPushButton):
                btn.setEnabled(False)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLOR_TEXT_DIM};
                        border: 1px solid #2a3942;
                        border-radius: 14px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }}
                """)
            self.current_suggestion_row = None

    def _on_suggestion_clicked(self, text):
        # Limpiar el emoji del inicio del texto para enviarlo limpio al motor NLP
        clean_text = text
        # Quitar emojis comunes al inicio
        for prefix in ["👟 ", "👕 ", "👖 ", "🎒 ", "💰 ", "📦 ", "🎨 ", "🛒 ", "📞 ", "🔍 ", "👫 ", "💲 ", "🔙 ", "❓ ", "👋 "]:
            if clean_text.startswith(prefix):
                clean_text = clean_text[len(prefix):]
                break

        self._add_user_message(text)
        self._process_message(clean_text)

    def _on_product_consult(self, product_id):
        producto = Obtener_Producto_Por_Id(product_id)
        if not producto:
            self._add_bot_message("No encontré ese producto.", tag="fuera_de_dominio")
            return

        self._disable_old_suggestions()
        self._add_user_message(f"Quiero saber más sobre: {producto['name']}")

        # Mensaje natural + tarjeta del producto
        import random
        nombre = producto.get('name', 'este producto')
        intros = [
            f"¡Con mucho gusto! Aquí tienes toda la info de {nombre}:",
            f"¡Excelente elección! Te muestro los detalles de {nombre}:",
            f"¡Claro que sí! Aquí está la ficha completa de {nombre}:",
        ]
        self._add_bot_message(random.choice(intros), tag="consultar_precio_item")

        # Mostrar la tarjeta con toda la info
        self._add_product_card(producto)

        # Guardar contexto del producto para preguntas de seguimiento
        from memoria import Actualizar_Contexto
        Actualizar_Contexto(self.session_id, Id_De_Producto=product_id)

    # ── INDICADOR DE ESCRITURA ──
    def _show_typing(self):
        self.typing_label = QLabel("  ● ● ●")
        self.typing_label.setObjectName("typing_indicator")
        self.typing_label.setStyleSheet(f"""
            background-color: {COLOR_BOT_BUBBLE};
            color: {COLOR_TEXT_DIM};
            border-radius: 14px;
            border-bottom-left-radius: 4px;
            padding: 10px 16px;
            font-size: 16px;
            font-weight: bold;
            max-width: 80px;
            margin-left: 8px;
        """)
        self.typing_label.setFixedWidth(80)
        self.messages_layout.addWidget(self.typing_label)
        self._scroll_down()

        # Animación simple de puntos
        self._typing_state = 0
        self._typing_timer = QTimer()
        self._typing_timer.timeout.connect(self._animate_typing)
        self._typing_timer.start(400)

    def _animate_typing(self):
        states = ["  ●      ", "  ● ●   ", "  ● ● ●"]
        self._typing_state = (self._typing_state + 1) % len(states)
        if hasattr(self, 'typing_label') and self.typing_label:
            self.typing_label.setText(states[self._typing_state])

    def _remove_typing(self):
        if hasattr(self, '_typing_timer'):
            self._typing_timer.stop()
        if hasattr(self, 'typing_label') and self.typing_label:
            self.typing_label.setParent(None)
            self.typing_label.deleteLater()
            self.typing_label = None

    # ── SCROLL ──
    def _scroll_down(self):
        QTimer.singleShot(60, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))


    # ── EVENTOS EXTRA ──
    def clear_chat(self):
        """Reinicia el historial visual y el contexto del backend."""
        self.current_suggestion_row = None
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Limpiar memoria del bot
        try:
            from memoria import Limpiar_Contexto
            Limpiar_Contexto(self.session_id)
        except Exception as e:
            print("Error al limpiar contexto:", e)

        # Volver a saludar
        self._add_bot_message(
            "¡Hola! 👋 Soy tu asistente virtual de SENATI SPORTS.\n\n"
            "Puedo ayudarte a buscar productos, consultar precios, tallas, colores y mucho más.\n\n"
            "¿En qué te ayudo hoy?",
            tag="saludo"
        )

# ─────────────────────────────────────────────
# LANZAR APLICACIÓN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())
