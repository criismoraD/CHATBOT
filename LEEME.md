# SENATI SPORTS - Chatbot + Panel de Administración

Proyecto completo integrado: chatbot de tienda + módulo de administración.

---

## 📁 Estructura del proyecto

```
proyecto/
├── app.py                        ← Servidor principal (ya integrado con admin)
├── admin.py                      ← Módulo de administración (backend)
├── panel_administracion.html                    ← Panel de administración (frontend)
├── chatbot_tienda_completo.sql   ← Base de datos COMPLETA (importar solo este)
├── core/configuracion.py
├── core/base_datos.py
├── bot/catalogo_productos.py
├── bot/motor_dialogo.py
├── bot/inteligencia_artificial.py
├── bot/memoria_conversacion.py
├── bot/extractor_entidades.py
├── core/procesamiento_lenguaje.py
├── entrenar_modelo_lstm.py
├── interfaz_chatbot.html
├── dependencias_python.txt
├── css/
├── js/
└── data/
```

---

## 🚀 Pasos para ejecutar

### 1. Importar la base de datos
Importar **solo** el archivo `chatbot_tienda_completo.sql` (ya incluye todo):

```bash
mysql -u root -p < chatbot_tienda_completo.sql
```

O desde phpMyAdmin: importar el archivo `chatbot_tienda_completo.sql`.

### 2. Instalar dependencias Python

```bash
pip install -r dependencias_python.txt
```

### 3. Ejecutar el servidor

```bash
python app.py
```

---

## 🔗 URLs disponibles

| URL | Descripción |
|-----|-------------|
| `http://localhost:5000/` | Tienda / Chatbot (frontend principal) |
| `http://localhost:5000/admin` | **Panel de Administración** |
| `http://localhost:5000/status` | Estado del servidor |

---

## 🔐 Credenciales del panel de administración

| Campo | Valor |
|-------|-------|
| Usuario | `admin` |
| Contraseña | `admin123` |

> El hash de la contraseña se genera automáticamente la primera vez que arranca el servidor.

---

## ✅ Funciones del panel de administración

- **Dashboard**: resumen de ventas del día, mes y total, productos activos, stock crítico
- **Productos**: CRUD completo (crear, ver, editar, eliminar/restaurar), paginación y búsqueda
- **Categorías**: CRUD completo
- **Stock**: ver todos los productos con su stock, alertas de stock crítico (≤10 unidades)
- **Reportes**: gráficos de ventas diarias, semanales o mensuales
- **Top Productos**: los 10 más vendidos

Las ventas se registran automáticamente cada vez que se genera una boleta PDF desde la tienda.
