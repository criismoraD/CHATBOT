## Estado
- Repositorio listo.
- Archivos descargados de main.

## Completado
- Endurecido el filtro por color usando color principal (backend y frontend) para evitar que se cuelen productos por colores secundarios.
- Mapeados sinónimos "vestido(s)" y "falda(s)" a PANTALONES para evitar desvíos a OTROS en filtros por chat.
- Agregado botón "Reiniciar filtros" con reseteo completo de categoría, color, género, precio y búsqueda.
- Soportado reinicio de filtros también por chat con frases tipo "mostrar todos" o "reiniciar filtros".
- Añadida normalización heurística de categoría por nombre del producto en frontend y backend para corregir registros mal clasificados (ej. mochilas fuera de OTROS).
- Rehabilitado filtro interno por keywords desde chat (sin escribir en el buscador) para refinar casos como "mochilas rojas" dentro de categorías amplias.
- Depurada extracción de keywords del backend para ignorar saludos y reducir ruido semántico en resultados filtrados.
- Restringido el chat para no escribir en el buscador: ahora solo aplica filtros estructurados y respeta el texto ingresado manualmente.
- Aclarado placeholder del buscador para indicar que filtra por nombre, color y descripción del catálogo.
- Corregido contraste del buscador principal: texto del input en negro y placeholder gris sobre fondo blanco.
- Mejorada la búsqueda del catálogo con coincidencia por tokens y variantes (plural/singular y sinónimos básicos como zapatilla/calzado/tenis).
- Ajustado color de texto del chat-input a negro para contraste sobre fondo blanco y placeholder a gris legible.
- Consolidada carpeta `Herramientas` con scripts de soporte y tests.
- Renombrados archivos a Pascal_Snake_Case (`Scrape_Productos.py`, `Utils_Inventario.py`, etc.).
- Corregidos imports y rutas para compatibilidad con nueva estructura.
- Parcheado CORS en app.py para resolver bloqueo de frontend.

## Pendiente
- Revisar app.py y requerimientos.
- Pruebas de funcionamiento.

## Resumen Antiguo
- [16/04] Refactorización Imprimir_Resumen y creación utils_inventario.py.
- [16/04] Consolidación train_pytorch.py y actualización requirements.txt.
- [16/04] Integración faster-whisper y soporte MediaRecorder.
- [15/04] Mejoras en app.py: umbrales, persistencia y contexto.
- [Anterior] Entrenamiento NLP (F1 0.799) y mejoras UX frontend.