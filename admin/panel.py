"""
admin/panel.py  ·  Módulo de Administración para el Chatbot Tienda
--------------------------------------------------------------------
Provee rutas Flask para:
  - Login / Logout de administrador
  - CRUD de Productos (Crear, Leer, Actualizar, Eliminar)
  - CRUD de Categorías
  - Reportes de ventas (diario, semanal, mensual)
  - Stock de productos
  - Registrar ventas desde el carrito

Uso: importar y registrar en app.py con:
    from admin import Inicializar_Admin
    Inicializar_Admin(app)
"""

import os
import io
import uuid
import functools
import datetime
from flask import (
    Blueprint, request, jsonify, session,
    send_from_directory, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from core.db import Ejecutar_Consulta, Ejecutar_Escritura, Obtener_Conexion
from mysql.connector import Error
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _ext_permitida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── Blueprint ────────────────────────────────────────────────────────────────
Admin_Blueprint = Blueprint("admin", __name__)

# Clave secreta para sesiones (en producción usar variable de entorno)
ADMIN_SESSION_KEY = "admin_logged_in"
ADMIN_USER_KEY    = "admin_usuario"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def login_requerido(f):
    """Decorador: protege rutas que requieren sesión de admin activa."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get(ADMIN_SESSION_KEY):
            return jsonify({"error": "No autorizado. Inicie sesión como administrador."}), 401
        return f(*args, **kwargs)
    return wrapper


def _init_admin_default():
    """
    Crea el admin por defecto si la tabla está vacía o el hash es placeholder.
    Llámalo una vez al arrancar la app.
    """
    try:
        rows = Ejecutar_Consulta("SELECT id, password_hash FROM administradores WHERE usuario = 'admin'")
        hash_ok = generate_password_hash("admin123")
        if not rows:
            Ejecutar_Escritura(
                "INSERT INTO administradores (usuario, password_hash, nombre) VALUES (%s, %s, %s)",
                ("admin", hash_ok, "Administrador")
            )
            print("[ADMIN] Usuario 'admin' creado con contraseña 'admin123'.")
        elif "placeholder" in rows[0].get("password_hash", ""):
            Ejecutar_Escritura(
                "UPDATE administradores SET password_hash = %s WHERE usuario = 'admin'",
                (hash_ok,)
            )
            print("[ADMIN] Hash del admin actualizado.")
    except Exception as e:
        print(f"[ADMIN] No se pudo inicializar admin por defecto: {e}")


# ─── Servir panel HTML ────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin", methods=["GET"])
def Servir_Panel_Admin():
    """Sirve la página HTML del panel de administración."""
    return send_from_directory(".", "admin.html")


# ─── Autenticación ───────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/login", methods=["POST"])
def Admin_Login():
    datos = request.get_json(silent=True) or {}
    usuario  = str(datos.get("usuario", "")).strip()
    password = str(datos.get("password", "")).strip()

    if not usuario or not password:
        return jsonify({"error": "Usuario y contraseña requeridos."}), 400

    rows = Ejecutar_Consulta(
        "SELECT id, password_hash, nombre FROM administradores WHERE usuario = %s",
        (usuario,)
    )
    if not rows or not check_password_hash(rows[0]["password_hash"], password):
        return jsonify({"error": "Credenciales incorrectas."}), 401

    session[ADMIN_SESSION_KEY] = True
    session[ADMIN_USER_KEY]    = usuario
    session.permanent = True
    return jsonify({"ok": True, "nombre": rows[0].get("nombre", usuario)})


@Admin_Blueprint.route("/admin/logout", methods=["POST"])
def Admin_Logout():
    session.pop(ADMIN_SESSION_KEY, None)
    session.pop(ADMIN_USER_KEY, None)
    return jsonify({"ok": True})


@Admin_Blueprint.route("/admin/verificar", methods=["GET"])
def Admin_Verificar():
    """Comprueba si hay una sesión activa."""
    if session.get(ADMIN_SESSION_KEY):
        return jsonify({"autenticado": True, "usuario": session.get(ADMIN_USER_KEY)})
    return jsonify({"autenticado": False}), 401


# ─── CRUD Productos ───────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/productos", methods=["GET"])
@login_requerido
def Admin_Listar_Productos():
    """Lista todos los productos con su categoría."""
    pagina   = max(1, int(request.args.get("pagina", 1)))
    por_pag  = min(50, max(5, int(request.args.get("por_pagina", 20))))
    busqueda = request.args.get("busqueda", "").strip()
    offset   = (pagina - 1) * por_pag

    if busqueda:
        sql_count = """
            SELECT COUNT(*) AS total FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE p.nombre LIKE %s
        """
        sql_data = """
            SELECT p.id, p.nombre, p.precio, c.nombre AS categoria,
                   p.genero, p.color, p.stock, p.rating,
                   p.descripcion, p.imagen_url, p.activo, p.creado_en
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE p.nombre LIKE %s
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """
        param_busq = f"%{busqueda}%"
        total_rows = Ejecutar_Consulta(sql_count, (param_busq,))
        productos  = Ejecutar_Consulta(sql_data, (param_busq, por_pag, offset))
    else:
        sql_count = "SELECT COUNT(*) AS total FROM productos"
        sql_data  = """
            SELECT p.id, p.nombre, p.precio, c.nombre AS categoria,
                   p.genero, p.color, p.stock, p.rating,
                   p.descripcion, p.imagen_url, p.activo, p.creado_en
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """
        total_rows = Ejecutar_Consulta(sql_count)
        productos  = Ejecutar_Consulta(sql_data, (por_pag, offset))

    total = total_rows[0]["total"] if total_rows else 0

    # Convertir campos Decimal/datetime a tipos serializables
    for p in productos:
        p["precio"] = float(p["precio"]) if p["precio"] is not None else 0.0
        p["rating"]  = float(p["rating"])  if p["rating"]  is not None else None
        p["creado_en"] = str(p["creado_en"]) if p["creado_en"] else None

    return jsonify({
        "productos": productos,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pag,
        "total_paginas": max(1, -(-total // por_pag))  # techo de división
    })


@Admin_Blueprint.route("/admin/productos/<int:producto_id>", methods=["GET"])
@login_requerido
def Admin_Obtener_Producto(producto_id):
    """Devuelve un producto específico por ID."""
    rows = Ejecutar_Consulta(
        """
        SELECT p.id, p.nombre, p.precio, p.categoria_id,
               c.nombre AS categoria, p.genero, p.color,
               p.stock, p.rating, p.descripcion, p.imagen_url, p.activo
        FROM productos p
        JOIN categorias c ON p.categoria_id = c.id
        WHERE p.id = %s
        """,
        (producto_id,)
    )
    if not rows:
        return jsonify({"error": "Producto no encontrado."}), 404
    p = rows[0]
    p["precio"] = float(p["precio"]) if p["precio"] is not None else 0.0
    p["rating"]  = float(p["rating"])  if p["rating"]  is not None else None
    return jsonify(p)


@Admin_Blueprint.route("/admin/productos", methods=["POST"])
@login_requerido
def Admin_Crear_Producto():
    """Crea un nuevo producto."""
    d = request.get_json(silent=True) or {}

    nombre       = str(d.get("nombre", "")).strip()
    precio       = d.get("precio")
    categoria_id = d.get("categoria_id")
    genero       = d.get("genero")
    color        = d.get("color", "")
    stock        = d.get("stock", 0)
    rating       = d.get("rating")
    descripcion  = d.get("descripcion", "")
    imagen_url   = d.get("imagen_url", "")
    activo       = int(d.get("activo", 1))

    if not nombre:
        return jsonify({"error": "El nombre del producto es requerido."}), 400
    if precio is None:
        return jsonify({"error": "El precio es requerido."}), 400
    if categoria_id is None:
        return jsonify({"error": "La categoría es requerida."}), 400

    try:
        precio = float(precio)
        stock  = int(stock)
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "Precio, stock o rating con formato incorrecto."}), 400

    nuevo_id = Ejecutar_Escritura(
        """
        INSERT INTO productos
            (nombre, precio, categoria_id, genero, color, stock, rating, descripcion, imagen_url, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (nombre, precio, categoria_id, genero, color, stock, rating, descripcion, imagen_url, activo)
    )

    if nuevo_id is None:
        return jsonify({"error": "No se pudo crear el producto."}), 500

    return jsonify({"ok": True, "id": nuevo_id, "mensaje": f"Producto '{nombre}' creado correctamente."}), 201


@Admin_Blueprint.route("/admin/productos/<int:producto_id>", methods=["PUT"])
@login_requerido
def Admin_Actualizar_Producto(producto_id):
    """Actualiza un producto existente."""
    # Verificar que existe
    existente = Ejecutar_Consulta("SELECT id FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    d = request.get_json(silent=True) or {}

    campos = []
    valores = []

    mapeo = {
        "nombre":       ("nombre",       str),
        "precio":       ("precio",       float),
        "categoria_id": ("categoria_id", int),
        "genero":       ("genero",       str),
        "color":        ("color",        str),
        "stock":        ("stock",        int),
        "rating":       ("rating",       float),
        "descripcion":  ("descripcion",  str),
        "imagen_url":   ("imagen_url",   str),
        "activo":       ("activo",       int),
    }

    for clave, (col, tipo) in mapeo.items():
        if clave in d:
            val = d[clave]
            try:
                val = tipo(val) if val is not None else None
            except (TypeError, ValueError):
                return jsonify({"error": f"Valor inválido para '{clave}'."}), 400
            campos.append(f"{col} = %s")
            valores.append(val)

    if not campos:
        return jsonify({"error": "No se enviaron campos para actualizar."}), 400

    valores.append(producto_id)
    sql = f"UPDATE productos SET {', '.join(campos)} WHERE id = %s"
    Ejecutar_Escritura(sql, tuple(valores))

    return jsonify({"ok": True, "mensaje": "Producto actualizado correctamente."})


@Admin_Blueprint.route("/admin/productos/<int:producto_id>", methods=["DELETE"])
@login_requerido
def Admin_Eliminar_Producto(producto_id):
    """Elimina (desactiva) un producto. Pasa activo=0 en lugar de borrar físicamente."""
    existente = Ejecutar_Consulta("SELECT id, nombre FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    nombre = existente[0]["nombre"]

    # Eliminación lógica: marca como inactivo
    Ejecutar_Escritura("UPDATE productos SET activo = 0 WHERE id = %s", (producto_id,))

    return jsonify({"ok": True, "mensaje": f"Producto '{nombre}' desactivado correctamente."})


@Admin_Blueprint.route("/admin/productos/<int:producto_id>/restaurar", methods=["POST"])
@login_requerido
def Admin_Restaurar_Producto(producto_id):
    """Reactiva un producto previamente desactivado."""
    existente = Ejecutar_Consulta("SELECT id, nombre FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    Ejecutar_Escritura("UPDATE productos SET activo = 1 WHERE id = %s", (producto_id,))
    return jsonify({"ok": True, "mensaje": f"Producto '{existente[0]['nombre']}' reactivado."})


# ─── CRUD Categorías ──────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/categorias", methods=["GET"])
@login_requerido
def Admin_Listar_Categorias():
    """Lista todas las categorías con conteo de productos."""
    rows = Ejecutar_Consulta(
        """
        SELECT c.id, c.nombre,
               COUNT(p.id) AS total_productos
        FROM categorias c
        LEFT JOIN productos p ON p.categoria_id = c.id
        GROUP BY c.id, c.nombre
        ORDER BY c.nombre
        """
    )
    return jsonify({"categorias": rows})


@Admin_Blueprint.route("/admin/categorias", methods=["POST"])
@login_requerido
def Admin_Crear_Categoria():
    d = request.get_json(silent=True) or {}
    nombre = str(d.get("nombre", "")).strip().upper()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría es requerido."}), 400

    existe = Ejecutar_Consulta("SELECT id FROM categorias WHERE nombre = %s", (nombre,))
    if existe:
        return jsonify({"error": f"La categoría '{nombre}' ya existe."}), 409

    nuevo_id = Ejecutar_Escritura("INSERT INTO categorias (nombre) VALUES (%s)", (nombre,))
    return jsonify({"ok": True, "id": nuevo_id, "mensaje": f"Categoría '{nombre}' creada."}), 201


@Admin_Blueprint.route("/admin/categorias/<int:cat_id>", methods=["PUT"])
@login_requerido
def Admin_Actualizar_Categoria(cat_id):
    d = request.get_json(silent=True) or {}
    nombre = str(d.get("nombre", "")).strip().upper()
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400

    existente = Ejecutar_Consulta("SELECT id FROM categorias WHERE id = %s", (cat_id,))
    if not existente:
        return jsonify({"error": "Categoría no encontrada."}), 404

    Ejecutar_Escritura("UPDATE categorias SET nombre = %s WHERE id = %s", (nombre, cat_id))
    return jsonify({"ok": True, "mensaje": "Categoría actualizada."})


@Admin_Blueprint.route("/admin/categorias/<int:cat_id>", methods=["DELETE"])
@login_requerido
def Admin_Eliminar_Categoria(cat_id):
    en_uso = Ejecutar_Consulta(
        "SELECT COUNT(*) AS n FROM productos WHERE categoria_id = %s", (cat_id,)
    )
    if en_uso and en_uso[0]["n"] > 0:
        return jsonify({"error": "No se puede eliminar: la categoría tiene productos asignados."}), 409

    existente = Ejecutar_Consulta("SELECT nombre FROM categorias WHERE id = %s", (cat_id,))
    if not existente:
        return jsonify({"error": "Categoría no encontrada."}), 404

    Ejecutar_Escritura("DELETE FROM categorias WHERE id = %s", (cat_id,))
    return jsonify({"ok": True, "mensaje": f"Categoría '{existente[0]['nombre']}' eliminada."})


# ─── Stock ────────────────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/stock", methods=["GET"])
@login_requerido
def Admin_Ver_Stock():
    """
    Devuelve el stock de todos los productos.
    Parámetro: ?alerta=1  → solo los que tienen stock <= umbral (por defecto 10)
    """
    solo_alerta = request.args.get("alerta", "0") == "1"
    umbral      = int(request.args.get("umbral", 10))

    if solo_alerta:
        sql = """
            SELECT p.id, p.nombre, p.stock, c.nombre AS categoria, p.activo
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE p.stock <= %s
            ORDER BY p.stock ASC, p.nombre
        """
        rows = Ejecutar_Consulta(sql, (umbral,))
    else:
        sql = """
            SELECT p.id, p.nombre, p.stock, c.nombre AS categoria, p.activo
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.stock ASC, p.nombre
        """
        rows = Ejecutar_Consulta(sql)

    return jsonify({"stock": rows, "total": len(rows)})


@Admin_Blueprint.route("/admin/stock/<int:producto_id>", methods=["PATCH"])
@login_requerido
def Admin_Actualizar_Stock(producto_id):
    """Actualiza solo el stock de un producto."""
    d = request.get_json(silent=True) or {}
    try:
        nuevo_stock = int(d.get("stock", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Stock debe ser un número entero."}), 400

    if nuevo_stock < 0:
        return jsonify({"error": "El stock no puede ser negativo."}), 400

    existente = Ejecutar_Consulta("SELECT id FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    Ejecutar_Escritura("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))
    return jsonify({"ok": True, "mensaje": f"Stock actualizado a {nuevo_stock}."})


# ─── Ventas: registrar ─────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/ventas/registrar", methods=["POST"])
def Admin_Registrar_Venta():
    """
    Registra una venta con su detalle.
    Body: { "sesion_id": "...", "carrito": [ {id, nombre, precio, cantidad}, ... ] }
    """
    datos   = request.get_json(silent=True) or {}
    carrito = datos.get("carrito", [])

    if not carrito:
        return jsonify({"error": "Carrito vacío."}), 400

    total_venta  = 0.0
    items_validos = []

    for item in carrito:
        try:
            cantidad = int(item.get("quantity", item.get("cantidad", 1)))
            precio   = float(item.get("price",    item.get("precio",   0)))
            prod_id  = int(item.get("id", 0))
            nombre   = str(item.get("name", item.get("nombre", "Producto")))
            subtotal = precio * cantidad
            total_venta += subtotal
            items_validos.append((prod_id, nombre, precio, cantidad, subtotal))
        except (TypeError, ValueError):
            continue

    if not items_validos:
        return jsonify({"error": "No se pudo procesar ningún item del carrito."}), 400

    sesion_id = str(datos.get("sesion_id", "anon"))

    # Insertar cabecera de venta
    venta_id = Ejecutar_Escritura(
        "INSERT INTO ventas (sesion_id, total, cantidad_items) VALUES (%s, %s, %s)",
        (sesion_id, round(total_venta, 2), len(items_validos))
    )

    if venta_id is None:
        return jsonify({"error": "No se pudo registrar la venta."}), 500

    # Insertar detalle y descontar stock
    for prod_id, nombre, precio, cantidad, subtotal in items_validos:
        Ejecutar_Escritura(
            """
            INSERT INTO venta_detalle
                (venta_id, producto_id, nombre_producto, precio_unitario, cantidad, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (venta_id, prod_id, nombre, precio, cantidad, round(subtotal, 2))
        )
        # Descontar stock (no bajar de 0)
        Ejecutar_Escritura(
            "UPDATE productos SET stock = GREATEST(0, stock - %s) WHERE id = %s",
            (cantidad, prod_id)
        )

    return jsonify({"ok": True, "venta_id": venta_id, "total": round(total_venta, 2)})


# ─── Reportes ─────────────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/reportes/ventas", methods=["GET"])
@login_requerido
def Admin_Reporte_Ventas():
    """
    Reporte de ventas agrupado.
    Parámetros:
        ?periodo=diario   → últimos 30 días, agrupado por día
        ?periodo=semanal  → últimas 12 semanas, agrupado por semana
        ?periodo=mensual  → últimos 12 meses, agrupado por mes (por defecto)
    """
    periodo = request.args.get("periodo", "diario").lower()

    if periodo == "diario":
        sql = """
            SELECT
                DATE(fecha)          AS etiqueta,
                COUNT(*)             AS cantidad_ventas,
                SUM(total)           AS monto_total,
                SUM(cantidad_items)  AS items_vendidos
            FROM ventas
            WHERE fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(fecha)
            ORDER BY etiqueta ASC
        """
    elif periodo == "semanal":
        sql = """
            SELECT
                CONCAT(YEAR(fecha), '-S', LPAD(WEEK(fecha,1), 2, '0')) AS etiqueta,
                COUNT(*)             AS cantidad_ventas,
                SUM(total)           AS monto_total,
                SUM(cantidad_items)  AS items_vendidos
            FROM ventas
            WHERE fecha >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
            GROUP BY YEAR(fecha), WEEK(fecha,1)
            ORDER BY YEAR(fecha) ASC, WEEK(fecha,1) ASC
        """
    else:  # mensual
        sql = """
            SELECT
                DATE_FORMAT(fecha, '%Y-%m') AS etiqueta,
                COUNT(*)             AS cantidad_ventas,
                SUM(total)           AS monto_total,
                SUM(cantidad_items)  AS items_vendidos
            FROM ventas
            WHERE fecha >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(fecha, '%Y-%m')
            ORDER BY etiqueta ASC
        """

    rows = Ejecutar_Consulta(sql)

    # Convertir Decimal a float para JSON
    for r in rows:
        r["monto_total"] = float(r["monto_total"]) if r["monto_total"] else 0.0
        r["etiqueta"]    = str(r["etiqueta"])

    return jsonify({"periodo": periodo, "datos": rows})


@Admin_Blueprint.route("/admin/reportes/resumen", methods=["GET"])
@login_requerido
def Admin_Resumen():
    """Resumen general para el dashboard de administración."""
    total_productos  = Ejecutar_Consulta("SELECT COUNT(*) AS n FROM productos WHERE activo=1")
    total_categorias = Ejecutar_Consulta("SELECT COUNT(*) AS n FROM categorias")
    stock_critico    = Ejecutar_Consulta("SELECT COUNT(*) AS n FROM productos WHERE stock <= 5 AND activo=1")

    ventas_hoy   = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE DATE(fecha)=CURDATE()")
    ventas_mes   = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE MONTH(fecha)=MONTH(NOW()) AND YEAR(fecha)=YEAR(NOW())")
    ventas_total = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas")

    def _val(rows, campo):
        return rows[0][campo] if rows else 0

    return jsonify({
        "total_productos":  _val(total_productos, "n"),
        "total_categorias": _val(total_categorias, "n"),
        "stock_critico":    _val(stock_critico, "n"),
        "ventas_hoy":       {"cantidad": _val(ventas_hoy, "n"),   "monto": float(_val(ventas_hoy, "monto"))},
        "ventas_mes":       {"cantidad": _val(ventas_mes, "n"),   "monto": float(_val(ventas_mes, "monto"))},
        "ventas_total":     {"cantidad": _val(ventas_total, "n"), "monto": float(_val(ventas_total, "monto"))},
    })


@Admin_Blueprint.route("/admin/reportes/top_productos", methods=["GET"])
@login_requerido
def Admin_Top_Productos():
    """Top 10 productos más vendidos."""
    rows = Ejecutar_Consulta(
        """
        SELECT
            vd.producto_id,
            vd.nombre_producto,
            SUM(vd.cantidad)  AS unidades_vendidas,
            SUM(vd.subtotal)  AS ingresos
        FROM venta_detalle vd
        GROUP BY vd.producto_id, vd.nombre_producto
        ORDER BY unidades_vendidas DESC
        LIMIT 10
        """
    )
    for r in rows:
        r["ingresos"] = float(r["ingresos"]) if r["ingresos"] else 0.0
    return jsonify({"top_productos": rows})


# ─── Upload Imagen ───────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/productos/upload_imagen", methods=["POST"])
@login_requerido
def Admin_Upload_Imagen():
    """Recibe un archivo imagen y lo guarda en data/uploads/. Retorna la URL."""
    if 'imagen' not in request.files:
        return jsonify({"error": "No se envió archivo."}), 400

    archivo = request.files['imagen']
    if archivo.filename == '':
        return jsonify({"error": "Archivo sin nombre."}), 400
    if not _ext_permitida(archivo.filename):
        return jsonify({"error": "Extensión no permitida. Usa PNG, JPG, JPEG, GIF o WEBP."}), 400

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    ext = archivo.filename.rsplit('.', 1)[1].lower()
    nombre_seguro = f"{uuid.uuid4().hex}.{ext}"
    ruta = os.path.join(UPLOADS_DIR, nombre_seguro)
    archivo.save(ruta)
    url = f"/uploads/{nombre_seguro}"
    return jsonify({"ok": True, "url": url})


# ─── Reporte PDF ──────────────────────────────────────────────────────────────

@Admin_Blueprint.route("/admin/reportes/pdf", methods=["GET"])
@login_requerido
def Admin_Reporte_PDF():
    """Genera y descarga un PDF con resumen de ventas y top productos."""
    # Datos resumen
    resumen_v = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE DATE(fecha)=CURDATE()")
    resumen_m = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE MONTH(fecha)=MONTH(NOW()) AND YEAR(fecha)=YEAR(NOW())")
    resumen_t = Ejecutar_Consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas")

    # Ventas últimos 30 días
    ventas_rows = Ejecutar_Consulta(
        "SELECT DATE(fecha) AS dia, COUNT(*) AS cant, SUM(total) AS monto "
        "FROM ventas WHERE fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY) "
        "GROUP BY DATE(fecha) ORDER BY dia ASC"
    )

    # Top productos
    top_rows = Ejecutar_Consulta(
        "SELECT vd.nombre_producto, SUM(vd.cantidad) AS unidades, SUM(vd.subtotal) AS ingresos "
        "FROM venta_detalle vd GROUP BY vd.nombre_producto "
        "ORDER BY unidades DESC LIMIT 10"
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=40, rightMargin=40,
                            topMargin=50, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    # Título
    story.append(Paragraph("SENATI Sports – Reporte de Ventas", styles['Title']))
    story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 16))

    # Resumen cards
    def _v(rows, campo):
        return rows[0][campo] if rows else 0

    resumen_data = [
        ['Período', 'Ventas', 'Monto Total'],
        ['Hoy',          str(_v(resumen_v,'n')), f"S/ {float(_v(resumen_v,'monto')):.2f}"],
        ['Este mes',     str(_v(resumen_m,'n')), f"S/ {float(_v(resumen_m,'monto')):.2f}"],
        ['Total historial', str(_v(resumen_t,'n')), f"S/ {float(_v(resumen_t,'monto')):.2f}"],
    ]
    t_res = Table(resumen_data, colWidths=[180, 100, 120])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c63ff')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f4f4ff'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ccccdd')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_res)
    story.append(Spacer(1, 20))

    # Tabla ventas diarias
    story.append(Paragraph("Ventas últimos 30 días", styles['Heading2']))
    story.append(Spacer(1, 8))
    if ventas_rows:
        v_data = [['Fecha', 'Nº Ventas', 'Monto']]
        for r in ventas_rows:
            v_data.append([str(r['dia']), str(r['cant']), f"S/ {float(r['monto']):.2f}"])
        t_v = Table(v_data, colWidths=[160, 100, 120])
        t_v.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#252840')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f8ff'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#ccccdd')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_v)
    else:
        story.append(Paragraph("Sin ventas registradas en los últimos 30 días.", styles['Normal']))
    story.append(Spacer(1, 20))

    # Top 10
    story.append(Paragraph("Top 10 Productos más vendidos", styles['Heading2']))
    story.append(Spacer(1, 8))
    if top_rows:
        top_data = [['Producto', 'Unidades', 'Ingresos']]
        for r in top_rows:
            top_data.append([str(r['nombre_producto'])[:45], str(r['unidades']), f"S/ {float(r['ingresos']):.2f}"])
        t_top = Table(top_data, colWidths=[280, 80, 100])
        t_top.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#00d4aa')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.HexColor('#111111')),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f0fff8'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#aaeedd')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_top)
    else:
        story.append(Paragraph("Sin productos vendidos aún.", styles['Normal']))

    doc.build(story)
    buf.seek(0)
    nombre_archivo = f"reporte_ventas_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=nombre_archivo)


# ─── Inicialización ───────────────────────────────────────────────────────────

def Inicializar_Admin(app):
    """
    Registra el blueprint de administración y configura la sesión.
    Llamar desde app.py: admin.Inicializar_Admin(app)
    """
    if not app.secret_key:
        app.secret_key = os.getenv("FLASK_SECRET_KEY", "senati_admin_secret_2024")
    app.register_blueprint(Admin_Blueprint)
    with app.app_context():
        _init_admin_default()
    print("[ADMIN] Módulo de administración registrado en /admin")
