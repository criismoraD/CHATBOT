"""
admin.py  ·  Módulo de Administración para el Chatbot Tienda
-------------------------------------------------------------
Provee rutas Flask para:
  - Login / Logout de administrador
  - CRUD de Productos (Crear, Leer, Actualizar, Eliminar)
  - CRUD de Categorías
  - Reportes de ventas (diario, semanal, mensual)
  - Stock de productos
  - Registrar ventas desde el carrito

Uso: importar y registrar en app.py con:
    from admin import admin_bp
    app.register_blueprint(admin_bp)
"""

import os
import functools
from flask import (
    Blueprint, request, jsonify, session,
    send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import ejecutar_consulta, ejecutar_escritura, get_connection
from mysql.connector import Error

# ─── Blueprint ────────────────────────────────────────────────────────────────
admin_bp = Blueprint("admin", __name__)

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
        rows = ejecutar_consulta("SELECT id, password_hash FROM administradores WHERE usuario = 'admin'")
        hash_ok = generate_password_hash("admin123")
        if not rows:
            ejecutar_escritura(
                "INSERT INTO administradores (usuario, password_hash, nombre) VALUES (%s, %s, %s)",
                ("admin", hash_ok, "Administrador")
            )
            print("[ADMIN] Usuario 'admin' creado con contraseña 'admin123'.")
        elif "placeholder" in rows[0].get("password_hash", ""):
            ejecutar_escritura(
                "UPDATE administradores SET password_hash = %s WHERE usuario = 'admin'",
                (hash_ok,)
            )
            print("[ADMIN] Hash del admin actualizado.")
    except Exception as e:
        print(f"[ADMIN] No se pudo inicializar admin por defecto: {e}")


# ─── Servir panel HTML ────────────────────────────────────────────────────────

@admin_bp.route("/admin", methods=["GET"])
def Servir_Panel_Admin():
    """Sirve la página HTML del panel de administración."""
    return send_from_directory(".", "admin.html")


# ─── Autenticación ───────────────────────────────────────────────────────────

@admin_bp.route("/admin/login", methods=["POST"])
def Admin_Login():
    datos = request.get_json(silent=True) or {}
    usuario  = str(datos.get("usuario", "")).strip()
    password = str(datos.get("password", "")).strip()

    if not usuario or not password:
        return jsonify({"error": "Usuario y contraseña requeridos."}), 400

    rows = ejecutar_consulta(
        "SELECT id, password_hash, nombre FROM administradores WHERE usuario = %s",
        (usuario,)
    )
    if not rows or not check_password_hash(rows[0]["password_hash"], password):
        return jsonify({"error": "Credenciales incorrectas."}), 401

    session[ADMIN_SESSION_KEY] = True
    session[ADMIN_USER_KEY]    = usuario
    session.permanent = True
    return jsonify({"ok": True, "nombre": rows[0].get("nombre", usuario)})


@admin_bp.route("/admin/logout", methods=["POST"])
def Admin_Logout():
    session.pop(ADMIN_SESSION_KEY, None)
    session.pop(ADMIN_USER_KEY, None)
    return jsonify({"ok": True})


@admin_bp.route("/admin/verificar", methods=["GET"])
def Admin_Verificar():
    """Comprueba si hay una sesión activa."""
    if session.get(ADMIN_SESSION_KEY):
        return jsonify({"autenticado": True, "usuario": session.get(ADMIN_USER_KEY)})
    return jsonify({"autenticado": False}), 401


# ─── CRUD Productos ───────────────────────────────────────────────────────────

@admin_bp.route("/admin/productos", methods=["GET"])
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
        total_rows = ejecutar_consulta(sql_count, (param_busq,))
        productos  = ejecutar_consulta(sql_data, (param_busq, por_pag, offset))
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
        total_rows = ejecutar_consulta(sql_count)
        productos  = ejecutar_consulta(sql_data, (por_pag, offset))

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


@admin_bp.route("/admin/productos/<int:producto_id>", methods=["GET"])
@login_requerido
def Admin_Obtener_Producto(producto_id):
    """Devuelve un producto específico por ID."""
    rows = ejecutar_consulta(
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


@admin_bp.route("/admin/productos", methods=["POST"])
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

    nuevo_id = ejecutar_escritura(
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


@admin_bp.route("/admin/productos/<int:producto_id>", methods=["PUT"])
@login_requerido
def Admin_Actualizar_Producto(producto_id):
    """Actualiza un producto existente."""
    # Verificar que existe
    existente = ejecutar_consulta("SELECT id FROM productos WHERE id = %s", (producto_id,))
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
    ejecutar_escritura(sql, tuple(valores))

    return jsonify({"ok": True, "mensaje": "Producto actualizado correctamente."})


@admin_bp.route("/admin/productos/<int:producto_id>", methods=["DELETE"])
@login_requerido
def Admin_Eliminar_Producto(producto_id):
    """Elimina (desactiva) un producto. Pasa activo=0 en lugar de borrar físicamente."""
    existente = ejecutar_consulta("SELECT id, nombre FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    nombre = existente[0]["nombre"]

    # Eliminación lógica: marca como inactivo
    ejecutar_escritura("UPDATE productos SET activo = 0 WHERE id = %s", (producto_id,))

    return jsonify({"ok": True, "mensaje": f"Producto '{nombre}' desactivado correctamente."})


@admin_bp.route("/admin/productos/<int:producto_id>/restaurar", methods=["POST"])
@login_requerido
def Admin_Restaurar_Producto(producto_id):
    """Reactiva un producto previamente desactivado."""
    existente = ejecutar_consulta("SELECT id, nombre FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    ejecutar_escritura("UPDATE productos SET activo = 1 WHERE id = %s", (producto_id,))
    return jsonify({"ok": True, "mensaje": f"Producto '{existente[0]['nombre']}' reactivado."})


# ─── CRUD Categorías ──────────────────────────────────────────────────────────

@admin_bp.route("/admin/categorias", methods=["GET"])
@login_requerido
def Admin_Listar_Categorias():
    """Lista todas las categorías con conteo de productos."""
    rows = ejecutar_consulta(
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


@admin_bp.route("/admin/categorias", methods=["POST"])
@login_requerido
def Admin_Crear_Categoria():
    d = request.get_json(silent=True) or {}
    nombre = str(d.get("nombre", "")).strip().upper()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría es requerido."}), 400

    existe = ejecutar_consulta("SELECT id FROM categorias WHERE nombre = %s", (nombre,))
    if existe:
        return jsonify({"error": f"La categoría '{nombre}' ya existe."}), 409

    nuevo_id = ejecutar_escritura("INSERT INTO categorias (nombre) VALUES (%s)", (nombre,))
    return jsonify({"ok": True, "id": nuevo_id, "mensaje": f"Categoría '{nombre}' creada."}), 201


@admin_bp.route("/admin/categorias/<int:cat_id>", methods=["PUT"])
@login_requerido
def Admin_Actualizar_Categoria(cat_id):
    d = request.get_json(silent=True) or {}
    nombre = str(d.get("nombre", "")).strip().upper()
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400

    existente = ejecutar_consulta("SELECT id FROM categorias WHERE id = %s", (cat_id,))
    if not existente:
        return jsonify({"error": "Categoría no encontrada."}), 404

    ejecutar_escritura("UPDATE categorias SET nombre = %s WHERE id = %s", (nombre, cat_id))
    return jsonify({"ok": True, "mensaje": "Categoría actualizada."})


@admin_bp.route("/admin/categorias/<int:cat_id>", methods=["DELETE"])
@login_requerido
def Admin_Eliminar_Categoria(cat_id):
    en_uso = ejecutar_consulta(
        "SELECT COUNT(*) AS n FROM productos WHERE categoria_id = %s", (cat_id,)
    )
    if en_uso and en_uso[0]["n"] > 0:
        return jsonify({"error": "No se puede eliminar: la categoría tiene productos asignados."}), 409

    existente = ejecutar_consulta("SELECT nombre FROM categorias WHERE id = %s", (cat_id,))
    if not existente:
        return jsonify({"error": "Categoría no encontrada."}), 404

    ejecutar_escritura("DELETE FROM categorias WHERE id = %s", (cat_id,))
    return jsonify({"ok": True, "mensaje": f"Categoría '{existente[0]['nombre']}' eliminada."})


# ─── Stock ────────────────────────────────────────────────────────────────────

@admin_bp.route("/admin/stock", methods=["GET"])
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
        rows = ejecutar_consulta(sql, (umbral,))
    else:
        sql = """
            SELECT p.id, p.nombre, p.stock, c.nombre AS categoria, p.activo
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.stock ASC, p.nombre
        """
        rows = ejecutar_consulta(sql)

    return jsonify({"stock": rows, "total": len(rows)})


@admin_bp.route("/admin/stock/<int:producto_id>", methods=["PATCH"])
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

    existente = ejecutar_consulta("SELECT id FROM productos WHERE id = %s", (producto_id,))
    if not existente:
        return jsonify({"error": "Producto no encontrado."}), 404

    ejecutar_escritura("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))
    return jsonify({"ok": True, "mensaje": f"Stock actualizado a {nuevo_stock}."})


# ─── Ventas: registrar ─────────────────────────────────────────────────────────

@admin_bp.route("/admin/ventas/registrar", methods=["POST"])
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
    venta_id = ejecutar_escritura(
        "INSERT INTO ventas (sesion_id, total, cantidad_items) VALUES (%s, %s, %s)",
        (sesion_id, round(total_venta, 2), len(items_validos))
    )

    if venta_id is None:
        return jsonify({"error": "No se pudo registrar la venta."}), 500

    # Insertar detalle y descontar stock
    for prod_id, nombre, precio, cantidad, subtotal in items_validos:
        ejecutar_escritura(
            """
            INSERT INTO venta_detalle
                (venta_id, producto_id, nombre_producto, precio_unitario, cantidad, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (venta_id, prod_id, nombre, precio, cantidad, round(subtotal, 2))
        )
        # Descontar stock (no bajar de 0)
        ejecutar_escritura(
            "UPDATE productos SET stock = GREATEST(0, stock - %s) WHERE id = %s",
            (cantidad, prod_id)
        )

    return jsonify({"ok": True, "venta_id": venta_id, "total": round(total_venta, 2)})


# ─── Reportes ─────────────────────────────────────────────────────────────────

@admin_bp.route("/admin/reportes/ventas", methods=["GET"])
@login_requerido
def Admin_Reporte_Ventas():
    """
    Reporte de ventas agrupado.
    Parámetros:
        ?periodo=diario   → últimos 30 días, agrupado por día
        ?periodo=semanal  → últimas 12 semanas, agrupado por semana
        ?periodo=mensual  → últimos 12 meses, agrupado por mes (por defecto)
    """
    periodo = request.args.get("periodo", "mensual").lower()

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

    rows = ejecutar_consulta(sql)

    # Convertir Decimal a float para JSON
    for r in rows:
        r["monto_total"] = float(r["monto_total"]) if r["monto_total"] else 0.0
        r["etiqueta"]    = str(r["etiqueta"])

    return jsonify({"periodo": periodo, "datos": rows})


@admin_bp.route("/admin/reportes/resumen", methods=["GET"])
@login_requerido
def Admin_Resumen():
    """Resumen general para el dashboard de administración."""
    total_productos  = ejecutar_consulta("SELECT COUNT(*) AS n FROM productos WHERE activo=1")
    total_categorias = ejecutar_consulta("SELECT COUNT(*) AS n FROM categorias")
    stock_critico    = ejecutar_consulta("SELECT COUNT(*) AS n FROM productos WHERE stock <= 5 AND activo=1")

    ventas_hoy   = ejecutar_consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE DATE(fecha)=CURDATE()")
    ventas_mes   = ejecutar_consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas WHERE MONTH(fecha)=MONTH(NOW()) AND YEAR(fecha)=YEAR(NOW())")
    ventas_total = ejecutar_consulta("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS monto FROM ventas")

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


@admin_bp.route("/admin/reportes/top_productos", methods=["GET"])
@login_requerido
def Admin_Top_Productos():
    """Top 10 productos más vendidos."""
    rows = ejecutar_consulta(
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


# ─── Inicialización ───────────────────────────────────────────────────────────

def init_admin(app):
    """
    Registra el blueprint y configura la clave secreta para sesiones.
    Llamar desde app.py: admin.init_admin(app)
    """
    if not app.secret_key:
        app.secret_key = os.getenv("FLASK_SECRET_KEY", "senati_admin_secret_2024")
    app.register_blueprint(admin_bp)
    with app.app_context():
        _init_admin_default()
    print("[ADMIN] Módulo de administración registrado en /admin")
