from dialogo import Obtener_Respuesta_Principal
from memoria import Memoria_Del_Chat

def run_test(session_id, input_text, description, file_handle):
    output, tag, context = Obtener_Respuesta_Principal(session_id, input_text)
    file_handle.write(f"### Test: {description}\n")
    file_handle.write(f"**Usuario:** `{input_text}`\n")
    file_handle.write(f"**Bot:** {output}\n")
    file_handle.write(f"*(Tag detectado: {tag})*\n\n")

with open("test_conversaciones.md", "w", encoding="utf-8") as f:
    f.write("# Resultados de los Tests de Conversación\n\n")

    # Reset memory
    Memoria_Del_Chat.clear()

    run_test('session_a', 'eres una porqueria', 'Test 1 - Insultos', f)
    run_test('session_a', 'aslkfasjlkfsdf', 'Test 2 - Texto sin sentido (Gibberish)', f)
    run_test('session_a', 'el pan es bueno para la salud?', 'Test 3 - Fuera de dominio (nutricion)', f)
    run_test('session_a', 'Cuales son los horarios del gym?', 'Test 4 - Fuera de dominio con intención parecida a horario', f)
    run_test('session_a', 'quiero devolver unos zapatos', 'Test 5 - Devoluciones y soporte', f)
    run_test('session_a', 'como es el envio', 'Test 6 - Políticas de envío/delivery', f)

    Memoria_Del_Chat.clear()
    f.write("## Test de Filtros Secuenciales (Tests 7 a 9)\n\n")
    run_test('session_seq', 'zapatillas rojas', 'Test 7 - Búsqueda base', f)
    run_test('session_seq', 'talla 44', 'Test 8 - Agregar talla', f)
    run_test('session_seq', 'para mujer', 'Test 9 - Agregar género', f)

    Memoria_Del_Chat.clear()
    f.write("## Otros tests de dominio\n\n")
    run_test('session_b', 'cuanto cuestan los pantalones', 'Test 10 - Consulta de precios general', f)
    run_test('session_b', 'y en color azul?', 'Test 11 - Herencia de filtro de precio a colores', f)
    run_test('session_b', 'tienen tallas grandes?', 'Test 12 - Consulta de stock o tallas', f)
    run_test('session_b', 'gracias por tu ayuda bot', 'Test 13 - Agradecimiento', f)
    run_test('session_b', 'bueno me paso a retirar, adios', 'Test 14 - Despedida', f)
    run_test('session_b', 'tienen promociones por el dia de la madre', 'Test 15 - Promociones', f)

    Memoria_Del_Chat.clear()
    f.write("## Prueba Extra: Conversación larga con filtros (5 mensajes)\n\n")
    run_test('session_long', 'hola', 'Test Extra 1 - Saludo', f)
    run_test('session_long', 'estoy buscando ropa deportiva', 'Test Extra 2 - Intención de búsqueda', f)
    run_test('session_long', 'quiero unos pantalones', 'Test Extra 3 - Filtro por categoría', f)
    run_test('session_long', 'que sean negros', 'Test Extra 4 - Filtro acumulativo color', f)
    run_test('session_long', 'tienes en talla M?', 'Test Extra 5 - Filtro acumulativo talla', f)

print("Tests ejecutados. Resultados en test_conversaciones.md")
