## Estado Actual
- Whisper eliminado completamente del proyecto.
- Entorno virtual `venv` recreado e instalado con `requirements.txt` actualizado.
- Modelo spaCy `es_core_news_sm` descargado e instalado.
- `app.py` carga sin errores tras la limpieza.

## Tareas Completadas
- Eliminado todo rastro de Whisper:
  - `requirements.txt`: removidas `faster-whisper`, `PyQt5`, `sounddevice`, `soundfile`.
  - `bot/inteligencia_artificial.py`: eliminada función `Obtener_Modelo_Voz`, variables `Modelo_Voz`, `_Candado_De_Modelo_Voz`, import `threading` innecesario; actualizado docstring.
  - `app.py`: eliminada ruta `/transcribe`, import `Obtener_Modelo_Voz`, import `tempfile`.
  - `js/interfaz_principal.js`: eliminadas funciones `Enviar_Audio_A_Whisper`, `Iniciar_Grabacion_Con_Whisper`, variables `Grabadora_De_Medios`, `Segmentos_De_Audio`; simplificado listener del micrófono a solo reconocimiento nativo del navegador.
  - `documentacion_arquitectura.html`: actualizada descripción de `inteligencia_artificial.py` y flujo de voz para reflejar reconocimiento nativo del navegador.
- `venv` recreado (anterior renombrado a `venv_old`) e instaladas dependencias limpias.
- Descargado modelo spaCy `es_core_news_sm`.

## Tareas Completadas
- `panel_administracion.html`:
  - Eliminado `<select id="prod-activo">` del modal; ajustado JS `guardarProducto` para calcular `activo` desde `stock`; tabla de productos usa `estaActivo = p.stock > 0`; badge cambia a "Desactivado" cuando stock es 0.
  - Eliminado listener que cerraba modal al clic fuera.
  - Agregado botón `.modal-close` [X] arriba a la derecha en ambos modales.
  - Cambiado botón Cancelar a clase `btn-danger` (rojo) en ambos modales.
  - Agregado flag `window._guardandoProducto` / `window._guardandoCategoria` para prevenir doble envío.
- `admin/panel_administracion.py`:
  - En `Admin_Crear_Producto` se calcula `activo = 1 if stock > 0 else 0`.
  - En `Admin_Actualizar_Producto` se deriva `activo` automáticamente cuando se envía `stock`.

