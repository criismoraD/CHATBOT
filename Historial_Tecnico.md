# Historial Técnico - Chatbot E-commerce SENATI

## Tareas Recientes (Detalladas)

- [24/04] **Rediseño: Layout de Dos Columnas (Catálogo + Chatbot):**
    - Eliminado el modo flotante (`position: fixed`) que tapaba productos.
    - Migrado el chatbot a una **columna derecha real** (`<aside class="dashboard-chat">`) dentro del layout flex de `.dashboard-app`.
    - `.dashboard-left` ocupa el ancho restante (`flex: 1`). `.dashboard-chat` tiene `width: 420px`, `position: sticky`, `top: 0`, `height: 100vh`.
    - El chatbot comparte el viewport con el catálogo sin superponerse; ambos tienen scroll independiente.
    - **Móvil (≤768px)**: la columna del chatbot se oculta por defecto. Se añade un botón flotante circular (`.mobile-chat-toggle`) con icono de robot que abre el chatbot como overlay a pantalla completa con fondo oscuro semitransparente.
    - Añadida lógica JS para abrir/cerrar el overlay móvil al tocar el botón o el fondo.
    - **Paginación**: cambiado `Cantidad_A_Mostrar` de 12 a **14** productos iniciales y de carga por clic en "Cargar más".

- [23/04] **Chatbot integrado en el mismo panel del catálogo (no sidebar):**
    - Eliminado el sidebar derecho (`dashboard-right`). El chatbot ahora es una sección (`chatbot-section`) dentro del panel principal.
    - **Posicionamiento**: el chat se ubica **arriba** de los filtros y productos, visible inmediatamente al cargar la página.
    - Sección con fondo `rgba(12,16,24,0.85)`, borde `rgba(255,255,255,0.1)`, `border-radius: 20px`, sombra pronunciada y `backdrop-filter`.
    - Avatar "S" reemplazado por icono SVG vectorial de robot.
    - Aumentado contraste del chat: header `rgba(20,26,38,0.95)`, mensajes bot con borde `rgba(255,255,255,0.12)`, input con texto blanco.
    - Filtros: añadido botón toggle "Filtros" para expandir/colapsar la barra de filtros con animación suave.
    - Layout centrado (`max-width: 1400px`) para mejor lectura en pantallas grandes.
    - **Fix scroll flotante**: cambiado `body { overflow: hidden }` a `overflow-y: auto` y eliminado `overflow-y: auto` de `.dashboard-left`. El scroll ahora es natural de la página completa, no de un contenedor interno.
    - Responsividad ajustada: la sección del chat se adapta en móvil con altura reducida.

- [24/04] **Mejora de UX: Chatbot Flotante Elegante y Sonidos Procedurales:**
    - Rediseñado layout: Chatbot movido de columna rígida a panel flotante (`fixed`) con Glassmorphism (`backdrop-filter`).
    - Añadidas animaciones de entrada `slideInBounce` para mensajes de chat.
    - Implementado sistema de audio procedural (Web Audio API) para sonidos de envío/recepción (sin archivos externos).
    - Ajustado catálogo para ocupar ancho total con padding inteligente.

- [24/04] **Hotfix: Migración de generación PDF al Backend (ReportLab):**
    - Eliminado el uso de la librería CDN `jsPDF` en el frontend (`index.html`) que causaba errores por red bloqueada ("El generador de PDF está cargando").
    - Instalada librería `reportlab` en Python.
    - Creado endpoint `/generate_pdf` en `app.py` que recibe el carrito en JSON y genera la factura PDF.
    - `boleta_compra.pdf` se guarda físicamente en la raíz del proyecto y se devuelve directamente al navegador para su apertura automática.

- [24/04] **Hotfix: Carga lenta al iniciar y dar F5 (Iconos SVG):**
    - Eliminado el CDN de FontAwesome en `index.html` que causaba bloqueos de renderizado de red (tiempos de carga muy altos).
    - Reemplazados los últimos iconos restantes (`fa-search`, `fa-shopping-cart`, `fa-xmark`, `fa-comment-dots`) por vectores SVG inline.
    - Esto elimina la dependencia externa y hace que el arranque local y la recarga de página (F5) sean instantáneos.

- [23/04] **BD: Limpieza Profunda SQL (Solo Catálogo):**
    - Añadidas sentencias `CREATE DATABASE IF NOT EXISTS` y `USE` para importación directa.
    - Eliminadas tablas `sesiones`, `memoria_usuario`, `historial_chat`.
    - Eliminados procedimientos `guardar_mensaje` y `upsert_memoria`.
    - SQL ahora contiene exclusivamente tablas de catálogo (`productos`, `categorias`, `colores`, `tallas`).
    - Estructura normalizada mantenida por eficiencia y precisión.

- [23/04] **Hotfix: Precisión de Filtrado Frontend (Subcategorías):**
    - Añadidas palabras clave (`pantalon`, `polo`, `zapatilla`, `conjunto`) a `Lista_De_Keywords_Especificas` en `main.js`.
    - Eliminado `Producto.category` del `Texto_Indexable_Del_Producto` para evitar que la palabra "pantalones" empareje con todos los ítems de esa categoría (como faldas/shorts).
    - El frontend ahora filtra estrictamente por texto dentro de la categoría.

- [23/04] **Hotfix: Sincronización Backend-Frontend (Sinónimos y Conteo):**
    - Añadidos sinónimos (`leggin`, `jogger`, `buzo`) para `pantalon` en `js/main.js` y `catalogo.py`.
    - Eliminado `Producto.category` de `Texto_Buscable` en `catalogo.py` (`Buscar_Productos_Por_Coincidencia_Lexica`).
    - El chatbot ahora cuenta exactamente lo mismo que el frontend y entiende que "pantalones" incluye "leggins".

- [23/04] **Mejora: UX de Filtros Vacíos:**
    - Modificado `dialogo.py` para reiniciar todos los filtros de forma silenciosa cuando no hay coincidencias.
    - Se reemplazó "Mantenemos los filtros anteriores" por sugerencias automáticas de otras opciones del catálogo.

- [23/04] **Hotfix: Precisión de Filtro por Precio:**
    - Añadidos términos de comparación (`menor`, `menores`, `mayor`, `mayores`, `bajo`) a `Ruidos_Excluir` en `extractor.py`.
    - Esto evita que palabras como "menores" se traten como texto de búsqueda, impidiendo que el frontend oculte los productos, y asegurando que el precio se guarde correctamente en memoria para filtros encadenados (ej. pedir luego "para hombre").

- [23/04] **Mejora: UX y Herencia de Botones Sugeridos:**
    - Modificado `Debe_Heredar_Filtros_De_Contexto` en `dialogo.py` para permitir la herencia del precio cuando el usuario hace clic en un botón de sugerencia que contiene la misma categoría actual (Ej: "Zapatillas para hombre" estando en "CALZADO").
    - Ajustado el mensaje de respuesta de género para que use la entidad extraída (Ej: "zapatillas") en lugar del término genérico "productos en CALZADO".

- [24/04] **Hotfix: Iconos de Chat Invisibles:**
    - Reemplazados los iconos de FontAwesome (`fa-microphone` y `fa-paper-plane`) en `index.html` por vectores SVG en línea pura.
    - Esto garantiza que los botones de Enviar y Micrófono siempre sean visibles incluso si el CDN de fuentes falla o es bloqueado por el navegador/adblock.

- [24/04] **Mejora: Eliminación de Memoria Persistente Zombie:**
    - Se eliminó el uso de `shelve` en `memoria.py`. Ahora la memoria del bot vive exclusivamente en RAM y se destruye al reiniciar el servidor (`app.py`).
    - En el frontend (`js/main.js`), se reemplazó el `session_id` estático (`user_local`) por un `Session_ID_Unico` generado aleatoriamente en cada recarga de página (F5).
    - Esto asegura que cada vez que recargas el navegador o reinicias el bot, empiezas con una memoria 100% limpia sin filtros arrastrados.

- [24/04] **Hotfix: Pérdida de contexto en precios cortos:**
    - Modificado `dialogo.py` para que los mensajes cortos (<= 6 palabras) que contengan un precio (ej: "y de 150?") fuercen la intención `buscar_producto`.
    - Esto evita que el modelo PyTorch se confunda por la falta de verbos y asuma intenciones incorrectas (como `consulta_precio` o características de materiales).

- [24/04] **Mejora UI y Exportación PDF:**
    - Reemplazados los iconos caídos de FontAwesome (`fa-robot` y `fa-plus`) por vectores SVG en línea en las tarjetas de producto en `main.js`.
    - Creado endpoint `/save_pdf` en `app.py` para guardar físicamente el archivo generado en la raíz del proyecto como `boleta_compra.pdf`.
    - El frontend ahora envía el PDF al backend, lo guarda, y luego lo abre en el navegador al finalizar compra.

- [23/04] **Hotfix: Mapeo de columnas SQL en catalogo.py:**
    - Corregido mapeo de `image` (antes buscaba `imagen`, ahora `imagen_url`).
    - Corregido mapeo de `colores` y `tallas` para coincidir con la vista SQL.
    - Las imágenes ahora cargan correctamente en el frontend.

- [23/04] **Hotfix: Configuración MySQL en config.py:**
    - Corregido error `module config has no attribute DB_HOST`.
    - Añadidas variables por defecto: `localhost`, `root`, `3306`.

- [23/04] **Migración Backend: Integración completa de MySQL:**
    - `catalogo.py` actualizado. `Cargar_Lista_De_Productos_Desde_BD` reemplaza lectura JSON, conectando con `db.py`.
    - `js/main.js` actualizado. Eliminada ruta local `data/products_scraped.json` para forzar consumo API.
    - Archivo `products_scraped.json` eliminado definitivamente.

- [23/04] **BD: Limpieza SQL (Opción JSON retenida):**
    - `chatbot_tienda.sql` depurado. Eliminadas tablas `intenciones`, `patrones`, `respuestas` y `vista_intents_completa`.
    - `intents.json` conservado para entrenamiento directo de la IA neuronal.
    - Base de datos 100% enfocada en Catálogo, Usuarios e Historial.

- [23/04] **BD: Revisión y Validación Estructura MySQL:**
    - Revisado `chatbot_tienda.sql` (Relacional completo, FKs, vistas, índices, Fulltext).
    - Añadidos `db.py` (Pooling de conexión) y `README_MYSQL.md`.
    - BD apta para reemplazar JSON.

- [23/04] **Sincronización: Reinicio de rama main (Hard Reset GitHub):**
    - Rama `main` en GitHub borrada y reemplazada por archivos locales actuales.
    - Historial de commits limpiado mediante rama orphan.
    - Sincronización completa con estado local.

- [23/04] **Sincronización: Actualización de repositorio local (git pull):**
    - Repositorio actualizado con éxito desde origen/main.
    - Cambios aplicados en 20 archivos (Lógica de diálogo, entrenamiento modelo, estilos CSS, etc.).

- [19/04] **🔒 Seguridad: Mitigación de Vulnerabilidad XSS en Frontend:**
    - `js/main.js`: Eliminado `innerHTML`. Implementado `createElement` y `textContent`.

## Resumen de Tareas Anteriores (Compresión Activa)

- [18/04] Optimización de Interfaz Móvil (Responsive Design).
- [18/04] Sincronización exacta Backend-Frontend por IDs de producto.
- [18/04] Hotfix Estabilidad /chat (500 UnboundLocalError).
- [17/04] Limpieza archivos Python, soporte subtipos y corrección coherencia contextual.
- [17/04] Naturalidad respuesta, arranque unificado y optimización filtros color.
- [17/04] Mejora detección intenciones y robustez en filtros automáticos.
- [17/04] Categorización faldas/vestidos y batería de 15 pruebas complejas.

## Pendiente
- Monitorear falsos positivos en búsquedas semánticas muy amplias.
- Expandir la base de sinónimos para categorías emergentes.
