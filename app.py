"""
app.py · Punto de Entrada Principal del Chatbot SENATI Sports
═════════════════════════════════════════════════════════════

Servidor Flask que orquesta todos los módulos del sistema.

FLUJO DE UN MENSAJE DE CHAT:
  1. El frontend (interfaz_chatbot.html) envía POST a /chat con el mensaje
  2. Se verifica si hay un producto en contexto (context_product_id)
  3. Se detecta si es una consulta rápida (precio/stock/color) → respuesta directa
  4. Se detecta si el usuario quiere añadir al carrito → respuesta con add_to_cart
  5. Si no, se delega a bot.motor_dialogo.Obtener_Respuesta_Principal()
     que retorna (respuesta, etiqueta, acción_de_filtro)
  6. El frontend aplica los filtros al catálogo y muestra la respuesta

FLUJO DE UNA VENTA:
  1. El frontend llama a /generate_pdf con el carrito
  2. Se genera la boleta PDF con reportlab
  3. Se registra la venta en MySQL (transacción con ROLLBACK)
  4. Se descuenta el stock de cada producto

MÓDULOS QUE USA:
  - bot.motor_dialogo       → cerebro conversacional
  - bot.catalogo_productos  → catálogo y búsqueda de productos
  - bot.memoria_conversacion → contexto por sesión
  - bot.inteligencia_artificial → modelo IA y voz
  - admin.panel_administracion  → panel de administración
  - core.base_datos         → conexión MySQL
  - core.configuracion      → constantes del sistema
"""

import os 
import tempfile  
from flask import Flask, request, jsonify, send_from_directory, send_file  
from flask_cors import CORS  
import datetime  
from reportlab.lib.pagesizes import letter 
from reportlab.pdfgen import canvas  

from admin import Inicializar_Admin  # Configura el panel de administración web
from core import configuracion  # Carga las constantes y ajustes globales del sistema
from core.base_datos import Ejecutar_Escritura  # Permite guardar datos en la base de datos MySQL
from bot.inteligencia_artificial import Modelo_IA, Etiquetas_De_Intencion, Obtener_Modelo_Voz  # Cerebro de IA y voz
from bot.catalogo_productos import (  # Gestión de búsqueda y stock de los productos
    Datos_De_Productos, Catalogos_De_Productos, Fuente_Activa_De_Catalogo,
    Cambiar_Fuente_De_Catalogo, Buscar_Productos, Obtener_Producto_Por_Id,
    Decrementar_Stock_En_Cache
)
from bot.memoria_conversacion import Obtener_Contexto, Actualizar_Contexto  # Recuerda el estado de la charla con cada usuario
from bot.motor_dialogo import Obtener_Respuesta_Principal  # Procesa el mensaje y decide qué responder


# ─── Inicialización de Flask ─────────────────────────────────────────────────

Aplicacion = Flask(__name__)
Aplicacion.secret_key = os.getenv("FLASK_SECRET_KEY", "senati_admin_2024")

CORS(Aplicacion, resources={r"/*": {"origins": configuracion.Origenes_Cors_Permitidos}})

Inicializar_Admin(Aplicacion)


# ─── Detección de Intención Contextual ───────────────────────────────────────

def Detectar_Intencion_De_Detalle_Contextual(Mensaje_Usuario):
    """Detecta si el usuario pregunta por precio, stock o color de un producto en contexto."""
    Texto = str(Mensaje_Usuario or "").strip().lower()
    if not Texto:
        return None

    if any(P in Texto for P in ("precio", "cuesta", "costo", "coste", "valor")):
        return "consultar_precio_item"
    if any(P in Texto for P in ("talla", "tallas", "stock", "disponible", "disponibles")):
        return "consultar_stock_item"
    if any(P in Texto for P in ("color", "colores", "tono", "tonos")):
        return "colores"

    return None


def Detectar_Intencion_Carrito(Mensaje_Usuario):
    """Detecta si el usuario quiere añadir el producto en contexto al carrito."""
    Texto = str(Mensaje_Usuario or "").strip().lower()
    Palabras = (
        "carrito", "añadir", "añadelo", "agregar", "agregalo",
        "comprar", "comprarlo", "quiero", "llevar", "llevarlo",
        "pedir", "pedirlo", "adquirir",
    )
    return any(P in Texto for P in Palabras)


def Construir_Respuesta_Contextual_Rapida(Producto, Etiqueta):
    """Genera una respuesta directa para consultas de precio/stock/color de un producto en contexto."""
    Nombre = Producto.get("name", "producto")

    if Etiqueta == "consultar_precio_item":
        Precio = Producto.get("price")
        if isinstance(Precio, (int, float)):
            return f"¡Excelente elección! El precio del {Nombre} es de S/ {Precio:.2f}."
        return f"Aún no tengo registrado el precio del {Nombre}."

    if Etiqueta == "consultar_stock_item":
        Tallas = Producto.get("tallas") or ["No especificadas"]
        Genero = Producto.get("genero") or "No especificado"
        Stock = Producto.get("stock")
        if Stock is None:
            Stock = "No especificado"
        return (
            f"Claro, el {Nombre} lo tenemos en las siguientes tallas: {', '.join(Tallas)}. "
            f"Genero: {Genero}. Stock: {Stock} unidades."
        )

    if Etiqueta == "colores":
        Colores = Producto.get("colores") or []
        if Colores:
            return f"El {Nombre} está disponible en estos colores: {', '.join(Colores)}."
        Color = Producto.get("color")
        if Color:
            return f"El {Nombre} está disponible en color {Color}."
        return f"Aún no tengo colores registrados para el {Nombre}."

    return None


# ─── Rutas Estáticas ─────────────────────────────────────────────────────────

@Aplicacion.route('/', methods=['GET'])
def Servir_Index():
    return send_from_directory('.', 'interfaz_chatbot.html')


@Aplicacion.route('/css/<path:Nombre_Archivo>', methods=['GET'])
def Servir_Css(Nombre_Archivo):
    return send_from_directory('css', Nombre_Archivo)


@Aplicacion.route('/js/<path:Nombre_Archivo>', methods=['GET'])
def Servir_Js(Nombre_Archivo):
    return send_from_directory('js', Nombre_Archivo)


@Aplicacion.route('/uploads/<path:Nombre_Archivo>', methods=['GET'])
def Servir_Uploads(Nombre_Archivo):
    Directorio = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'uploads')
    return send_from_directory(Directorio, Nombre_Archivo)


# ─── Estado del Servidor ─────────────────────────────────────────────────────

@Aplicacion.route('/status', methods=['GET'])
def Estado_Del_Servidor():
    return jsonify({
        "status": "online",
        "bot_name": configuracion.Nombre_Del_Bot,
        "products_active": len(Datos_De_Productos),
        "products_auto": len(Catalogos_De_Productos.get("auto", [])),
        "products_scraped": len(Catalogos_De_Productos.get("scraped", [])),
        "catalog_source_active": Fuente_Activa_De_Catalogo,
        "ai_model": "PyTorch loaded" if Modelo_IA else "Not loaded",
        "tags": Etiquetas_De_Intencion
    })


# ─── Chat ────────────────────────────────────────────────────────────────────

@Aplicacion.route('/chat', methods=['POST'])
def Chat():
    Datos = request.get_json(silent=True) or {}
    Mensaje = str(Datos.get('message', '')).strip()
    Id_Sesion = str(Datos.get('session_id', 'default_user')).strip() or 'default_user'
    Id_Producto_Ctx = Datos.get('context_product_id')
    Contexto = Obtener_Contexto(Id_Sesion)

    Fuente = Datos.get('catalog_source') or Contexto.get('catalog_source', 'auto')
    Fuente_Usada = Cambiar_Fuente_De_Catalogo(Fuente)
    Actualizar_Contexto(Id_Sesion, Fuente_De_Catalogo=Fuente_Usada)

    if isinstance(Id_Producto_Ctx, str) and Id_Producto_Ctx.isdigit():
        Id_Producto_Ctx = int(Id_Producto_Ctx)

    # Actualizar producto en contexto
    if Id_Producto_Ctx is not None:
        Actualizar_Contexto(Id_Sesion, Id_De_Producto=Id_Producto_Ctx, Fuente_De_Catalogo=Fuente_Usada)
        Contexto = Obtener_Contexto(Id_Sesion)

        if Mensaje == 'quiero saber mas de este producto':
            Producto = Obtener_Producto_Por_Id(Id_Producto_Ctx)
            if Producto:
                Msg = f"¡Excelente elección! Veo que te interesa el {Producto['name']}. ¿Qué te gustaría saber? (Ej. 'precio' o 'stock')."
            else:
                Msg = "Claro, ¿En qué te ayudo con este producto?"
            return jsonify({
                "response": Msg, "tag": "contexto_iniciado",
                "bot_name": configuracion.Nombre_Del_Bot, "catalog_source": Fuente_Usada,
            })

    if not Mensaje:
        return jsonify({"error": "No se recibio mensaje"}), 400

    # Consulta contextual rápida (precio/stock/color)
    Id_Producto_Ctx_Actual = Contexto.get('selected_product_id')
    Etiqueta_Detalle = Detectar_Intencion_De_Detalle_Contextual(Mensaje)
    if Id_Producto_Ctx_Actual and Etiqueta_Detalle:
        Producto = Obtener_Producto_Por_Id(Id_Producto_Ctx_Actual)
        if Producto:
            Respuesta_Ctx = Construir_Respuesta_Contextual_Rapida(Producto, Etiqueta_Detalle)
            if Respuesta_Ctx:
                Actualizar_Contexto(Id_Sesion, Etiqueta=Etiqueta_Detalle, Id_De_Producto=Id_Producto_Ctx_Actual, Fuente_De_Catalogo=Fuente_Usada)
                return jsonify({
                    "response": Respuesta_Ctx, "tag": Etiqueta_Detalle,
                    "bot_name": configuracion.Nombre_Del_Bot, "catalog_source": Fuente_Usada,
                })

    # Intención de carrito
    if Id_Producto_Ctx_Actual and Detectar_Intencion_Carrito(Mensaje):
        Producto = Obtener_Producto_Por_Id(Id_Producto_Ctx_Actual)
        if Producto:
            Nombre = Producto.get("name", "el producto")
            Precio = Producto.get("price", 0)
            Stock = Producto.get("stock", 0)
            if isinstance(Stock, (int, float)) and int(Stock) <= 0:
                return jsonify({
                    "response": f"Lo siento, {Nombre} está agotado en este momento. 😔",
                    "tag": "sin_stock", "bot_name": configuracion.Nombre_Del_Bot, "catalog_source": Fuente_Usada,
                })
            return jsonify({
                "response": f"¡Listo! Añadí {Nombre} (S/ {Precio:.2f}) a tu carrito. 🛒",
                "tag": "agregar_carrito", "add_to_cart": True,
                "product": Producto, "bot_name": configuracion.Nombre_Del_Bot, "catalog_source": Fuente_Usada,
            })

    # Motor de diálogo principal
    Respuesta, Etiqueta, Accion = Obtener_Respuesta_Principal(Id_Sesion, Mensaje)

    Resultado = {
        "response": Respuesta, "tag": Etiqueta,
        "bot_name": configuracion.Nombre_Del_Bot, "catalog_source": Fuente_Usada,
    }
    if Accion:
        Resultado["filter_action"] = Accion

    return jsonify(Resultado)


# ─── Productos ───────────────────────────────────────────────────────────────

@Aplicacion.route('/products', methods=['GET'])
def Listar_Productos():
    Fuente = Cambiar_Fuente_De_Catalogo(request.args.get('source', 'auto'))
    return jsonify({"products": Datos_De_Productos, "count": len(Datos_De_Productos), "source": Fuente})


# ─── Búsqueda ────────────────────────────────────────────────────────────────

@Aplicacion.route('/search', methods=['POST'])
def Buscar():
    Datos = request.get_json(silent=True) or {}
    Fuente = Cambiar_Fuente_De_Catalogo(Datos.get('catalog_source', request.args.get('source', 'auto')))

    Cat = Datos.get('category')
    Color = Datos.get('color')
    Genero = Datos.get('genero')
    Keywords = Datos.get('keywords')

    Precio_Max = Datos.get('max_price')
    if Precio_Max is not None:
        try:
            Precio_Max = float(Precio_Max)
        except (TypeError, ValueError):
            Precio_Max = None

    Limite = Datos.get('limit', configuracion.Limite_Busqueda_Por_Defecto)
    try:
        Limite = int(Limite)
    except (TypeError, ValueError):
        Limite = configuracion.Limite_Busqueda_Por_Defecto
    Limite = max(1, min(configuracion.Maximo_Limite_De_Busqueda, Limite))

    Resultados = Buscar_Productos(
        Categoria=Cat, Color=Color, Precio_Maximo=Precio_Max,
        Genero=Genero, Palabras_Clave=Keywords, Limite=Limite,
    )
    return jsonify({"products": Resultados, "count": len(Resultados), "source": Fuente})


# ─── Transcripción de Voz ────────────────────────────────────────────────────

@Aplicacion.route('/transcribe', methods=['POST'])
def Transcribir_Voz():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    Archivo = request.files['audio']
    Ruta_Temporal = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as Temp:
            Ruta_Temporal = Temp.name
            Archivo.save(Ruta_Temporal)

        Modelo_Voz = Obtener_Modelo_Voz()
        Segmentos, _ = Modelo_Voz.transcribe(Ruta_Temporal, beam_size=5)
        Texto = " ".join([Seg.text for Seg in Segmentos])
        return jsonify({"text": Texto.strip()})
    except Exception as Error:
        print(f"[ERROR] Transcripcion de voz: {Error}")
        return jsonify({"error": "No se pudo procesar el audio"}), 500
    finally:
        if Ruta_Temporal and os.path.exists(Ruta_Temporal):
            os.remove(Ruta_Temporal)


# ─── Generación de Boleta PDF ────────────────────────────────────────────────

@Aplicacion.route('/generate_pdf', methods=['POST'])
def Generar_Boleta_PDF():
    Datos = request.get_json(silent=True) or {}
    Carrito = Datos.get('carrito', [])

    if not Carrito:
        return jsonify({"error": "Carrito vacio"}), 400

    Ruta_Guardado = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boleta_compra.pdf')

    try:
        C = canvas.Canvas(Ruta_Guardado, pagesize=letter)
        C.setFont("Helvetica-Bold", 20)
        C.drawCentredString(300, 750, "SENATI SPORTS - Boleta de Venta")

        C.setFont("Helvetica", 12)
        Fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        C.drawString(50, 710, f"Fecha: {Fecha}")

        Y = 670
        C.setFont("Helvetica-Bold", 12)
        C.drawString(50, Y, "Producto")
        C.drawString(350, Y, "Cant.")
        C.drawString(420, Y, "P. Unit")
        C.drawString(500, Y, "Subtotal")

        Y -= 10
        C.line(50, Y, 550, Y)
        Y -= 20
        C.setFont("Helvetica", 12)

        Total = 0
        for Item in Carrito:
            Nombre = str(Item.get('name', ''))
            if len(Nombre) > 40:
                Nombre = Nombre[:37] + '...'

            Cantidad = int(Item.get('quantity', 1))
            Precio = float(Item.get('price', 0))
            Subtotal = Precio * Cantidad
            Total += Subtotal

            C.drawString(50, Y, Nombre)
            C.drawRightString(380, Y, str(Cantidad))
            C.drawRightString(460, Y, f"S/ {Precio:.2f}")
            C.drawRightString(540, Y, f"S/ {Subtotal:.2f}")
            Y -= 20

            if Y < 100:
                C.showPage()
                Y = 750
                C.setFont("Helvetica", 12)

        Y -= 10
        C.line(50, Y, 550, Y)
        Y -= 20
        C.setFont("Helvetica-Bold", 12)
        C.drawString(420, Y, "TOTAL:")
        C.drawRightString(540, Y, f"S/ {Total:.2f}")

        Y -= 40
        C.setFont("Helvetica-Oblique", 10)
        C.drawCentredString(300, Y, "¡Gracias por tu compra en SENATI SPORTS!")

        C.save()

        # Registrar venta en la base de datos
        try:
            Sesion_Id = str(Datos.get('session_id', 'anonimo'))
            Total_Venta = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in Carrito)
            Venta_Id = Ejecutar_Escritura(
                "INSERT INTO ventas (sesion_id, total, cantidad_items) VALUES (%s, %s, %s)",
                (Sesion_Id, round(Total_Venta, 2), len(Carrito))
            )
            if Venta_Id:
                for Item in Carrito:
                    Cantidad = int(Item.get('quantity', 1))
                    Precio = float(Item.get('price', 0))
                    Prod_Id = int(Item.get('id', 0))
                    Nombre = str(Item.get('name', 'Producto'))
                    Subtotal = Precio * Cantidad
                    Ejecutar_Escritura(
                        "INSERT INTO venta_detalle (venta_id, producto_id, nombre_producto, precio_unitario, cantidad, subtotal) VALUES (%s,%s,%s,%s,%s,%s)",
                        (Venta_Id, Prod_Id, Nombre, Precio, Cantidad, round(Subtotal, 2))
                    )
                    Ejecutar_Escritura(
                        "UPDATE productos SET stock = GREATEST(0, stock - %s) WHERE id = %s",
                        (Cantidad, Prod_Id)
                    )
                    Decrementar_Stock_En_Cache(Prod_Id, Cantidad)
                print(f"[ADMIN] Venta #{Venta_Id} registrada automáticamente.")
        except Exception as Error_Venta:
            print(f"[ADMIN] No se pudo registrar la venta: {Error_Venta}")

        return send_file(Ruta_Guardado, mimetype='application/pdf', as_attachment=False)
    except Exception as Error:
        print(f"[ERROR] No se pudo generar PDF: {Error}")
        return jsonify({"error": str(Error)}), 500


# ─── Ejecución ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    Puerto = int(os.getenv('SENATI_PORT', '5000'))
    Debug = False
    print(f">>> Frontend listo en http://localhost:{Puerto}/")
    print(f">>> Admin Panel en http://localhost:{Puerto}/admin")
    print(f">>> Debug: {Debug}")
    Aplicacion.run(port=Puerto, debug=Debug)
