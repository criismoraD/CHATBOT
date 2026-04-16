## Tareas Completadas

- Historial técnico comprimido para optimizar tokens.
- Se implementaron filtros y mejoras de UX en el frontend (categoría, género, precio, tallas ocultas).
- Se entrenó el modelo NLP con intents balanceados usando PyTorch (accuracy 0.811, macro-F1 0.799).
- Se crearon y ajustaron scripts de scraping (`scrape_products.py`) para generar inventario automático.
- Se incorporaron opciones de memoria persistente en el backend (`app.py`) usando `shelve`.

- [2026-04-15] Calibración de inferencia en app.py (confianza + margen top1-top2).
- `app.py`: Predecir_Tag ahora devuelve etiqueta, confianza y margen de separación entre primera y segunda clase.
- `app.py`: agregados `Umbral_De_Margen_Base` y `Umbral_De_Margen_Por_Tag` para endurecer tags más ambiguos.
- `app.py`: la lógica de fallback por patrones ahora se activa por predicción ambigua, no solo por confianza.

- [2026-04-15] Corrección de fallos de chat reportados en pruebas visuales.
- `app.py`: mejorada la detección de producto por texto parcial con fallback ponderado por rareza de tokens.
- `app.py`: agregado manejo explícito de seguimiento de pedido.
- `app.py`: consulta de precio ahora prioriza precio exacto si ya existe producto en contexto.

- [2026-04-15] Corrección de persistencia de filtros y memoria conversacional.
- `app.py`: mejorada extracción de precio para frases naturales como "tengo 50 soles".
- `app.py`: herencia contextual de filtros entre mensajes cortos para mantener filtros en pasos.
- `app.py`: `filter_action` se devuelve incluso cuando no hay resultados.
- `app.py`: memoria del chat persistente en disco con `shelve`.
- `app.py`: limpieza de keywords de ruido de presupuesto.

- [2026-04-16] Limpieza de generación automática e implementación de voz.
- Eliminados `generate_products.py` y `data/products.json` del proyecto.
- Frontend (`index.html`, `js/main.js`) actualizado para remover los botones de selección de fuente de catálogo (auto/scraped) y utilizar por defecto los datos scrapeados.
- Backend (`app.py`) limpiado de variables (`Ruta_Productos_Automaticos`, `Fuentes_De_Catalogo_Validas`) y fallback asociado a generación automática.
- Integrado `faster-whisper` en `app.py` mediante un nuevo endpoint `/transcribe` para reconocimiento de voz usando el modelo "tiny".
- Implementado soporte de micrófono nativo en `js/main.js` usando `MediaRecorder` y envío del audio como WebM al backend para su transcripción y posterior inyección en el flujo del chat.
- Mejorada la inteligencia del bot para lidiar con el fuera de dominio, mediante el ajuste de `intents.json` e iteración sobre el fallback natural del bot.

- [2026-04-16] Actualización de dependencias.
- `requirements.txt`: Agregado `faster-whisper`.
- [2026-04-16] Consolidación de archivos de entrenamiento.
- model_arch.py y utils_texto.py combinados en train_pytorch.py.
- app.py modificado para importar tokenizar y NeuralNet directamente desde train_pytorch.py

- [2026-04-16] Mejora de salud del código: Refactorización de Imprimir_Resumen.
- Creado `utils_inventario.py` para centralizar utilidades de inventario y restaurar constantes perdidas por la eliminación de `generate_products.py`.
- `scrape_products.py`: Migrada la función `Imprimir_Resumen` a `utils_inventario.py` y actualizados los imports.
# Mejoras al modelo de intención (NLP)

- Se incrementaron los patrones de entrenamiento en data/intents.json (de ~600 a ~2000) para evitar sobreajuste y perfeccionar scores irreales.
- Se afinó train_pytorch.py (ajuste de learning rate, weight decay, tamaño oculto y control de BatchNorm) logrando estabilizar las validaciones por encima del umbral requerido de 0.8 de F1-score sin tocar el 1.0 artificial.
- Se actualizó el archivo de pruebas test_inventory.py para contemplar dependencias de Torch en los mocks.
