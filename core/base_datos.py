"""
core/base_datos.py · Capa de Conexión MySQL
═══════════════════════════════════════════

Centraliza la conexión a la base de datos mediante un pool de conexiones
y expone helpers reutilizables para consultas y escrituras.

FLUJO:
  1. Al primer uso, Crear_Pool_De_Conexiones() crea un pool de 5 conexiones
  2. Obtener_Conexion() devuelve una conexión del pool (la reutiliza)
  3. Ejecutar_Consulta(sql, params) → lista de diccionarios (SELECT)
  4. Ejecutar_Escritura(sql, params) → lastrowid (INSERT/UPDATE/DELETE)
  5. La conexión se devuelve al pool automáticamente al cerrar

CONFIGURACIÓN:
  Lee DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME de:
  1. Variables de entorno (prioridad alta)
  2. core.configuracion (defaults)

USO:
  from core.base_datos import Ejecutar_Consulta, Ejecutar_Escritura
  productos = Ejecutar_Consulta("SELECT * FROM productos WHERE activo = 1")
"""

import os
import mysql.connector
from mysql.connector import pooling, Error
from core import config


# ─── Pool de Conexiones ──────────────────────────────────────────────────────

_Pool_De_Conexiones = None


def Crear_Pool_De_Conexiones():
    """Crea el pool de conexiones a MySQL (máx. 5 conexiones reutilizables)."""
    global _Pool_De_Conexiones
    _Pool_De_Conexiones = pooling.MySQLConnectionPool(
        pool_name="chatbot_pool",
        pool_size=5,
        host      = os.getenv("DB_HOST",     config.DB_HOST),
        port      = int(os.getenv("DB_PORT", config.DB_PORT)),
        user      = os.getenv("DB_USER",     config.DB_USER),
        password  = os.getenv("DB_PASSWORD", config.DB_PASSWORD),
        database  = os.getenv("DB_NAME",     config.DB_NAME),
        charset   = "utf8mb4",
        collation = "utf8mb4_unicode_ci",
        autocommit=True,
    )
    return _Pool_De_Conexiones


def Obtener_Conexion():
    """Devuelve una conexión del pool. Lo crea si es la primera vez."""
    global _Pool_De_Conexiones
    if _Pool_De_Conexiones is None:
        Crear_Pool_De_Conexiones()
    return _Pool_De_Conexiones.get_connection()


# ─── Helpers de Consulta ─────────────────────────────────────────────────────

def Ejecutar_Consulta(sql: str, params: tuple = ()):
    """
    Ejecuta una sentencia SELECT y retorna una lista de diccionarios.
    """
    Conexion = None
    try:
        Conexion = Obtener_Conexion()
        Cursor = Conexion.cursor(dictionary=True)
        Cursor.execute(sql, params)
        return Cursor.fetchall()
    except Error as Error_De_DB:
        print(f"[DB ERROR] {Error_De_DB}\nSQL: {sql}\nParams: {params}")
        return []
    finally:
        if Conexion and Conexion.is_connected():
            Conexion.close()


def Ejecutar_Escritura(sql: str, params: tuple = ()):
    """
    Ejecuta una sentencia INSERT/UPDATE/DELETE.
    Retorna el lastrowid (ID del último registro insertado) o None.
    """
    Conexion = None
    try:
        Conexion = Obtener_Conexion()
        Cursor = Conexion.cursor()
        Cursor.execute(sql, params)
        Conexion.commit()
        return Cursor.lastrowid
    except Error as Error_De_DB:
        print(f"[DB ERROR escritura] {Error_De_DB}")
        return None
    finally:
        if Conexion and Conexion.is_connected():
            Conexion.close()


def Probar_Conexion() -> bool:
    """Retorna True si la base de datos es accesible."""
    try:
        Conexion = Obtener_Conexion()
        Conexion.close()
        return True
    except Error as Error_De_DB:
        print(f"[DB] No se pudo conectar: {Error_De_DB}")
        return False
