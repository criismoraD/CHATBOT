# Resultados de los Tests de Conversación

### Test: Test 1 - Insultos
**Usuario:** `eres una porqueria`
**Bot:** No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa.
*(Tag detectado: fuera_de_dominio)*

### Test: Test 2 - Texto sin sentido (Gibberish)
**Usuario:** `aslkfasjlkfsdf`
**Bot:** No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa.
*(Tag detectado: fuera_de_dominio)*

### Test: Test 3 - Fuera de dominio (nutricion)
**Usuario:** `el pan es bueno para la salud?`
**Bot:** No entiendo tu consulta. Puedes preguntarme nuevamente sobre calzado o ropa.
*(Tag detectado: fuera_de_dominio)*

### Test: Test 4 - Fuera de dominio con intención parecida a horario
**Usuario:** `Cuales son los horarios del gym?`
**Bot:** Atendemos de lunes a sábado de 9am a 8pm. Hacemos envíos por delivery a todo el Perú, con envío gratis en Chiclayo por compras mayores a S/300. Aceptamos tarjetas, Yape, Plin y contraentrega.
*(Tag detectado: informacion_tienda)*

### Test: Test 5 - Devoluciones y soporte
**Usuario:** `quiero devolver unos zapatos`
**Bot:** Lamentamos el inconveniente. Para devoluciones o cambios, nuestra política requiere que el producto esté sin uso, en su empaque original y presentar el comprobante de pago dentro de los primeros 7 días. Por favor comunícate a nuestro correo de soporte@senatisports.com para ayudarte.
*(Tag detectado: reclamos)*

### Test: Test 6 - Políticas de envío/delivery
**Usuario:** `como es el envio`
**Bot:** Atendemos de lunes a sábado de 9am a 8pm. Hacemos envíos por delivery a todo el Perú, con envío gratis en Chiclayo por compras mayores a S/300. Aceptamos tarjetas, Yape, Plin y contraentrega.
*(Tag detectado: informacion_tienda)*

## Test de Filtros Secuenciales (Tests 7 a 9)

### Test: Test 7 - Búsqueda base
**Usuario:** `zapatillas rojas`
**Bot:** ¡Listo! Aquí tienes 5 resultados en color rojo de la categoría Calzado. Desliza por el catálogo para verlos.
*(Tag detectado: buscar_producto)*

### Test: Test 8 - Agregar talla
**Usuario:** `talla 44`
**Bot:** ¡Genial! Encontré 5 opciones en color rojo de la categoría Calzado talla 44. Te las dejé en el catálogo, dime qué te parecen.
*(Tag detectado: buscar_producto)*

### Test: Test 9 - Agregar género
**Usuario:** `para mujer`
**Bot:** No encontré productos con esas características. Mantenemos los filtros anteriores para que puedas modificarlos. ¿Deseas buscar otra cosa?
*(Tag detectado: buscar_producto)*

## Otros tests de dominio

### Test: Test 10 - Consulta de precios general
**Usuario:** `cuanto cuestan los pantalones`
**Bot:** Puedo darte el precio exacto si me dices el producto.
*(Tag detectado: consulta_precio)*

### Test: Test 11 - Herencia de filtro de precio a colores
**Usuario:** `y en color azul?`
**Bot:** ¡Genial! Encontré 5 opciones en color azul. Te las dejé en el catálogo, dime qué te parecen.
*(Tag detectado: buscar_producto)*

### Test: Test 12 - Consulta de stock o tallas
**Usuario:** `tienen tallas grandes?`
**Bot:** Tenemos stock en: {tallas}.
*(Tag detectado: consultar_stock_item)*

### Test: Test 13 - Agradecimiento
**Usuario:** `gracias por tu ayuda bot`
**Bot:** ¡Con gusto! Avísame si necesitas otra cosa.
*(Tag detectado: agradecimiento)*

### Test: Test 14 - Despedida
**Usuario:** `bueno me paso a retirar, adios`
**Bot:** Adiós, vuelve pronto por más equipo deportivo.
*(Tag detectado: despedida)*

### Test: Test 15 - Promociones
**Usuario:** `tienen promociones por el dia de la madre`
**Bot:** Estudiantes SENATI tienen 10% adicional con correo institucional.
*(Tag detectado: promociones)*

## Prueba Extra: Conversación larga con filtros (5 mensajes)

### Test: Test Extra 1 - Saludo
**Usuario:** `hola`
**Bot:** ¡Qué gusto saludarte! Estoy aquí para informarte sobre nuestros productos.
*(Tag detectado: saludo)*

### Test: Test Extra 2 - Intención de búsqueda
**Usuario:** `estoy buscando ropa deportiva`
**Bot:** ¡Listo! Aquí tienes 5 resultados. Desliza por el catálogo para verlos.
*(Tag detectado: buscar_producto)*

### Test: Test Extra 3 - Filtro por categoría
**Usuario:** `quiero unos pantalones`
**Bot:** He filtrado el catálogo y encontré 5 artículos de la categoría Pantalones. ¿Alguno te llama la atención?
*(Tag detectado: buscar_producto)*

### Test: Test Extra 4 - Filtro acumulativo color
**Usuario:** `que sean negros`
**Bot:** ¡Listo! Aquí tienes 5 resultados en color negro de la categoría Pantalones. Desliza por el catálogo para verlos.
*(Tag detectado: buscar_producto)*

### Test: Test Extra 5 - Filtro acumulativo talla
**Usuario:** `tienes en talla M?`
**Bot:** ¡Bingo! Tengo 5 productos en color negro de la categoría Pantalones talla M listos para ti. Échales un vistazo arriba.
*(Tag detectado: buscar_producto)*
