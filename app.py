import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from ia import Modelo_IA, Etiquetas_De_Intencion, Modelo_Voz
from catalogo import (
    Datos_De_Productos, Catalogos_De_Productos, Fuente_Activa_De_Catalogo,
    Cambiar_Fuente_De_Catalogo, Buscar_Productos, Obtener_Producto_Por_Id
)
from memoria import Obtener_Contexto, Actualizar_Contexto
from dialogo import Obtener_Respuesta_Principal

app = Flask(__name__)

# Configuración de CORS: Permitir cualquier origen para desarrollo local.
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "products_active": len(Datos_De_Productos),
        "products_auto": len(Catalogos_De_Productos.get("auto", [])),
        "products_scraped": len(Catalogos_De_Productos.get("scraped", [])),
        "catalog_source_active": Fuente_Activa_De_Catalogo,
        "ai_model": "PyTorch loaded" if Modelo_IA else "Not loaded",
        "tags": Etiquetas_De_Intencion
    })


@app.route('/chat', methods=['POST'])
def chat():
    Datos_Usuario = request.get_json(silent=True) or {}
    mensaje = str(Datos_Usuario.get('message', '')).strip()
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
                "bot_name": "Asistente SENATI",
                "catalog_source": Fuente_Usada,
            })
        
    if not mensaje:
        return jsonify({"error": "No se recibio mensaje"}), 400

    Respuesta_Bot, Etiqueta_Bot, Accion_De_Filtro = Obtener_Respuesta_Principal(Id_De_Sesion_Actual, mensaje)

    Resultado_Json = {
        "response": Respuesta_Bot,
        "tag": Etiqueta_Bot,
        "bot_name": "Asistente SENATI",
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
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as Archivo_Temporal:
        Archivo_Audio.save(Archivo_Temporal.name)
        Segmentos, _ = Modelo_Voz.transcribe(Archivo_Temporal.name, beam_size=5)
        Texto_Transcrito = " ".join([segmento.text for segmento in Segmentos])

    os.remove(Archivo_Temporal.name)
    return jsonify({"text": Texto_Transcrito.strip()})


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


if __name__ == '__main__':
    server_port = int(os.getenv('SENATI_PORT', '5000'))
    debug_mode = os.getenv('SENATI_DEBUG', 'false').lower() == 'true'
    print(f">>> Servidor SENATI IA listo en http://localhost:{server_port} (debug={debug_mode})")
    app.run(port=server_port, debug=debug_mode)
