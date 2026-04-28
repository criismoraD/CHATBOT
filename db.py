"""
db.py  ·  Capa de conexión MySQL para el Chatbot
-------------------------------------------------
Centraliza la conexión y expone helpers reutilizables.
Configurar credenciales en config.py o variables de entorno.
"""

import os
import mysql.connector
from mysql.connector import pooling, Error
import config

# ─── Pool de conexiones (reutiliza conexiones, evita overhead) ────────────────
_pool = None


def _crear_pool():
    global _pool
    _pool = pooling.MySQLConnectionPool(
        pool_name="chatbot_pool",
        pool_size=5,
        host     = os.getenv("DB_HOST",     config.DB_HOST),
        port     = int(os.getenv("DB_PORT", config.DB_PORT)),
        user     = os.getenv("DB_USER",     config.DB_USER),
        password = os.getenv("DB_PASSWORD", config.DB_PASSWORD),
        database = os.getenv("DB_NAME",     config.DB_NAME),
        charset  = "utf8mb4",
        collation= "utf8mb4_unicode_ci",
        autocommit=True,
    )
    return _pool


def get_connection():
    """Devuelve una conexión del pool. Crear el pool la primera vez."""
    global _pool
    if _pool is None:
        _crear_pool()
    return _pool.get_connection()


def ejecutar_consulta(sql: str, params: tuple = (), many: bool = False):
    """
    Ejecuta una SELECT y retorna lista de dicts.
    many=False  → retorna list[dict]
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Error as e:
        print(f"[DB ERROR] {e}\nSQL: {sql}\nParams: {params}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()


def ejecutar_escritura(sql: str, params: tuple = ()):
    """
    Ejecuta INSERT/UPDATE/DELETE. Retorna lastrowid.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR escritura] {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()


def probar_conexion() -> bool:
    """Retorna True si la BD es accesible."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Error as e:
        print(f"[DB] No se pudo conectar: {e}")
        return False
