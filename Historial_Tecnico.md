# Historial Técnico - Chatbot E-commerce SENATI

## Tareas Recientes (Detalladas)

- [19/04] **🔒 Seguridad: Mitigación de Vulnerabilidad XSS en Frontend:**
    - `js/main.js`: Se eliminó el uso de `innerHTML` con literales de plantilla en `Crear_Tarjeta_Producto` y `Actualizar_UI_Carrito`.
    - Se implementó la construcción programática del DOM mediante `document.createElement`, `textContent` y `appendChild`.
    - Se garantizó que los datos controlados por el usuario (nombres de productos de catálogos scrapeados) se traten estrictamente como texto plano.
    - Verificación: Validado mediante Playwright con payloads de inyección (`<img src=x onerror=...>`), confirmando que se renderizan de forma segura y no ejecutan scripts.
    - Higiene: Se eliminaron artefactos de ejecución (`backend.log`, `frontend.log`) y código muerto antes del commit.

- [18/04] **Optimización de Interfaz Móvil (Responsive Design):**
    - `index.html`: agregado botón flotante `mobile-chat-toggle` para controlar el chatbot en pantallas pequeñas.
    - `css/style.css`: implementadas Media Queries para apilar paneles, habilitar scroll en body y redimensionar tarjetas de producto (2 columnas en móviles).
    - `js/main.js`: añadida lógica de interactividad para abrir/cerrar el chat móvil y auto-cierre al hacer clic fuera del panel.

- [18/04] **Sincronización Exacta Backend-Frontend por IDs de Producto:**
    - `dialogo.py`: actualizado payload `filter_action` para enviar lista explícita de `product_ids` encontrados.
    - `js/main.js`: implementado `Ids_Filtrados_Por_Backend` (Set) para renderizado estricto basado en la respuesta del NLP.
    - `intents.json` & `model.pth`: reentrenamiento del modelo con nuevos patrones para `buscar_producto` y `colores`.

## Resumen de Tareas Anteriores (Compresión Activa)

- [18/04] Hotfix Crítico de Estabilidad en /chat (500 por UnboundLocalError) mediante inicialización defensiva.
- [17/04] Limpieza Segura de Archivos Python manteniendo núcleo de 9 archivos operativos.
- [17/04] Hotfix de Coherencia Contextual en API y soporte para subtipos sin recorte de categoría.
- [17/04] Corrección de subtipos (Mochilas/Faldas) y herencia de filtros refinada.
- [17/04] Naturalidad en respuesta de búsqueda y gestión de herencia de precio.
- [17/04] Arranque Unificado Frontend + API en el mismo puerto con rutas estáticas.
- [17/04] Corrección de coherencia conversacional (TF-IDF fallback y singularización).
- [17/04] Corrección de lógica de diálogo eliminando placeholders sin reemplazar.
- [17/04] Optimización de filtros de color multivariante en backend y frontend.
- [17/04] Mejora en detección de intenciones priorizando pattern matching en baja confianza.
- [17/04] Robustez en filtros automáticos al detectar entidades en mensajes fuera de dominio.
- [17/04] Categorización de faldas y vestidos en PANTALONES.
- [17/04] Ejecución de batería de 15 casos de prueba complejos cubriendo 6+ turnos.

## Pendiente
- Monitorear falsos positivos en búsquedas semánticas muy amplias.
- Expandir la base de sinónimos para categorías emergentes.
