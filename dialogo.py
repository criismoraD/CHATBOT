import random
import config
from ia import Predecir_Tag, Datos_De_Intents
from extractor import (
    Es_Consulta_De_Seguimiento_De_Pedido, Detectar_Id_De_Producto_En_Texto,
    Extraer_Filtros, Extraer_Palabras_Clave_De_Mensaje, Es_Solicitud_De_Reinicio_De_Filtros,
    Normalizar_Texto_Base, Inferir_Etiqueta_De_Detalle
)
from catalogo import (
    Datos_De_Productos, Buscar_Productos, Obtener_Producto_Por_Id,
    Obtener_Colores_De_Producto, Obtener_Detalle_De_Inventario,
    Categorias_Dinamicas, Colores_Dinamicos, Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto
)
from memoria import Obtener_Contexto, Actualizar_Contexto


def Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Intent):
    for intent in Datos_De_Intents['intents']:
        if intent['tag'] == Etiqueta_Intent and intent['responses']:
            return random.choice(intent['responses'])
    return None


def Generar_Respuesta_Busqueda(cantidad, texto_filtro, exito=True):
    if exito:
        plantillas = [
            f"¡Genial! Encontré {cantidad} opciones{texto_filtro}. Te las dejé en el catálogo, dime qué te parecen.",
            f"¡Bingo! Tengo {cantidad} productos{texto_filtro} listos para ti. Échales un vistazo arriba.",
            f"He filtrado el catálogo y encontré {cantidad} artículos{texto_filtro}. ¿Alguno te llama la atención?",
            f"¡Listo! Aquí tienes {cantidad} resultados{texto_filtro}. Desliza por el catálogo para verlos."
        ]
        return random.choice(plantillas)
    else:
        plantillas = [
            "Uy, lo siento mucho. No encontré nada con esas características exactas en este momento. ¿Probamos con otro color o modelo?",
            "Revisé el inventario pero no di con lo que buscas. ¿Te gustaría intentar una búsqueda un poco más general?",
            "Lamentablemente no tengo productos que coincidan al 100% con eso ahora mismo. ¡Pero sigo actualizando mi stock a diario!"
        ]
        return random.choice(plantillas)


def Debe_Heredar_Filtros_De_Contexto(
    Contexto_Actual,
    Mensaje_Usuario,
    Categoria_Filtro,
    Color_Filtro,
    Precio_Maximo_Filtro,
    Talla_Filtro,
    Genero_Filtro,
):
    Filtros_Anteriores = Contexto_Actual.get("last_filters", {}) if isinstance(Contexto_Actual, dict) else {}
    if not isinstance(Filtros_Anteriores, dict) or not Filtros_Anteriores:
        return False

    Hay_Filtros_En_Mensaje = any([
        Categoria_Filtro,
        Color_Filtro,
        Precio_Maximo_Filtro is not None,
        Talla_Filtro,
        Genero_Filtro,
    ])
    if not Hay_Filtros_En_Mensaje:
        return False

    # No verificamos strictamente que Ultimo_Tag sea de busqueda,
    # porque el usuario puede haber pedido ayuda (tag='reclamos')
    # y luego decir "y verdes?". Queremos heredar los filtros en ese caso,
    # si los filtros anteriores siguen ahí.

    Tokens_Del_Mensaje = Normalizar_Texto_Base(Mensaje_Usuario).split()
    if len(Tokens_Del_Mensaje) <= 4:
        return True

    if Tokens_Del_Mensaje and Tokens_Del_Mensaje[0] in {"y", "ademas", "tambien"}:
        return True

    if Genero_Filtro and not any([Categoria_Filtro, Color_Filtro, Precio_Maximo_Filtro is not None, Talla_Filtro]) and len(Tokens_Del_Mensaje) <= 6:
        return True

    if Color_Filtro and not any([Categoria_Filtro, Genero_Filtro, Precio_Maximo_Filtro is not None, Talla_Filtro]) and len(Tokens_Del_Mensaje) <= 6:
        return True

    return False


def Heredar_Filtros_De_Contexto(
    Contexto_Actual,
    Categoria_Filtro,
    Color_Filtro,
    Precio_Maximo_Filtro,
    Talla_Filtro,
    Genero_Filtro,
    Palabras_Clave_Detectadas,
):
    Filtros_Anteriores = Contexto_Actual.get("last_filters", {}) if isinstance(Contexto_Actual, dict) else {}
    if not isinstance(Filtros_Anteriores, dict):
        Filtros_Anteriores = {}

    # Si hay un cambio de categoría explícito, no heredamos color ni talla, a menos que sean los nuevos explicitos
    Cambio_De_Categoria = Categoria_Filtro is not None and Filtros_Anteriores.get("category") is not None and Categoria_Filtro != Filtros_Anteriores.get("category")

    Categoria_Final = Categoria_Filtro or Filtros_Anteriores.get("category")

    if Cambio_De_Categoria:
        Color_Final = Color_Filtro
        Talla_Final = Talla_Filtro
    else:
        Color_Final = Color_Filtro or Filtros_Anteriores.get("color")
        Talla_Final = Talla_Filtro or Filtros_Anteriores.get("talla")

    Precio_Maximo_Final = Precio_Maximo_Filtro if Precio_Maximo_Filtro is not None else Filtros_Anteriores.get("max_price")
    Genero_Final = Genero_Filtro or Filtros_Anteriores.get("genero")

    Keywords_Finales = Palabras_Clave_Detectadas if isinstance(Palabras_Clave_Detectadas, list) else []

    return (
        Categoria_Final,
        Color_Final,
        Precio_Maximo_Final,
        Talla_Final,
        Genero_Final,
        Keywords_Finales,
    )


def Obtener_Respuesta_Principal(Id_De_Sesion, Mensaje_Usuario):
    Etiqueta_Detectada, Confianza_Modelo, Margen_De_Confianza = Predecir_Tag(Mensaje_Usuario)
    Contexto_Actual = Obtener_Contexto(Id_De_Sesion)
    Mensaje_Normalizado = Normalizar_Texto_Base(Mensaje_Usuario)
    Es_Consulta_De_Seguimiento = Es_Consulta_De_Seguimiento_De_Pedido(Mensaje_Usuario)

    Id_De_Producto_Detectado = Detectar_Id_De_Producto_En_Texto(Mensaje_Usuario, Indice_De_Nombres_De_Producto, Frecuencia_De_Tokens_De_Producto)
    if Id_De_Producto_Detectado is not None:
        Actualizar_Contexto(Id_De_Sesion, Id_De_Producto=Id_De_Producto_Detectado)
        Contexto_Actual = Obtener_Contexto(Id_De_Sesion)

    Categoria_Filtro, Color_Filtro, Precio_Maximo_Filtro, Talla_Filtro, Genero_Filtro = Extraer_Filtros(Mensaje_Usuario, Categorias_Dinamicas, Colores_Dinamicos)
    Palabras_Clave_Detectadas = Extraer_Palabras_Clave_De_Mensaje(Mensaje_Usuario)

    if Es_Solicitud_De_Reinicio_De_Filtros(Mensaje_Usuario):
        Accion_De_Filtro = {
            "category": None,
            "color": None,
            "max_price": None,
            "talla": None,
            "genero": None,
            "keywords": [],
        }
        Respuesta_Final = "Listo, reinicie todos los filtros y ya te muestro el catalogo completo."
        Actualizar_Contexto(Id_De_Sesion, "buscar_producto", Accion_De_Filtro)
        return Respuesta_Final, "buscar_producto", Accion_De_Filtro

    if Debe_Heredar_Filtros_De_Contexto(
        Contexto_Actual,
        Mensaje_Usuario,
        Categoria_Filtro,
        Color_Filtro,
        Precio_Maximo_Filtro,
        Talla_Filtro,
        Genero_Filtro,
    ):
        (
            Categoria_Filtro,
            Color_Filtro,
            Precio_Maximo_Filtro,
            Talla_Filtro,
            Genero_Filtro,
            Palabras_Clave_Detectadas,
        ) = Heredar_Filtros_De_Contexto(
            Contexto_Actual,
            Categoria_Filtro,
            Color_Filtro,
            Precio_Maximo_Filtro,
            Talla_Filtro,
            Genero_Filtro,
            Palabras_Clave_Detectadas,
        )

    Hay_Producto_En_Contexto = bool(Id_De_Producto_Detectado or Contexto_Actual.get("selected_product_id"))
    Etiqueta_Inferida = Inferir_Etiqueta_De_Detalle(
        Mensaje_Usuario,
        Ultima_Etiqueta=Contexto_Actual.get("last_tag"),
        Hay_Producto_En_Contexto=Hay_Producto_En_Contexto,
        Producto_Mencionado_En_Mensaje=Id_De_Producto_Detectado is not None,
    )
    if Etiqueta_Inferida:
        Etiqueta_Detectada = Etiqueta_Inferida

    if (Color_Filtro or Precio_Maximo_Filtro or Genero_Filtro or Categoria_Filtro or Talla_Filtro) and Etiqueta_Detectada in {"saludo", "pedidos", "fuera_de_dominio", "agradecimiento", "informacion_tienda", "reclamos"}:
        Etiqueta_Detectada = "buscar_producto"

    if Etiqueta_Detectada == "colores" and (Precio_Maximo_Filtro or Genero_Filtro or Categoria_Filtro or not Hay_Producto_En_Contexto):
        Etiqueta_Detectada = "buscar_producto"

    if Es_Consulta_De_Seguimiento and Etiqueta_Detectada in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta_Detectada = "pedidos"

    Umbral_De_Margen_Actual = config.Umbral_De_Margen_Por_Tag.get(Etiqueta_Detectada, config.Umbral_De_Margen_Base)
    Prediccion_Ambigua = (
        Confianza_Modelo < config.Umbral_De_Confianza
        or Margen_De_Confianza < Umbral_De_Margen_Actual
    )
    if Prediccion_Ambigua and not (Categoria_Filtro or Color_Filtro or Precio_Maximo_Filtro or Talla_Filtro or Genero_Filtro):
        Etiqueta_Detectada = None
        for intent in Datos_De_Intents['intents']:
            for pattern in intent['patterns']:
                if Normalizar_Texto_Base(pattern) in Mensaje_Normalizado:
                    Etiqueta_Detectada = intent['tag']
                    break
            if Etiqueta_Detectada:
                break

        if Etiqueta_Detectada is None:
            Etiqueta_Detectada = "fuera_de_dominio"

    if Prediccion_Ambigua and (Categoria_Filtro or Color_Filtro or Precio_Maximo_Filtro or Talla_Filtro or Genero_Filtro):
        Etiqueta_Detectada = "buscar_producto"

    if Es_Consulta_De_Seguimiento and Etiqueta_Detectada in {None, "pedidos", "fuera_de_dominio"}:
        Etiqueta_Detectada = "pedidos"

    Accion_De_Filtro = None
    Productos_Encontrados = []

    # --- LÓGICA POR TAG ---
    if Etiqueta_Detectada == "buscar_producto":
        Productos_Encontrados = Buscar_Productos(
            Categoria=Categoria_Filtro,
            Color=Color_Filtro,
            Precio_Maximo=Precio_Maximo_Filtro,
            Talla=Talla_Filtro,
            Genero=Genero_Filtro,
            Palabras_Clave=Palabras_Clave_Detectadas,
        )

        if not Productos_Encontrados and not Palabras_Clave_Detectadas and not Categoria_Filtro and Color_Filtro:
            Respuesta_Final = f"Me parece genial el color {Color_Filtro.lower()}, pero ¿qué buscas exactamente? ¿Zapatillas, polos, pantalones o algo más?"
            Accion_De_Filtro = {
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
            }
        elif not Productos_Encontrados and not Palabras_Clave_Detectadas and not Categoria_Filtro and Talla_Filtro:
            Respuesta_Final = f"Talla {Talla_Filtro}, perfecto. ¿Pero de qué producto? ¿Buscas calzado o alguna prenda en particular?"
            Accion_De_Filtro = {
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
            }
        elif Productos_Encontrados:
            Texto_De_Filtro = ""
            if Color_Filtro: Texto_De_Filtro += f" en color {Color_Filtro}"
            if Categoria_Filtro: Texto_De_Filtro += f" de {Categoria_Filtro.lower()}"
            if Talla_Filtro: Texto_De_Filtro += f" talla {Talla_Filtro}"
            if Genero_Filtro: Texto_De_Filtro += f" para {Genero_Filtro.lower()}"
            Respuesta_Final = f"Encontré {len(Productos_Encontrados)} productos{Texto_De_Filtro}. Ya te los muestro en el catálogo, indícame cuál te interesa."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }
        else:
            Respuesta_Final = "Lo siento, no encontré productos con esas características exactas. Intenta ampliar tu búsqueda."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "genero": Genero_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }

    elif Etiqueta_Detectada == "filtrar_categoria":
        if Categoria_Filtro:
            Cantidad_Productos = len([p for p in Datos_De_Productos if p['category'] == Categoria_Filtro])
            Respuesta_Final = f"Listo! Te muestro los {Cantidad_Productos} productos de {Categoria_Filtro}. Revisa el catalogo arriba."
            Accion_De_Filtro = {"category": Categoria_Filtro}
        else:
            Respuesta_Final = "Claro! Que categoria te interesa? Tenemos: Calzado, Polos, Pantalones y Otros."

    elif Etiqueta_Detectada == "filtrar_genero":
        if Genero_Filtro:
            Productos_Filtrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Talla=Talla_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=len(Datos_De_Productos),
            )
            Cantidad_Productos = len(Productos_Filtrados)

            Texto_De_Condicion = f" para {Genero_Filtro.lower()}"
            if Precio_Maximo_Filtro:
                Texto_De_Condicion += f" hasta S/ {Precio_Maximo_Filtro:.2f}"
            if Categoria_Filtro:
                Texto_De_Condicion += f" en {Categoria_Filtro}"

            if Cantidad_Productos > 0:
                Texto_Cantidad = "producto" if Cantidad_Productos == 1 else "productos"
                Respuesta_Final = f"Listo! Te muestro {Cantidad_Productos} {Texto_Cantidad}{Texto_De_Condicion}."
                Accion_De_Filtro = {
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
            else:
                Respuesta_Final = f"No encontre productos{Texto_De_Condicion} con ese termino especifico. Prueba con otra descripcion."
                Accion_De_Filtro = {
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
        else:
            Respuesta_Final = "¿Para qué genero te muestro opciones? Tengo Mujer, Hombre y Unisex."
            Accion_De_Filtro = {
                "category": Categoria_Filtro,
                "color": Color_Filtro,
                "max_price": Precio_Maximo_Filtro,
                "talla": Talla_Filtro,
                "keywords": Palabras_Clave_Detectadas,
            }

    elif Etiqueta_Detectada == "consulta_precio":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Respuesta_Final = f"El {Producto_Seleccionado['name']} cuesta S/ {Producto_Seleccionado['price']:.2f}."
            else:
                Respuesta_Final = "No encuentro el precio de ese producto en específico."
        elif Categoria_Filtro or Color_Filtro or Genero_Filtro:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=3,
            )
            if Productos_Encontrados:
                Respuesta_Final = "Listo, ya te filtre esos productos en el catalogo. Indicame cual te interesa y te doy el precio exacto."
                Accion_De_Filtro = {
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "genero": Genero_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
            else:
                Respuesta_Final = "No encontre productos con esas caracteristicas. Prueba otra busqueda."
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Puedes pedirme precios por categoria o color."

    elif Etiqueta_Detectada == "pedidos":
        if Es_Consulta_De_Seguimiento:
            Respuesta_Final = (
                "Te ayudo con el seguimiento de tu pedido. En esta version aun no consulto tracking en tiempo real. "
                "Si me compartes tu numero de pedido, te indico el estado estimado y los siguientes pasos."
            )
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Para comprar, elige un producto y agrégalo al carrito."

    elif Etiqueta_Detectada == "colores":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Colores_Producto = Obtener_Colores_De_Producto(Producto_Seleccionado)
                if Colores_Producto:
                    Respuesta_Final = f"El {Producto_Seleccionado['name']} esta disponible en estos colores: {', '.join(Colores_Producto)}."
                else:
                    Respuesta_Final = f"El {Producto_Seleccionado['name']} no registra colores en la base actual."
            else:
                Respuesta_Final = "No encuentro el producto en contexto para listar sus colores."
        elif Categoria_Filtro:
            Colores_Disponibles = sorted(
                {
                    Color_Item
                    for p in Datos_De_Productos
                    if p['category'] == Categoria_Filtro
                    for Color_Item in Obtener_Colores_De_Producto(p)
                }
            )
            Respuesta_Final = f"En {Categoria_Filtro} tenemos los colores: {', '.join(Colores_Disponibles)}."
        else:
            Respuesta_Final = "Nuestros productos estan disponibles en: Negro, Blanco, Rojo, Azul, Gris y Verde."

    elif Etiqueta_Detectada == "disponibilidad":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Texto_De_Tallas, Texto_De_Genero, Texto_De_Stock, Stock_Entero = Obtener_Detalle_De_Inventario(Producto_Seleccionado)
                if Stock_Entero is None or Stock_Entero > 0:
                    Respuesta_Final = (
                        f"Si, tenemos disponible el {Producto_Seleccionado['name']}. "
                        f"Stock: {Texto_De_Stock}. Genero: {Texto_De_Genero}. Tallas: {Texto_De_Tallas}."
                    )
                else:
                    Respuesta_Final = (
                        f"En este momento el {Producto_Seleccionado['name']} no tiene stock disponible. "
                        f"Genero: {Texto_De_Genero}. Tallas registradas: {Texto_De_Tallas}."
                    )
            else:
                Respuesta_Final = "No encuentro el producto en contexto para validar disponibilidad."
        elif Categoria_Filtro or Color_Filtro or Genero_Filtro:
            Coincidencias_De_Stock = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
                Limite=3,
            )
            if Coincidencias_De_Stock:
                Respuesta_Final = f"Si, tenemos {len(Coincidencias_De_Stock)}+ productos disponibles con ese filtro. Ya te los muestro en el catalogo, indicame cual te interesa."
            else:
                Respuesta_Final = "Actualmente no tenemos stock con esas especificaciones."
        else:
            Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "Claro, dime color o categoria para revisar stock."

    elif Etiqueta_Detectada == "consultar_precio_item":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Respuesta_Final = f"¡Excelente elección! El precio del {Producto_Seleccionado['name']} es de S/ {Producto_Seleccionado['price']:.2f}."
            else:
                Respuesta_Final = "No encuentro el precio de ese producto en específico."
        else:
            Respuesta_Final = "¡Claro que sí! Solo ayúdame indicando el nombre del producto que te interesa para darte el precio exacto."

    elif Etiqueta_Detectada == "consultar_stock_item":
        Id_Producto_Contextual = Contexto_Actual.get("selected_product_id")
        if Id_Producto_Contextual:
            Producto_Seleccionado = Obtener_Producto_Por_Id(Id_Producto_Contextual)
            if Producto_Seleccionado:
                Texto_De_Tallas, Texto_De_Genero, Texto_De_Stock, _ = Obtener_Detalle_De_Inventario(Producto_Seleccionado)
                if Talla_Filtro:
                    if 'tallas' in Producto_Seleccionado and Talla_Filtro in Producto_Seleccionado['tallas']:
                        Respuesta_Final = (
                            f"¡Buenas noticias! Si tenemos el {Producto_Seleccionado['name']} en talla {Talla_Filtro}. "
                            f"Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                    elif 'tallas' in Producto_Seleccionado:
                        tallas = ", ".join(Producto_Seleccionado['tallas'])
                        Respuesta_Final = (
                            f"Lo siento, no nos queda en talla {Talla_Filtro}. "
                            f"Lo tenemos en: {tallas}. Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                    else:
                        Respuesta_Final = (
                            f"Este producto es talla unica. Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                        )
                else:
                    Respuesta_Final = (
                        f"Claro, el {Producto_Seleccionado['name']} lo tenemos en las siguientes tallas: {Texto_De_Tallas}. "
                        f"Genero: {Texto_De_Genero}. Stock: {Texto_De_Stock}."
                    )
            else:
                Respuesta_Final = "No encuentro la información de tallas de ese producto en específico."
        else:
            if Talla_Filtro:
                Productos_Encontrados = Buscar_Productos(Talla=Talla_Filtro, Limite=3)
                if Productos_Encontrados:
                    Respuesta_Final = f"Listo, ya filtre productos en talla {Talla_Filtro}. Revisa el catalogo e indicame cual te interesa."
                    Accion_De_Filtro = {"talla": Talla_Filtro}
                    Etiqueta_Detectada = "buscar_producto"
                else:
                    Respuesta_Final = f"Actualmente no me queda stock en la base de datos para la talla {Talla_Filtro}."
            else:
                Respuesta_Final = "¡Con gusto lo reviso! ¿Me podrías decir qué modelo de zapatilla o prenda estás buscando específicamente?"

    if Etiqueta_Detectada and Etiqueta_Detectada != "fuera_de_dominio" and not (Etiqueta_Detectada == "buscar_producto"):
        Respuesta_Final = Obtener_Respuesta_Aleatoria_De_Intent(Etiqueta_Detectada) or "No entiendo tu consulta. puedes repetirla?."
    elif Etiqueta_Detectada == "buscar_producto" and not (Categoria_Filtro or Color_Filtro or Genero_Filtro or Palabras_Clave_Detectadas or Talla_Filtro):
        # Cuando dicen "buscame otra cosa" sin filtros
        Respuesta_Final = "¡Claro! Dime qué buscas y te muestro las opciones."
    else:
        if Categoria_Filtro or Color_Filtro or Genero_Filtro:
            Productos_Encontrados = Buscar_Productos(
                Categoria=Categoria_Filtro,
                Color=Color_Filtro,
                Precio_Maximo=Precio_Maximo_Filtro,
                Genero=Genero_Filtro,
                Palabras_Clave=Palabras_Clave_Detectadas,
            )

            if not Productos_Encontrados and not Palabras_Clave_Detectadas and not Categoria_Filtro and Color_Filtro:
                Respuesta_Final = f"Me parece genial el color {Color_Filtro.lower()}, pero ¿qué buscas exactamente? ¿Zapatillas, polos, pantalones o algo más?"
                Accion_De_Filtro = {
                    "color": Color_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "talla": Talla_Filtro,
                    "genero": Genero_Filtro,
                    "category": None,
                    "keywords": []
                }
            elif not Productos_Encontrados and not Palabras_Clave_Detectadas and not Categoria_Filtro and Talla_Filtro:
                Respuesta_Final = f"Talla {Talla_Filtro}, perfecto. ¿Pero de qué producto? ¿Buscas calzado o alguna prenda en particular?"
                Accion_De_Filtro = {
                    "color": Color_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "talla": Talla_Filtro,
                    "genero": Genero_Filtro,
                    "category": None,
                    "keywords": []
                }
            elif not Productos_Encontrados and Palabras_Clave_Detectadas:
                Respuesta_Final = "No encontré nada exactamente con esos términos. ¿Te gustaría ver el catálogo en general?"
                Accion_De_Filtro = {
                    "color": Color_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "talla": Talla_Filtro,
                    "genero": Genero_Filtro,
                    "category": Categoria_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
            elif Productos_Encontrados:
                Texto_De_Filtro = ""
                if Color_Filtro: Texto_De_Filtro += f" en color {Color_Filtro.lower()}"
                if Categoria_Filtro: Texto_De_Filtro += f" de la categoría {Categoria_Filtro.capitalize()}"
                if Talla_Filtro: Texto_De_Filtro += f" talla {Talla_Filtro}"

                Respuesta_Final = Generar_Respuesta_Busqueda(len(Productos_Encontrados), Texto_De_Filtro, exito=True)
                Accion_De_Filtro = {
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
                Etiqueta_Detectada = "buscar_producto"
            else:
                Respuesta_Final = Generar_Respuesta_Busqueda(0, "", exito=False)
                Accion_De_Filtro = {
                    "category": Categoria_Filtro,
                    "color": Color_Filtro,
                    "talla": Talla_Filtro,
                    "genero": Genero_Filtro,
                    "max_price": Precio_Maximo_Filtro,
                    "keywords": Palabras_Clave_Detectadas,
                }
                Etiqueta_Detectada = "buscar_producto"
        elif Id_De_Producto_Detectado is not None:
            Producto_Detectado = Obtener_Producto_Por_Id(Id_De_Producto_Detectado)
            if Producto_Detectado:
                Respuesta_Final = (
                    f"Ya identifique el producto {Producto_Detectado['name']}. "
                    "¿Quieres que te diga precio, colores o stock?"
                )
                Etiqueta_Detectada = "buscar_producto"
            else:
                Respuesta_Final = "No entiendo tu consulta. Puedes preguntarme nuevamente"
        else:
            Respuesta_Final = "No entiendo tu consulta. Puedes preguntarme nuevamente"

    if Etiqueta_Detectada in ["buscar_producto", "filtrar_categoria", "filtrar_genero", "colores"]:
        Actualizar_Contexto(Id_De_Sesion, Etiqueta_Detectada, {
            "category": Categoria_Filtro,
            "color": Color_Filtro,
            "max_price": Precio_Maximo_Filtro,
            "talla": Talla_Filtro,
            "genero": Genero_Filtro,
            "keywords": Palabras_Clave_Detectadas,
        })
    else:
        # En caso de otros tags no queremos sobrescribir los filtros con dict de None (que borraria la memoria)
        Actualizar_Contexto(Id_De_Sesion, Etiqueta_Detectada, Filtros=None)

    return Respuesta_Final, Etiqueta_Detectada, Accion_De_Filtro
