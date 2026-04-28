# CHATBOT Tienda Deportiva · Migración MySQL

## Archivos nuevos / modificados

| Archivo | Qué cambió |
|---|---|
| `db.py` | **NUEVO** · Pool de conexiones MySQL, helpers `ejecutar_consulta` y `ejecutar_escritura` |
| `config.py` | Agrega `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_FUENTE_CATALOGO` |
| `catalogo.py` | Carga productos desde MySQL; respaldo automático al JSON si MySQL no está disponible |
| `memoria.py` | Guarda historial de chat en tabla `sesiones_chat`; respaldo a shelve si no hay MySQL |
| `esquema_base_datos_tienda.sql` | **NUEVO** · Base de datos completa: 204 productos, colores, tallas, vistas y procedimientos |
| `dependencias_python.txt` | Agrega `mysql-connector-python>=8.3.0` |

---

## Instalación rápida

### 1. Instalar dependencias
```bash
pip install -r dependencias_python.txt
```

### 2. Importar la base de datos
```bash
mysql -u root -p < esquema_base_datos_tienda.sql
```

### 3. Configurar credenciales
Edita `config.py`:
```python
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "tu_contraseña"
DB_NAME     = "chatbot_tienda"
```
O usa variables de entorno: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

### 4. Ejecutar
```bash
python servidor_principal.py
```

---

## Estructura de la base de datos

```
categorias          → 4 categorías (CALZADO, POLOS, PANTALONES, ACCESORIOS)
productos           → 204 productos con precio, stock, rating, imagen
producto_colores    → 809 registros (colores disponibles por producto)
producto_tallas     → 805 registros (tallas disponibles por producto)
sesiones_chat       → historial de conversaciones del chatbot
```

### Vista útil
```sql
SELECT * FROM vista_productos_completa WHERE categoria = 'CALZADO' LIMIT 5;
```

### Procedimiento de búsqueda
```sql
CALL buscar_productos('zapatilla', 'CALZADO', 'Mujer', NULL, NULL, NULL, 200.00);
```

---

## Modo respaldo (sin MySQL)
Si MySQL no está disponible al iniciar, el chatbot carga automáticamente
`data/products_scraped.json` y usa `shelve` para el historial. No se pierde
ninguna funcionalidad.
