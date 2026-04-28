import os
import tempfile
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import admin as admin_module
import config
from ia import Modelo_IA, Etiquetas_De_Intencion, Obtener_Modelo_Voz
from catalogo import (
    Datos_De_Productos, Catalogos_De_Productos, Fuente_Activa_De_Catalogo,
    Cambiar_Fuente_De_Catalogo, Buscar_Productos, Obtener_Producto_Por_Id
)
from memoria import Obtener_Contexto, Actualizar_Contexto
from dialogo import Obtener_Respuesta_Principal

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "senati_admin_2024")

# Configuración de CORS: Permitir solo origenes definidos en config.
CORS(app, resources={r"/*": {"origins": config.Origenes_Cors_Permitidos}})

# Módulo de administración
admin_module.init_admin(app)


def Detectar_Intencion_De_Detalle_Contextual(Mensaje_Usuario):
    Texto_Normalizado = str(Mensaje_Usuario or "").strip().lower()
    if not Texto_Normalizado:
        return None
    Indicadores_De_Precio = ("precio", "cuesta", "costo", "coste", "valor")
    Indicadores_De_Stock = ("talla", "tallas", "stock", "disponible", "disponibles")
    Indicadores_De_Color = ("color", "colores", "tono", "tonos")

    if any(Indicador in Texto_Normalizado for Indicador in Indicadores_De_Precio):
        return "consultar_precio_item"
    if any(Indicador in Texto_Normalizado for Indicador in Indicadores_De_Stock):
        return "consultar_stock_item"
    if any(Indicador in Texto_Normalizado for Indicador in Indicadores_De_Color):
        return "colores"

    return None


def Construir_Respuesta_Contextual_Rapida(Producto, Etiqueta_Detalle):
    Nombre_Producto = Producto.get("name", "producto")

    if Etiqueta_Detalle == "consultar_precio_item":
        Precio = Producto.get("price")
        if isinstance(Precio, (int, float)):
            return f"¡Excelente elección! El precio del {Nombre_Producto} es de S/ {Precio:.2f}."
        return f"Aún no tengo registrado el precio del {Nombre_Producto}."

    if Etiqueta_Detalle == "consultar_stock_item":
        Tallas = Producto.get("tallas") or ["No especificadas"]
        Genero = Producto.get("genero") or "No especificado"
        Stock = Producto.get("stock")
        if Stock is None:
            Stock = "No especificado"
        return (
            f"Claro, el {Nombre_Producto} lo tenemos en las siguientes tallas: {', '.join(Tallas)}. "
            f"Genero: {Genero}. Stock: {Stock} unidades."
        )

    if Etiqueta_Detalle == "colores":
        Colores = Producto.get("colores") or []
        if Colores:
            return f"El {Nombre_Producto} está disponible en estos colores: {', '.join(Colores)}."
        Color_Principal = Producto.get("color")
        if Color_Principal:
            return f"El {Nombre_Producto} está disponible en color {Color_Principal}."
        return f"Aún no tengo colores registrados para el {Nombre_Producto}."

    return None


@app.route('/', methods=['GET'])
def index():
    return send_from_directory('.', 'index.html')


@app.route('/status', methods=['GET'])
def Estado_Del_Servidor():
    return jsonify({
        "status": "online",
        "bot_name": config.Nombre_Del_Bot,
        "products_active": len(Datos_De_Productos),
        "products_auto": len(Catalogos_De_Productos.get("auto", [])),
        "products_scraped": len(Catalogos_De_Productos.get("scraped", [])),
        "catalog_source_active": Fuente_Activa_De_Catalogo,
        "ai_model": "PyTorch loaded" if Modelo_IA else "Not loaded",
        "tags": Etiquetas_De_Intencion
    })


@app.route('/css/<path:Nombre_De_Archivo>', methods=['GET'])
def Servir_Archivos_Css(Nombre_De_Archivo):
    return send_from_directory('css', Nombre_De_Archivo)


@app.route('/js/<path:Nombre_De_Archivo>', methods=['GET'])
def Servir_Archivos_Js(Nombre_De_Archivo):
    return send_from_directory('js', Nombre_De_Archivo)


@app.route('/chat', methods=['POST'])
def chat():
    Datos_Usuario = request.get_json(silent=True) or {}
    mensaje = str(Datos_Usuario.get('message', '')).strip()
    print(f"[DEBUG] Mensaje recibido: '{mensaje}'")
    Id_De_Sesion_Actual = str(Datos_Usuario.get('session_id', 'default_user')).strip() or 'default_user'
    Id_De_Producto_En_Contexto = Datos_Usuario.get('context_product_id')
    Contexto_Actual = Obtener_Contexto(Id_De_Sesion_Actual)

    Fuente_Solicitada = Datos_Usuario.get('catalog_source')
    if not Fuente_Solicitada:
        Fuente_Solicitada = Contexto_Actual.get('catalog_source', 'auto')

    Fuente_Usada = Cambiar_Fuente_De_Catalogo(Fuente_Solicitada)
    Actualizar_Contexto(Id_De_Sesion_Actual, Fuente_De_Catalogo=Fuente_Usada)

    if isinstance(Id_De_Producto_En_Contexto, str) and Id_De_Producto_En_Contexto.isdigit():
        Id_De_Producto_En_Contexto = int(Id_De_Producto_En_Contexto)
    
    # Si recibimos un ID de contexto, actualizamos el estado actual del bot
    if Id_De_Producto_En_Contexto is not None:
        Actualizar_Contexto(
            Id_De_Sesion_Actual,
            Id_De_Producto=Id_De_Producto_En_Contexto,
            Fuente_De_Catalogo=Fuente_Usada,
        )
        Contexto_Actual = Obtener_Contexto(Id_De_Sesion_Actual)
        # Si es el mensaje oculto de inicio de consulta, cortamos aquí
        if mensaje == 'quiero saber mas de este producto':
            product = Obtener_Producto_Por_Id(Id_De_Producto_En_Contexto)
            if product:
                msg = f"¡Excelente elección! Veo que te interesa el {product['name']}. ¿Qué te gustaría saber? (Ej. 'precio' o 'stock')."
            else:
                msg = "Claro, ¿En qué te ayudo con este producto?"
            return jsonify({
                "response": msg,
                "tag": "contexto_iniciado",
                "bot_name": config.Nombre_Del_Bot,
                "catalog_source": Fuente_Usada,
            })
        
    if not mensaje:
        return jsonify({"error": "No se recibio mensaje"}), 400

    Id_De_Producto_Contextual = Contexto_Actual.get('selected_product_id')
    Etiqueta_De_Detalle_Contextual = Detectar_Intencion_De_Detalle_Contextual(mensaje)
    if Id_De_Producto_Contextual and Etiqueta_De_Detalle_Contextual:
        Producto_Contextual = Obtener_Producto_Por_Id(Id_De_Producto_Contextual)
        if Producto_Contextual:
            Respuesta_Contextual = Construir_Respuesta_Contextual_Rapida(
                Producto_Contextual,
                Etiqueta_De_Detalle_Contextual,
            )
            if Respuesta_Contextual:
                Actualizar_Contexto(
                    Id_De_Sesion_Actual,
                    Etiqueta=Etiqueta_De_Detalle_Contextual,
                    Id_De_Producto=Id_De_Producto_Contextual,
                    Fuente_De_Catalogo=Fuente_Usada,
                )
                return jsonify({
                    "response": Respuesta_Contextual,
                    "tag": Etiqueta_De_Detalle_Contextual,
                    "bot_name": config.Nombre_Del_Bot,
                    "catalog_source": Fuente_Usada,
                })

    Respuesta_Bot, Etiqueta_Bot, Accion_De_Filtro = Obtener_Respuesta_Principal(Id_De_Sesion_Actual, mensaje)

    Resultado_Json = {
        "response": Respuesta_Bot,
        "tag": Etiqueta_Bot,
        "bot_name": config.Nombre_Del_Bot,
        "catalog_source": Fuente_Usada,
    }

    if Accion_De_Filtro:
        Resultado_Json["filter_action"] = Accion_De_Filtro

    return jsonify(Resultado_Json)


@app.route('/products', methods=['GET'])
def Productos_Endpoint():
    Fuente_Usada = Cambiar_Fuente_De_Catalogo(request.args.get('source', 'auto'))
    return jsonify({
        "products": Datos_De_Productos,
        "count": len(Datos_De_Productos),
        "source": Fuente_Usada,
    })


@app.route('/transcribe', methods=['POST'])
def Transcribir_Voz():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    Archivo_Audio = request.files['audio']
    Ruta_Temporal = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as Archivo_Temporal:
            Ruta_Temporal = Archivo_Temporal.name
            Archivo_Audio.save(Ruta_Temporal)

        Modelo_De_Voz = Obtener_Modelo_Voz()
        Segmentos, _ = Modelo_De_Voz.transcribe(Ruta_Temporal, beam_size=5)
        Texto_Transcrito = " ".join([segmento.text for segmento in Segmentos])
        return jsonify({"text": Texto_Transcrito.strip()})
    except Exception as Error_De_Transcripcion:
        print(f"[ERROR] Transcripcion de voz: {Error_De_Transcripcion}")
        return jsonify({"error": "No se pudo procesar el audio"}), 500
    finally:
        if Ruta_Temporal and os.path.exists(Ruta_Temporal):
            os.remove(Ruta_Temporal)


@app.route('/search', methods=['POST'])
def Buscar_Endpoint():
    """Endpoint para buscar productos filtrados."""
    Datos_De_Consulta = request.get_json(silent=True) or {}
    Fuente_Usada = Cambiar_Fuente_De_Catalogo(
        Datos_De_Consulta.get('catalog_source', request.args.get('source', 'auto'))
    )
    Categoria_Consulta = Datos_De_Consulta.get('category')
    Color_Consulta = Datos_De_Consulta.get('color')
    Genero_Consulta = Datos_De_Consulta.get('genero')
    Palabras_Clave_Consulta = Datos_De_Consulta.get('keywords')

    Precio_Maximo_Consulta = Datos_De_Consulta.get('max_price')
    if Precio_Maximo_Consulta is not None:
        try:
            Precio_Maximo_Consulta = float(Precio_Maximo_Consulta)
        except (TypeError, ValueError):
            Precio_Maximo_Consulta = None

    Limite_Consulta = Datos_De_Consulta.get('limit', config.Limite_Busqueda_Por_Defecto)
    try:
        Limite_Consulta = int(Limite_Consulta)
    except (TypeError, ValueError):
        Limite_Consulta = config.Limite_Busqueda_Por_Defecto
    Limite_Consulta = max(1, min(config.Maximo_Limite_De_Busqueda, Limite_Consulta))
    
    Resultados_De_Busqueda = Buscar_Productos(
        Categoria=Categoria_Consulta,
        Color=Color_Consulta,
        Precio_Maximo=Precio_Maximo_Consulta,
        Genero=Genero_Consulta,
        Palabras_Clave=Palabras_Clave_Consulta,
        Limite=Limite_Consulta,
    )
    return jsonify({
        "products": Resultados_De_Busqueda,
        "count": len(Resultados_De_Busqueda),
        "source": Fuente_Usada,
    })


@app.route('/generate_pdf', methods=['POST'])
def Generate_Pdf():
    datos = request.get_json(silent=True) or {}
    carrito = datos.get('carrito', [])
    
    if not carrito:
        return jsonify({"error": "Carrito vacio"}), 400

    Ruta_Guardado = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boleta_compra.pdf')
    
    try:
        c = canvas.Canvas(Ruta_Guardado, pagesize=letter)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(300, 750, "SENATI SPORTS - Boleta de Venta")
        
        c.setFont("Helvetica", 12)
        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.drawString(50, 710, f"Fecha: {fecha_actual}")
        
        y = 670
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Producto")
        c.drawString(350, y, "Cant.")
        c.drawString(420, y, "P. Unit")
        c.drawString(500, y, "Subtotal")
        
        y -= 10
        c.line(50, y, 550, y)
        
        y -= 20
        c.setFont("Helvetica", 12)
        total = 0
        for item in carrito:
            nombre = str(item.get('name', ''))
            if len(nombre) > 40:
                nombre = nombre[:37] + '...'
                
            cantidad = int(item.get('quantity', 1))
            precio = float(item.get('price', 0))
            subtotal = precio * cantidad
            total += subtotal
            
            c.drawString(50, y, nombre)
            c.drawRightString(380, y, str(cantidad))
            c.drawRightString(460, y, f"S/ {precio:.2f}")
            c.drawRightString(540, y, f"S/ {subtotal:.2f}")
            
            y -= 20
            
            if y < 100:
                c.showPage()
                y = 750
                c.setFont("Helvetica", 12)
                
        y -= 10
        c.line(50, y, 550, y)
        
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(420, y, "TOTAL:")
        c.drawRightString(540, y, f"S/ {total:.2f}")
        
        y -= 40
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(300, y, "¡Gracias por tu compra en SENATI SPORTS!")
        
        c.save()
        print(f"[OK] PDF generado y guardado en: {Ruta_Guardado}")

        # Registrar la venta en la base de datos automáticamente
        try:
            sesion_id = datos.get('session_id', 'anonimo')
            from admin import Admin_Registrar_Venta as _reg
            with app.test_request_context(
                '/admin/ventas/registrar',
                method='POST',
                json={'sesion_id': sesion_id, 'carrito': carrito}
            ):
                from flask import request as _req
                _req.get_json  # noqa
            # Llamada directa a la función de registro
            from db import ejecutar_escritura
            total_venta = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in carrito)
            venta_id = ejecutar_escritura(
                "INSERT INTO ventas (sesion_id, total, cantidad_items) VALUES (%s, %s, %s)",
                (str(datos.get('session_id', 'anonimo')), round(total_venta, 2), len(carrito))
            )
            if venta_id:
                for item in carrito:
                    cantidad = int(item.get('quantity', 1))
                    precio   = float(item.get('price', 0))
                    prod_id  = int(item.get('id', 0))
                    nombre   = str(item.get('name', 'Producto'))
                    subtotal = precio * cantidad
                    ejecutar_escritura(
                        "INSERT INTO venta_detalle (venta_id, producto_id, nombre_producto, precio_unitario, cantidad, subtotal) VALUES (%s,%s,%s,%s,%s,%s)",
                        (venta_id, prod_id, nombre, precio, cantidad, round(subtotal, 2))
                    )
                    ejecutar_escritura(
                        "UPDATE productos SET stock = GREATEST(0, stock - %s) WHERE id = %s",
                        (cantidad, prod_id)
                    )
                print(f"[ADMIN] Venta #{venta_id} registrada automáticamente.")
        except Exception as e_venta:
            print(f"[ADMIN] No se pudo registrar la venta: {e_venta}")

        return send_file(Ruta_Guardado, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        print(f"[ERROR] No se pudo generar PDF: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    server_port = int(os.getenv('SENATI_PORT', '5000'))
    debug_mode = True
    print(f">>> Frontend listo en http://localhost:{server_port}/")
    print(f">>> Estado API en http://localhost:{server_port}/status")
    print(f">>> Chat API en http://localhost:{server_port}/chat")
    print(f">>> Debug: {debug_mode}")
    app.run(port=server_port, debug=debug_mode)
