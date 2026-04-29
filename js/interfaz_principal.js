let Ids_Filtrados_Por_Backend = null;
document.addEventListener('DOMContentLoaded', () => {
    // State management
    let Productos_Mostrados = [];
    let Datos_De_Productos = Normalizar_Lista_De_Productos(Array.isArray(window.PRODUCT_DATA) ? window.PRODUCT_DATA : []);
    const Origen_Actual = typeof window !== 'undefined' && window.location ? window.location.origin : '';
    const Candidatos_De_URL_API = Array.from(new Set([
        window.SENATI_API_URL,
        (Origen_Actual && /^https?:\/\//i.test(Origen_Actual)) ? Origen_Actual : null,
        'http://127.0.0.1:5000',
        'http://localhost:5000',
    ].filter(Boolean)));
    let URL_Base_API = Candidatos_De_URL_API[0] || 'http://127.0.0.1:5000';
    let Categoria_Actual = 'all';
    let Color_Actual = null;
    let Talla_Actual = null;
    let Genero_Actual = null;
    let Precio_Minimo_Actual = null;
    let Precio_Maximo_Actual = null;
    let Precio_Minimo_Base = 0;
    let Precio_Maximo_Base = 500;
    let Texto_De_Busqueda = '';
    let Cantidad_A_Mostrar = 14;
    let Carrito_Actual = JSON.parse(localStorage.getItem('senati_cart')) || [];
    let Id_De_Producto_En_Contexto_Chat = null;

    // --- Procedural Sound System ---
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    let context_audio = null;

    function Reproducir_Sonido(tipo) {
        try {
            if (!context_audio) {
                if (!AudioContextClass) return;
                context_audio = new AudioContextClass();
            }
            if (context_audio.state === 'suspended') context_audio.resume();

            const osc = context_audio.createOscillator();
            const gain = context_audio.createGain();
            osc.connect(gain);
            gain.connect(context_audio.destination);

            const now = context_audio.currentTime;

            if (tipo === 'enviar') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(400, now);
                osc.frequency.exponentialRampToValueAtTime(600, now + 0.1);
                gain.gain.setValueAtTime(0, now);
                gain.gain.linearRampToValueAtTime(0.1, now + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
                osc.start(now);
                osc.stop(now + 0.1);
            } else if (tipo === 'recibir') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(500, now);
                osc.frequency.exponentialRampToValueAtTime(800, now + 0.1);
                osc.frequency.exponentialRampToValueAtTime(1000, now + 0.2);
                gain.gain.setValueAtTime(0, now);
                gain.gain.linearRampToValueAtTime(0.1, now + 0.05);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
                osc.start(now);
                osc.stop(now + 0.2);
            }
        } catch (e) { console.warn("Audio procedural no soportado o bloqueado."); }
    }

    // Elements
    const Lista_De_Productos = document.getElementById('product-list');
    const Texto_Conteo_Productos = document.getElementById('product-count');
    const Boton_Cargar_Mas = document.getElementById('load-more-btn');
    const Entrada_Busqueda = document.getElementById('product-search');
    const Tarjetas_De_Categoria = document.querySelectorAll('.filter-btn');
    const Botones_De_Genero = document.querySelectorAll('.gender-btn');
    const Slider_Precio_Minimo = document.getElementById('price-min-slider');
    const Slider_Precio_Maximo = document.getElementById('price-max-slider');
    const Texto_Precio_Minimo = document.getElementById('price-min-value');
    const Texto_Precio_Maximo = document.getElementById('price-max-value');
    const Barra_Rango_De_Precio = document.getElementById('price-range-highlight');
    const Boton_Reiniciar_Filtros = document.getElementById('reset-all-filters');
    const Boton_Carrito = document.getElementById('cart-btn');
    const Panel_Carrito = document.getElementById('cart-sidebar');
    const Boton_Cerrar_Carrito = document.getElementById('close-cart');
    const Overlay_Carrito = document.getElementById('cart-overlay');
    const Lista_Items_Carrito = document.getElementById('cart-items-list');
    const Monto_Total_Carrito = document.getElementById('cart-total-amount');
    const Insignia_Cantidad_Carrito = document.querySelector('.cart-count');

    if (!Lista_De_Productos || !Texto_Conteo_Productos || !Boton_Cargar_Mas || !Panel_Carrito || !Overlay_Carrito || !Lista_Items_Carrito || !Monto_Total_Carrito || !Insignia_Cantidad_Carrito) {
        console.error('Faltan elementos clave del DOM para iniciar el dashboard.');
        return;
    }

    function Normalizar_Texto_Para_Categoria(Texto_Original) {
        return String(Texto_Original || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function Inferir_Categoria_Desde_Nombre_Producto(Nombre_Del_Producto) {
        const Nombre_Normalizado = Normalizar_Texto_Para_Categoria(Nombre_Del_Producto);
        if (!Nombre_Normalizado) {
            return null;
        }

        const Tokens_Del_Nombre = new Set((Nombre_Normalizado.match(/[a-z0-9]+/g) || []));
        if (!Tokens_Del_Nombre.size) {
            return null;
        }

        const Reglas_De_Categoria = [
            { Categoria: 'CALZADO', Palabras_Clave: ['zapatilla', 'zapatillas', 'zapato', 'zapatos', 'botin', 'botines', 'chimpun', 'chimpunes', 'tenis'] },
            { Categoria: 'PANTALONES', Palabras_Clave: ['pantalon', 'pantalones', 'short', 'shorts', 'legging', 'leggings', 'jogger', 'joggers', 'buzo', 'buzos', 'falda', 'faldas', 'vestido', 'vestidos'] },
            { Categoria: 'POLOS', Palabras_Clave: ['polo', 'polos', 'camiseta', 'camisetas', 'jersey', 'bividi', 'top'] },
            { Categoria: 'OTROS', Palabras_Clave: ['mochila', 'mochilas', 'maletin', 'maletines', 'gorra', 'gorras', 'media', 'medias', 'calcetin', 'calcetines', 'botella', 'botellas', 'termo', 'termos', 'accesorio', 'accesorios'] },
        ];

        for (const Regla_Actual of Reglas_De_Categoria) {
            if (Regla_Actual.Palabras_Clave.some(Palabra_Clave => Tokens_Del_Nombre.has(Palabra_Clave))) {
                return Regla_Actual.Categoria;
            }
        }

        return null;
    }

    function Normalizar_Categoria_Producto(Categoria_Original, Nombre_Del_Producto = '') {
        const Categoria_Detectada_Por_Nombre = Inferir_Categoria_Desde_Nombre_Producto(Nombre_Del_Producto);
        if (Categoria_Detectada_Por_Nombre) {
            return Categoria_Detectada_Por_Nombre;
        }

        const Categoria_En_Mayusculas = String(Categoria_Original || '').trim().toUpperCase();
        if (Categoria_En_Mayusculas === 'MEDIAS' || Categoria_En_Mayusculas === 'ACCESORIOS') {
            return 'OTROS';
        }
        return Categoria_En_Mayusculas;
    }

    function Normalizar_Lista_De_Productos(Lista_De_Productos) {
        if (!Array.isArray(Lista_De_Productos)) {
            return [];
        }

        return Lista_De_Productos
            .filter(Producto => Producto && typeof Producto === 'object')
            .map(Producto => ({
                ...Producto,
                category: Normalizar_Categoria_Producto(Producto.category, Producto.name),
            }));
    }

    // Initialization
    async function Cargar_Productos_Desde_Json() {
        const Rutas_De_Carga = [`${URL_Base_API}/products?source=scraped`];

        for (const Ruta of Rutas_De_Carga) {
            try {
                const Respuesta = await fetch(Ruta);
                if (!Respuesta.ok) {
                    continue;
                }

                const Datos = await Respuesta.json();
                if (Array.isArray(Datos)) {
                    return Normalizar_Lista_De_Productos(Datos);
                }

                if (Array.isArray(Datos.products)) {
                    return Normalizar_Lista_De_Productos(Datos.products);
                }
            } catch (Error_De_Carga) {
                console.error(`[FRONTEND] Error fetch en ${Ruta}:`, Error_De_Carga.message);
            }
        }

        return [];
    }

    async function Resolver_URL_Base_API() {
        for (const URL_Candidata of Candidatos_De_URL_API) {
            try {
                const Respuesta_Estado = await fetch(`${URL_Candidata}/status`, { method: 'GET' });
                if (Respuesta_Estado.ok) {
                    URL_Base_API = URL_Candidata;
                    return;
                }
            } catch (Error_De_Conexion) {
                console.warn(`[FRONTEND] API no disponible en ${URL_Candidata}:`, Error_De_Conexion.message);
            }
        }
    }

    function Restablecer_Filtros_Visuales_Y_Estado() {
        Ids_Filtrados_Por_Backend = null;
        Categoria_Actual = 'all';
        Color_Actual = null;
        Talla_Actual = null;
        Genero_Actual = null;
        Texto_De_Busqueda = '';
        Id_De_Producto_En_Contexto_Chat = null;
        Precio_Minimo_Actual = Precio_Minimo_Base;
        Precio_Maximo_Actual = Precio_Maximo_Base;
        Cantidad_A_Mostrar = 14;

        if (Entrada_Busqueda) Entrada_Busqueda.value = '';
        if (Slider_Precio_Minimo) Slider_Precio_Minimo.value = String(Precio_Minimo_Base);
        if (Slider_Precio_Maximo) Slider_Precio_Maximo.value = String(Precio_Maximo_Base);

        Tarjetas_De_Categoria.forEach(Boton => {
            Boton.classList.toggle('active', Boton.dataset.category === 'all');
        });

        const Circulos_De_Color = document.querySelectorAll('.color-circle');
        Circulos_De_Color.forEach(Circulo => {
            Circulo.classList.toggle('active', Circulo.dataset.color === 'all');
        });

        Actualizar_Botones_De_Genero();
        Actualizar_Textos_Rango_De_Precio();
    }

    async function Recargar_Catalogo_Activo() {
        const Productos_Cargados = await Cargar_Productos_Desde_Json();
        if (Productos_Cargados.length) {
            Datos_De_Productos = Productos_Cargados;
        } else {
            Datos_De_Productos = Array.isArray(window.PRODUCT_DATA) ? window.PRODUCT_DATA : Productos_Cargados;
        }
        Configurar_Rango_De_Precio_Inicial();
        Actualizar_Botones_De_Genero();
        Restablecer_Filtros_Visuales_Y_Estado();
        Renderizar_Productos();
    }

    async function Inicializar_Dashboard() {
        await Resolver_URL_Base_API();
        const Productos_Cargados = await Cargar_Productos_Desde_Json();
        if (Productos_Cargados.length || !Datos_De_Productos.length) {
            Datos_De_Productos = Productos_Cargados;
        }

        Configurar_Rango_De_Precio_Inicial();
        Actualizar_Botones_De_Genero();

        Renderizar_Productos();
        Actualizar_UI_Carrito();
        Configurar_Eventos();
    }

    function Configurar_Rango_De_Precio_Inicial() {
        const Lista_De_Precios = Datos_De_Productos
            .map(Producto => Number(Producto.price))
            .filter(Precio => Number.isFinite(Precio));

        if (Lista_De_Precios.length) {
            Precio_Minimo_Base = Math.floor(Math.min(...Lista_De_Precios));
            Precio_Maximo_Base = Math.ceil(Math.max(...Lista_De_Precios));
        }

        Precio_Minimo_Actual = Precio_Minimo_Base;
        Precio_Maximo_Actual = Precio_Maximo_Base;

        if (Slider_Precio_Minimo) {
            Slider_Precio_Minimo.min = String(Precio_Minimo_Base);
            Slider_Precio_Minimo.max = String(Precio_Maximo_Base);
            Slider_Precio_Minimo.value = String(Precio_Minimo_Base);
        }

        if (Slider_Precio_Maximo) {
            Slider_Precio_Maximo.min = String(Precio_Minimo_Base);
            Slider_Precio_Maximo.max = String(Precio_Maximo_Base);
            Slider_Precio_Maximo.value = String(Precio_Maximo_Base);
        }

        Actualizar_Textos_Rango_De_Precio();
    }

    function Actualizar_Textos_Rango_De_Precio() {
        if (Texto_Precio_Minimo) {
            Texto_Precio_Minimo.textContent = `S/ ${Math.round(Precio_Minimo_Actual ?? Precio_Minimo_Base)}`;
        }
        if (Texto_Precio_Maximo) {
            Texto_Precio_Maximo.textContent = `S/ ${Math.round(Precio_Maximo_Actual ?? Precio_Maximo_Base)}`;
        }

        if (Barra_Rango_De_Precio) {
            const Rango_Total = Math.max(1, Precio_Maximo_Base - Precio_Minimo_Base);
            const Inicio = ((Precio_Minimo_Actual - Precio_Minimo_Base) / Rango_Total) * 100;
            const Fin = ((Precio_Maximo_Actual - Precio_Minimo_Base) / Rango_Total) * 100;
            Barra_Rango_De_Precio.style.left = `${Inicio}%`;
            Barra_Rango_De_Precio.style.width = `${Math.max(0, Fin - Inicio)}%`;
        }
    }

    function Actualizar_Botones_De_Genero() {
        if (!Botones_De_Genero || !Botones_De_Genero.length) return;

        Botones_De_Genero.forEach(Boton => {
            Boton.classList.remove('active');
            if ((!Genero_Actual && Boton.dataset.gender === 'all') || Genero_Actual === Boton.dataset.gender) {
                Boton.classList.add('active');
            }
        });
    }

    function Normalizar_Texto_Para_Busqueda(Texto_Original) {
        return String(Texto_Original || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function Expandir_Variantes_De_Token(Token_Original) {
        const Variantes = new Set([Token_Original]);

        if (Token_Original.length > 4 && Token_Original.endsWith('es')) {
            Variantes.add(Token_Original.slice(0, -2));
        }
        if (Token_Original.length > 3 && Token_Original.endsWith('s')) {
            Variantes.add(Token_Original.slice(0, -1));
        }

        if (Token_Original.length > 3 && Token_Original.endsWith('as')) {
            Variantes.add(`${Token_Original.slice(0, -2)}a`);
            Variantes.add(`${Token_Original.slice(0, -2)}o`);
        } else if (Token_Original.length > 3 && Token_Original.endsWith('a')) {
            Variantes.add(`${Token_Original.slice(0, -1)}o`);
        }

        if (Token_Original.length > 3 && Token_Original.endsWith('os')) {
            Variantes.add(`${Token_Original.slice(0, -2)}o`);
            Variantes.add(`${Token_Original.slice(0, -2)}a`);
        } else if (Token_Original.length > 3 && Token_Original.endsWith('o')) {
            Variantes.add(`${Token_Original.slice(0, -1)}a`);
        }

        const Sinonimos_Por_Token = {
            zapatilla: ['calzado', 'zapato', 'tenis'],
            zapatillas: ['calzado', 'zapato', 'tenis'],
            zapato: ['calzado', 'zapatilla', 'tenis'],
            zapatos: ['calzado', 'zapatilla', 'tenis'],
            tenis: ['calzado', 'zapatilla'],
            calzado: ['zapatilla', 'zapato', 'tenis'],
            pantalon: ['leggin', 'legging', 'jogger', 'buzo'],
            pantalones: ['leggins', 'leggings', 'joggers', 'buzos'],
        };

        const Lista_De_Sinonimos = Sinonimos_Por_Token[Token_Original] || [];
        Lista_De_Sinonimos.forEach(Sinonimo => Variantes.add(Sinonimo));

        return Array.from(Variantes);
    }

    function Coincide_Texto_De_Busqueda(Producto, Colores_Disponibles, Texto_De_Busqueda_Actual) {
        const Texto_Busqueda_Normalizado = Normalizar_Texto_Para_Busqueda(Texto_De_Busqueda_Actual);
        if (!Texto_Busqueda_Normalizado) {
            return true;
        }

        const Tokens_De_Busqueda = Texto_Busqueda_Normalizado.split(/\s+/).filter(t => t.length > 2);
        if (Tokens_De_Busqueda.length === 0) return true;

        const Texto_Indexable_Del_Producto = Normalizar_Texto_Para_Busqueda([
            Producto.name,
            Producto.description,
            Producto.genero,
            Colores_Disponibles.join(' '),
        ].join(' '));

        return Tokens_De_Busqueda.every(Token => {
            const Variantes_Del_Token = Expandir_Variantes_De_Token(Token);
            // Si alguna variante coincide exactamente o como palabra completa, o si el token largo está incluido
            return Variantes_Del_Token.some(Variante => {
                if (Texto_Indexable_Del_Producto.includes(Variante)) return true;
                return false;
            });
        });
    }

    // ============================================================
    // PRODUCT RENDERING (Con soporte para filtro por color)
    // ============================================================
    function Renderizar_Productos() {
        Lista_De_Productos.classList.toggle('source-scraped', true);

        const Productos_Filtrados = Datos_De_Productos.filter(Producto => {
            const Colores_Disponibles = Obtener_Colores_Producto(Producto);
            const Colores_Filtrables = Obtener_Colores_Filtrables(Producto, Colores_Disponibles);

            if (Ids_Filtrados_Por_Backend !== null && !Ids_Filtrados_Por_Backend.has(Producto.id)) {
                return false;
            }
            const Coincide_Categoria = Categoria_Actual === 'all' || Producto.category === Categoria_Actual;
            const Coincide_Color = !Color_Actual || Colores_Filtrables.includes(Color_Actual);
            const Coincide_Talla = !Talla_Actual || (Producto.tallas && Producto.tallas.includes(Talla_Actual));
            const Coincide_Genero = !Genero_Actual || Producto.genero === Genero_Actual;
            const Coincide_Precio_Minimo = Precio_Minimo_Actual === null || Producto.price >= Precio_Minimo_Actual;
            const Coincide_Precio_Maximo = Precio_Maximo_Actual === null || Producto.price <= Precio_Maximo_Actual;
            const Coincide_Busqueda = Coincide_Texto_De_Busqueda(Producto, Colores_Filtrables, Texto_De_Busqueda);

            return Coincide_Categoria
                && Coincide_Color
                && Coincide_Talla
                && Coincide_Genero
                && Coincide_Precio_Minimo
                && Coincide_Precio_Maximo
                && Coincide_Busqueda;
        });

        Productos_Mostrados = Productos_Filtrados.slice(0, Cantidad_A_Mostrar);
        Lista_De_Productos.innerHTML = '';

        if (!Datos_De_Productos.length) {
            Lista_De_Productos.innerHTML = '<p class="empty-msg">No hay catalogo scrapeado todavia. Ejecuta scrape_products.py para generarlo.</p>';
        } else if (Productos_Mostrados.length === 0) {
            Lista_De_Productos.innerHTML = '<p class="empty-msg">No se encontraron productos con ese filtro.</p>';
        } else {
            Productos_Mostrados.forEach(product => {
                const card = Crear_Tarjeta_Producto(product);
                Lista_De_Productos.appendChild(card);
            });
        }

        // Update count
        let filterText = '';
        if (Color_Actual) filterText += ` | Color: ${Color_Actual}`;
        if (Talla_Actual) filterText += ` | Talla: ${Talla_Actual}`;
        if (Genero_Actual) filterText += ` | Genero: ${Genero_Actual}`;
        if (Texto_De_Busqueda) filterText += ` | Busqueda: ${Texto_De_Busqueda}`;
        if (Precio_Minimo_Actual !== null && Precio_Maximo_Actual !== null) {
            filterText += ` | Precio: S/ ${Precio_Minimo_Actual.toFixed(0)} - S/ ${Precio_Maximo_Actual.toFixed(0)}`;
        }
        Texto_Conteo_Productos.innerText = `Mostrando ${Productos_Mostrados.length} de ${Productos_Filtrados.length} productos${filterText}`;

        // Hide/Show load more
        Boton_Cargar_Mas.style.display = Cantidad_A_Mostrar >= Productos_Filtrados.length ? 'none' : 'inline-block';
    }

    function Obtener_Emoji_Categoria(category) {
        const emojis = {
            'CALZADO': '👟',
            'POLOS': '👕',
            'PANTALONES': '👖',
            'OTROS': '🎒'
        };
        return emojis[category] || '✨';
    }

    function Crear_Tarjeta_Producto(product) {
        const div = document.createElement('div');
        div.className = 'dashboard-card';

        const Tallas_Como_Texto = product.tallas ? product.tallas.join(', ') : 'Sin talla';
        const Colores_Disponibles = Obtener_Colores_Producto(product);
        const Colores_Como_Texto = Colores_Disponibles.length ? Colores_Disponibles.join(', ') : 'No definido';
        const Genero_Producto = product.genero || 'Unisex';
        const Stock_Producto = Number.isFinite(product.stock) ? product.stock : null;
        const catEmoji = Obtener_Emoji_Categoria(product.category);
        const Url_Imagen_Producto = Obtener_Imagen_Producto(product);

        const cardTop = document.createElement('div');
        cardTop.className = 'card-top';

        const cardMedia = document.createElement('div');
        cardMedia.className = 'card-media';
        if (Url_Imagen_Producto) {
            const img = document.createElement('img');
            img.className = 'card-image';
            img.src = Url_Imagen_Producto;
            img.alt = product.name;
            img.loading = 'lazy';
            img.referrerPolicy = 'no-referrer';
            cardMedia.appendChild(img);
        } else {
            const span = document.createElement('span');
            span.className = 'card-emoji';
            span.textContent = catEmoji;
            cardMedia.appendChild(span);
        }

        const cardColorDots = document.createElement('div');
        cardColorDots.className = 'card-color-dots';
        Colores_Disponibles.forEach(Color_Item => {
            const dot = document.createElement('div');
            dot.className = 'card-color-dot';
            dot.style.backgroundColor = Obtener_Color_Hex(Color_Item);
            dot.title = Color_Item;
            cardColorDots.appendChild(dot);
        });

        cardTop.appendChild(cardMedia);
        cardTop.appendChild(cardColorDots);

        const cardCat = document.createElement('span');
        cardCat.className = 'card-cat';
        cardCat.textContent = product.category;

        const cardTitle = document.createElement('h3');
        cardTitle.textContent = product.name;

        const cardMeta = document.createElement('div');
        cardMeta.className = 'card-meta';
        const spanColores = document.createElement('span');
        spanColores.textContent = `Colores: ${Colores_Como_Texto}`;
        const spanGenero = document.createElement('span');
        spanGenero.textContent = `Genero: ${Genero_Producto}`;
        cardMeta.appendChild(spanColores);
        cardMeta.appendChild(document.createElement('br'));
        cardMeta.appendChild(spanGenero);

        const cardTallasVisor = document.createElement('div');
        cardTallasVisor.className = 'card-tallas-visor';
        const tallasEtiqueta = document.createElement('span');
        tallasEtiqueta.className = 'tallas-etiqueta';
        tallasEtiqueta.textContent = 'Tallas disponibles';
        const tallasValores = document.createElement('span');
        tallasValores.className = 'tallas-valores';
        tallasValores.textContent = Tallas_Como_Texto;
        cardTallasVisor.appendChild(tallasEtiqueta);
        cardTallasVisor.appendChild(tallasValores);

        const cardStock = document.createElement('div');
        cardStock.className = 'card-stock';
        cardStock.textContent = `Stock: ${Stock_Producto !== null ? `${Stock_Producto} unidades` : 'No disponible'}`;

        const cardPriceRow = document.createElement('div');
        cardPriceRow.className = 'card-price-row';
        const cardPrice = document.createElement('span');
        cardPrice.className = 'card-price';
        cardPrice.textContent = `S/ ${product.price.toFixed(2)}`;

        const cardActions = document.createElement('div');
        cardActions.className = 'card-actions';

        const btnConsult = document.createElement('button');
        btnConsult.className = 'card-btn consult-bot-quick';
        btnConsult.title = 'Preguntar';
        btnConsult.dataset.id = product.id;
        btnConsult.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a3 3 0 0 1 3 3v2h2a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-2v1a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3v-1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2V10a3 3 0 0 1 3-3h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zM9 13a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"></path></svg>';

        const btnAdd = document.createElement('button');
        btnAdd.className = 'card-btn add-to-cart-quick';
        btnAdd.title = 'Agregar al carrito';
        btnAdd.dataset.id = product.id;
        btnAdd.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>';

        cardActions.appendChild(btnConsult);
        cardActions.appendChild(btnAdd);

        cardPriceRow.appendChild(cardPrice);
        cardPriceRow.appendChild(cardActions);

        div.appendChild(cardTop);
        div.appendChild(cardCat);
        div.appendChild(cardTitle);
        div.appendChild(cardMeta);
        div.appendChild(cardTallasVisor);
        div.appendChild(cardStock);
        div.appendChild(cardPriceRow);

        btnAdd.addEventListener('click', () => Agregar_Al_Carrito(product));
        btnConsult.addEventListener('click', () => Consultar_Producto(product));

        return div;
    }

    function Obtener_Color_Hex(colorName) {
        const map = {
            'Negro': '#1a1a1a', 'Blanco': '#f0f0f0', 'Rojo': '#e74c3c',
            'Azul': '#3498db', 'Gris': '#95a5a6', 'Verde': '#27ae60'
        };
        return map[colorName] || '#666';
    }

    function Obtener_Imagen_Producto(Producto) {
        const Url_Imagen = typeof Producto.image === 'string' && Producto.image.trim()
            ? Producto.image.trim()
            : (typeof Producto.imagen === 'string' && Producto.imagen.trim()
                ? Producto.imagen.trim()
                : null);

        return Url_Imagen ? Url_Imagen.replace(/\\/g, '/') : null;
    }

    function Obtener_Colores_Producto(Producto) {
        if (Array.isArray(Producto.colores) && Producto.colores.length) {
            return Producto.colores;
        }
        return Producto.color ? [Producto.color] : [];
    }

    function Obtener_Colores_Filtrables(Producto, Colores_Disponibles = null) {
        const Set_De_Colores = new Set();
        
        const Color_Principal = typeof Producto.color === 'string' ? Producto.color.trim() : '';
        if (Color_Principal) {
            Set_De_Colores.add(Color_Principal);
        }

        const Lista_De_Colores = Array.isArray(Colores_Disponibles) ? Colores_Disponibles : Obtener_Colores_Producto(Producto);
        Lista_De_Colores.forEach(Color_Item => {
            if (typeof Color_Item === 'string' && Color_Item.trim()) {
                Set_De_Colores.add(Color_Item.trim());
            }
        });

        return Array.from(Set_De_Colores);
    }

    function Consultar_Producto(product) {
        // Enviar un mensaje visual distinto al chat
        const infoMsg = `[Consulta iniciada para: ${product.name}]`;
        Agregar_Mensaje_Chat(infoMsg, 'user');
        Id_De_Producto_En_Contexto_Chat = product.id;
        
        // Enviar al backend indicándole el contexto del producto ocultamente
        Obtener_Respuesta_Chat('quiero saber mas de este producto', product.id);
    }

    // ============================================================
    // FILTRADO DESDE EL CHAT (filter_action)
    // ============================================================
    function Aplicar_Filtro_Desde_Chat(Accion_De_Filtro) {
        if (Accion_De_Filtro.product_ids) {
            Ids_Filtrados_Por_Backend = new Set(Accion_De_Filtro.product_ids);
        } else {
            Ids_Filtrados_Por_Backend = null;
        }

        if (Accion_De_Filtro.category) {
            Categoria_Actual = Accion_De_Filtro.category;
            Tarjetas_De_Categoria.forEach(c => {
                c.classList.remove('active');
                if (c.dataset.category === Accion_De_Filtro.category) {
                    c.classList.add('active');
                }
            });
        } else {
            Categoria_Actual = 'all';
            Tarjetas_De_Categoria.forEach(c => {
                c.classList.toggle('active', c.dataset.category === 'all');
            });
        }
        if (Accion_De_Filtro.color) {
            Color_Actual = Accion_De_Filtro.color;
        } else {
            Color_Actual = null;
        }
        
        if (Accion_De_Filtro.talla) {
            Talla_Actual = Accion_De_Filtro.talla;
        } else {
            Talla_Actual = null;
        }

        if (Accion_De_Filtro.genero) {
            Genero_Actual = Accion_De_Filtro.genero;
        } else {
            Genero_Actual = null;
        }
        Actualizar_Botones_De_Genero();

        // Evita sobre-filtrar cuando ya tenemos filtros estructurados (categoria/color/talla/genero/precio).
        const Tiene_Filtros_Estructurados = Boolean(
            Accion_De_Filtro.category
            || Accion_De_Filtro.color
            || Accion_De_Filtro.talla
            || Accion_De_Filtro.genero
            || typeof Accion_De_Filtro.max_price === 'number'
        );
        const Tiene_Ids_De_Backend = Array.isArray(Accion_De_Filtro.product_ids)
            && Accion_De_Filtro.product_ids.length > 0;

        const Lista_De_Keywords_Especificas = new Set([
            'mochila', 'mochilas', 'gorra', 'gorras', 'tomatodo', 'tomatodos',
            'falda', 'faldas', 'vestido', 'vestidos', 'legging', 'leggings',
            'jogger', 'joggers', 'short', 'shorts', 'casaca', 'casacas',
            'pantalon', 'pantalones', 'polo', 'polos', 'zapatilla', 'zapatillas',
            'conjunto', 'conjuntos'
        ]);

        const Debe_Aplicar_Keywords_Con_Filtros = Array.isArray(Accion_De_Filtro.keywords)
            && Accion_De_Filtro.keywords.some(Keyword_Actual => {
                const Keyword_Normalizada = Normalizar_Texto_Para_Busqueda(Keyword_Actual);
                return Lista_De_Keywords_Especificas.has(Keyword_Normalizada);
            });

        if (!Tiene_Ids_De_Backend
            && Array.isArray(Accion_De_Filtro.keywords)
            && Accion_De_Filtro.keywords.length
            && (!Tiene_Filtros_Estructurados || Debe_Aplicar_Keywords_Con_Filtros)) {
            Texto_De_Busqueda = Accion_De_Filtro.keywords.join(' ').trim();
        } else {
            Texto_De_Busqueda = '';
        }

        if (Entrada_Busqueda) {
            Entrada_Busqueda.value = '';
        }

        if (typeof Accion_De_Filtro.max_price === 'number') {
            Precio_Maximo_Actual = Math.min(Precio_Maximo_Base, Math.max(Precio_Minimo_Base, Accion_De_Filtro.max_price));
            if (Precio_Minimo_Actual === null) {
                Precio_Minimo_Actual = Precio_Minimo_Base;
            }
            if (Precio_Maximo_Actual < Precio_Minimo_Actual) {
                Precio_Minimo_Actual = Precio_Maximo_Actual;
            }
            if (Slider_Precio_Minimo) {
                Slider_Precio_Minimo.value = String(Math.round(Precio_Minimo_Actual));
            }
            if (Slider_Precio_Maximo) {
                Slider_Precio_Maximo.value = String(Math.round(Precio_Maximo_Actual));
            }
        } else {
            Precio_Minimo_Actual = Precio_Minimo_Base;
            Precio_Maximo_Actual = Precio_Maximo_Base;
            if (Slider_Precio_Minimo) {
                Slider_Precio_Minimo.value = String(Precio_Minimo_Base);
            }
            if (Slider_Precio_Maximo) {
                Slider_Precio_Maximo.value = String(Precio_Maximo_Base);
            }
        }
        Actualizar_Textos_Rango_De_Precio();
        
        // Actualizar UI colores
        const colorCircles = document.querySelectorAll('.color-circle');
        colorCircles.forEach(c => {
            c.classList.remove('active');
            if (Color_Actual === c.dataset.color || (Color_Actual === null && c.dataset.color === 'all')) {
                c.classList.add('active');
            }
        });

        Cantidad_A_Mostrar = 14;
        Renderizar_Productos();
        
        // Scroll suave al catálogo
        const catalogSection = document.getElementById('catalogo');
        if (catalogSection) {
            catalogSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // ============================================================
    // CART LOGIC
    // ============================================================
    function Agregar_Al_Carrito(product) {
        const existing = Carrito_Actual.find(item => item.id === product.id);
        if (existing) {
            existing.quantity += 1;
        } else {
            Carrito_Actual.push({ ...product, quantity: 1 });
        }
        Guardar_Carrito();
        Actualizar_UI_Carrito();
        Abrir_Panel_Carrito();
    }

    function Quitar_Del_Carrito(id) {
        Carrito_Actual = Carrito_Actual.filter(item => item.id !== id);
        Guardar_Carrito();
        Actualizar_UI_Carrito();
    }

    function Aumentar_Cantidad(id) {
        const item = Carrito_Actual.find(item => item.id === id);
        if (item) {
            item.quantity += 1;
            Guardar_Carrito();
            Actualizar_UI_Carrito();
        }
    }

    function Disminuir_Cantidad(id) {
        const item = Carrito_Actual.find(item => item.id === id);
        if (item) {
            item.quantity -= 1;
            if (item.quantity <= 0) {
                Quitar_Del_Carrito(id);
            } else {
                Guardar_Carrito();
                Actualizar_UI_Carrito();
            }
        }
    }

    function Guardar_Carrito() {
        localStorage.setItem('senati_cart', JSON.stringify(Carrito_Actual));
    }

    function Actualizar_UI_Carrito() {
        const totalItems = Carrito_Actual.reduce((acc, current) => acc + current.quantity, 0);
        Insignia_Cantidad_Carrito.innerText = totalItems;

        Lista_Items_Carrito.innerHTML = '';
        if (Carrito_Actual.length === 0) {
            Lista_Items_Carrito.innerHTML = '<p class="empty-msg">Tu carrito está vacío.</p>';
            Monto_Total_Carrito.innerText = 'S/ 0.00';
        } else {
            let total = 0;
            Carrito_Actual.forEach(item => {
                total += item.price * item.quantity;
                const itemDiv = document.createElement('div');
                itemDiv.className = 'cart-item-row';

                const itemEmoji = document.createElement('div');
                itemEmoji.className = 'cart-item-emoji';
                const imgUrl = Obtener_Imagen_Producto(item);
                if (imgUrl) {
                    const imgEl = document.createElement('img');
                    imgEl.src = imgUrl;
                    imgEl.alt = item.name;
                    imgEl.style.cssText = 'width:52px;height:52px;object-fit:cover;border-radius:8px;display:block;';
                    imgEl.referrerPolicy = 'no-referrer';
                    imgEl.onerror = () => { imgEl.style.display='none'; itemEmoji.textContent = Obtener_Emoji_Categoria(item.category); };
                    itemEmoji.appendChild(imgEl);
                } else {
                    itemEmoji.textContent = Obtener_Emoji_Categoria(item.category);
                }

                const itemInfo = document.createElement('div');
                itemInfo.className = 'cart-item-info';

                const itemName = document.createElement('h4');
                itemName.textContent = item.name;

                const qtyControls = document.createElement('div');
                qtyControls.className = 'cart-item-qty-controls';
                qtyControls.style.cssText = 'display: flex; align-items: center; gap: 8px; margin: 4px 0;';

                const btnDecrease = document.createElement('button');
                btnDecrease.className = 'qty-btn decrease-qty';
                btnDecrease.dataset.id = item.id;
                btnDecrease.style.cssText = 'width: 24px; height: 24px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center;';
                btnDecrease.textContent = '-';

                const qtySpan = document.createElement('span');
                qtySpan.style.cssText = 'font-size: 0.9rem; font-weight: 600; min-width: 20px; text-align: center;';
                qtySpan.textContent = item.quantity;

                const btnIncrease = document.createElement('button');
                btnIncrease.className = 'qty-btn increase-qty';
                btnIncrease.dataset.id = item.id;
                btnIncrease.style.cssText = 'width: 24px; height: 24px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center;';
                btnIncrease.textContent = '+';

                qtyControls.appendChild(btnDecrease);
                qtyControls.appendChild(qtySpan);
                qtyControls.appendChild(btnIncrease);

                const pricePara = document.createElement('p');
                pricePara.style.cssText = 'margin: 0; font-weight: bold; color: var(--primary-color);';
                pricePara.textContent = `S/ ${(item.price * item.quantity).toFixed(2)} `;
                const unitPriceSpan = document.createElement('span');
                unitPriceSpan.style.cssText = 'font-size: 0.8em; color: #777; font-weight: normal;';
                unitPriceSpan.textContent = `(S/ ${item.price.toFixed(2)} c/u)`;
                pricePara.appendChild(unitPriceSpan);

                itemInfo.appendChild(itemName);
                itemInfo.appendChild(qtyControls);
                itemInfo.appendChild(pricePara);

                const btnRemove = document.createElement('button');
                btnRemove.className = 'remove-item';
                btnRemove.dataset.id = item.id;
                const iconTrash = document.createElement('i');
                iconTrash.className = 'fa-solid fa-trash-can';
                btnRemove.appendChild(iconTrash);

                itemDiv.appendChild(itemEmoji);
                itemDiv.appendChild(itemInfo);
                itemDiv.appendChild(btnRemove);

                Lista_Items_Carrito.appendChild(itemDiv);

                btnRemove.addEventListener('click', () => Quitar_Del_Carrito(item.id));
                btnIncrease.addEventListener('click', () => Aumentar_Cantidad(item.id));
                btnDecrease.addEventListener('click', () => Disminuir_Cantidad(item.id));
            });
            Monto_Total_Carrito.innerText = `S/ ${total.toFixed(2)}`;
        }
    }

    // ============================================================
    // EVENT LISTENERS
    // ============================================================
    function Configurar_Eventos() {
        const Aplicar_Rango_De_Precio = (Tipo_De_Control) => {
            if (!Slider_Precio_Minimo || !Slider_Precio_Maximo) return;

            let Precio_Minimo_Leido = Number.parseFloat(Slider_Precio_Minimo.value);
            let Precio_Maximo_Leido = Number.parseFloat(Slider_Precio_Maximo.value);

            if (Precio_Minimo_Leido > Precio_Maximo_Leido) {
                if (Tipo_De_Control === 'min') {
                    Precio_Maximo_Leido = Precio_Minimo_Leido;
                    Slider_Precio_Maximo.value = String(Precio_Maximo_Leido);
                } else {
                    Precio_Minimo_Leido = Precio_Maximo_Leido;
                    Slider_Precio_Minimo.value = String(Precio_Minimo_Leido);
                }
            }

            Precio_Minimo_Actual = Precio_Minimo_Leido;
            Precio_Maximo_Actual = Precio_Maximo_Leido;
            Actualizar_Textos_Rango_De_Precio();
            Cantidad_A_Mostrar = 14;
            Renderizar_Productos();
        };

        if (Entrada_Busqueda) {
            Entrada_Busqueda.addEventListener('input', (e) => {
                Texto_De_Busqueda = e.target.value;
                Color_Actual = null;
                Talla_Actual = null;
                Genero_Actual = null;
                Actualizar_Botones_De_Genero();
                Precio_Minimo_Actual = Precio_Minimo_Base;
                Precio_Maximo_Actual = Precio_Maximo_Base;
                if (Slider_Precio_Minimo) Slider_Precio_Minimo.value = String(Precio_Minimo_Base);
                if (Slider_Precio_Maximo) Slider_Precio_Maximo.value = String(Precio_Maximo_Base);
                Actualizar_Textos_Rango_De_Precio();
                Cantidad_A_Mostrar = 14;
                Renderizar_Productos();
            });
        }

        if (Slider_Precio_Minimo) {
            Slider_Precio_Minimo.addEventListener('input', () => {
                Aplicar_Rango_De_Precio('min');
            });
        }

        if (Slider_Precio_Maximo) {
            Slider_Precio_Maximo.addEventListener('input', () => {
                Aplicar_Rango_De_Precio('max');
            });
        }



        if (Boton_Reiniciar_Filtros) {
            Boton_Reiniciar_Filtros.addEventListener('click', () => {
                Restablecer_Filtros_Visuales_Y_Estado();
                Renderizar_Productos();
            });
        }

        Tarjetas_De_Categoria.forEach(card => {
            card.addEventListener('click', () => {
                Tarjetas_De_Categoria.forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                Categoria_Actual = card.dataset.category;
                Ids_Filtrados_Por_Backend = null;
                Cantidad_A_Mostrar = 14;
                Renderizar_Productos();
            });
        });

        if (Botones_De_Genero && Botones_De_Genero.length) {
            Botones_De_Genero.forEach(Boton => {
                Boton.addEventListener('click', () => {
                    Genero_Actual = Boton.dataset.gender === 'all' ? null : Boton.dataset.gender;
                    Ids_Filtrados_Por_Backend = null;
                    Actualizar_Botones_De_Genero();
                    Cantidad_A_Mostrar = 14;
                    Renderizar_Productos();
                });
            });
        }

        // Color circles listener
        const colorCircles = document.querySelectorAll('.color-circle');
        colorCircles.forEach(circle => {
            circle.addEventListener('click', () => {
                colorCircles.forEach(c => c.classList.remove('active'));
                circle.classList.add('active');
                
                if(circle.dataset.color === 'all') {
                    Color_Actual = null;
                    Ids_Filtrados_Por_Backend = null;
                } else {
                    Color_Actual = circle.dataset.color;
                }
                Ids_Filtrados_Por_Backend = null;
                Cantidad_A_Mostrar = 14;
                Renderizar_Productos();
            });
        });

        if (Boton_Cargar_Mas) {
            Boton_Cargar_Mas.addEventListener('click', () => {
                Cantidad_A_Mostrar += 14;
                Renderizar_Productos();
            });
        }

        if (Boton_Carrito) Boton_Carrito.addEventListener('click', Abrir_Panel_Carrito);
        if (Boton_Cerrar_Carrito) Boton_Cerrar_Carrito.addEventListener('click', Cerrar_Panel_Carrito);
        if (Overlay_Carrito) Overlay_Carrito.addEventListener('click', Cerrar_Panel_Carrito);

        const Boton_Checkout = document.getElementById('checkout-btn');
        if (Boton_Checkout) {
            Boton_Checkout.addEventListener('click', Generar_Boleta_PDF);
        }

        // Toggle Filtros
        const Boton_Toggle_Filtros = document.getElementById('filters-toggle-btn');
        const Panel_Filtros = document.getElementById('dashboard-filters');

        if (Boton_Toggle_Filtros && Panel_Filtros) {
            Boton_Toggle_Filtros.addEventListener('click', () => {
                Panel_Filtros.classList.toggle('collapsed');
                Boton_Toggle_Filtros.classList.toggle('active');
                const Texto_Span = Boton_Toggle_Filtros.querySelector('span');
                if (Texto_Span) {
                    Texto_Span.textContent = Panel_Filtros.classList.contains('collapsed') ? 'Filtros' : 'Ocultar filtros';
                }
            });
        }

        // Toggle Chatbot Móvil (Overlay)
        const Panel_Chatbot_Movil = document.getElementById('dashboard-chat');
        const Boton_Chat_Movil = document.getElementById('mobile-chat-toggle');

        if (Boton_Chat_Movil && Panel_Chatbot_Movil) {
            Boton_Chat_Movil.addEventListener('click', () => {
                Panel_Chatbot_Movil.classList.add('open');
            });
            Panel_Chatbot_Movil.addEventListener('click', (e) => {
                if (e.target === Panel_Chatbot_Movil) Panel_Chatbot_Movil.classList.remove('open');
            });
        }
    }

    function Abrir_Panel_Carrito() {
        Panel_Carrito.classList.add('open');
        Overlay_Carrito.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function Cerrar_Panel_Carrito() {
        Panel_Carrito.classList.remove('open');
        Overlay_Carrito.classList.remove('show');
        document.body.style.overflow = 'auto';
    }

    function Generar_Boleta_PDF() {
        if (Carrito_Actual.length === 0) {
            alert('Tu carrito está vacío. Agrega productos para comprar.');
            return;
        }

        fetch(`${URL_Base_API}/generate_pdf`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ carrito: Carrito_Actual, session_id: Session_ID_Unico })
        })
        .then(response => {
            if (!response.ok) throw new Error('Error en el servidor');
            return response.blob();
        })
        .then(blob => {
            const pdfUrl = URL.createObjectURL(blob);
            window.open(pdfUrl, '_blank');
            
            Carrito_Actual = [];
            Guardar_Carrito();
            Actualizar_UI_Carrito();
            Cerrar_Panel_Carrito();
            
            const chatWindow = document.getElementById('chat-window');
            if (chatWindow && typeof Agregar_Mensaje_Chat === 'function') {
                const Panel_Derecho = document.getElementById('dashboard-right');
                if (Panel_Derecho && window.innerWidth <= 768 && !Panel_Derecho.classList.contains('mobile-open')) {
                    Panel_Derecho.classList.add('mobile-open');
                }
                Agregar_Mensaje_Chat('¡Compra finalizada exitosamente! He generado tu boleta de venta en formato PDF.', 'bot');
            }
        })
        .catch(err => {
            console.error('Error generando PDF:', err);
            alert('Error al generar el PDF de la boleta.');
        });
    }

    // ============================================================
    // CHATBOT LOGIC (Conexión real con PyTorch backend)
    // ============================================================
    const Boton_Enviar_Chat = document.getElementById('send-chat');
    const Entrada_Chat = document.getElementById('chat-input');
    const Mensajes_Chat = document.getElementById('chat-messages');
    const Boton_Microfono = document.getElementById('mic-btn');
    const Session_ID_Unico = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();

    function Enviar_Mensaje() {
        const Texto_Usuario = Entrada_Chat.value.trim();
        if (!Texto_Usuario) return;
        Reproducir_Sonido('enviar');
        Limpiar_Sugerencias_Chat();
        Agregar_Mensaje_Chat(Texto_Usuario, 'user');
        Entrada_Chat.value = '';
        Obtener_Respuesta_Chat(Texto_Usuario);
    }

    function Obtener_Respuesta_Chat(Mensaje_Usuario, Id_Producto_En_Contexto = null) {
        // Mostrar indicador escribiendo
        const Indicador_De_Escritura = document.createElement('div');
        Indicador_De_Escritura.className = 'message bot typing-indicator';
        Indicador_De_Escritura.innerHTML = '<span></span><span></span><span></span>';
        Mensajes_Chat.appendChild(Indicador_De_Escritura);
        Mensajes_Chat.scrollTop = Mensajes_Chat.scrollHeight;

        const Carga_Util = {
            message: Mensaje_Usuario,
            session_id: Session_ID_Unico,
            catalog_source: 'scraped',
        };

        const Id_De_Contexto_Para_Enviar = Id_Producto_En_Contexto !== null
            ? Id_Producto_En_Contexto
            : Id_De_Producto_En_Contexto_Chat;
        
        if (Id_De_Contexto_Para_Enviar !== null) {
            Carga_Util.context_product_id = Id_De_Contexto_Para_Enviar;
        }

        fetch(`${URL_Base_API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Carga_Util)
        })
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            // Remover indicador de escritura
            Indicador_De_Escritura.remove();

            const Tags_Que_Mantienen_Contexto = new Set([
                'contexto_iniciado', 'consulta_precio', 'consultar_precio_item', 'consultar_stock_item', 'colores'
            ]);
            const Tags_Que_Limpian_Contexto = new Set([
                'buscar_producto', 'filtrar_categoria', 'filtrar_genero', 'saludo', 'agradecimiento',
                'despedida', 'promociones', 'pedidos', 'reclamos', 'informacion_tienda', 'fuera_de_dominio'
            ]);

            if (Id_Producto_En_Contexto !== null && data.tag === 'contexto_iniciado') {
                Id_De_Producto_En_Contexto_Chat = Id_Producto_En_Contexto;
            } else if (Tags_Que_Mantienen_Contexto.has(data.tag)) {
                if (Id_De_Contexto_Para_Enviar !== null) {
                    Id_De_Producto_En_Contexto_Chat = Id_De_Contexto_Para_Enviar;
                }
            } else if (Tags_Que_Limpian_Contexto.has(data.tag)) {
                Id_De_Producto_En_Contexto_Chat = null;
            }
            
            Reproducir_Sonido('recibir');
            Agregar_Mensaje_Chat(data.response || 'No pude procesar la respuesta del servidor.', 'bot');
            const Sugerencias_Coherentes = Obtener_Sugerencias_Coherentes(data.tag, data.filter_action || {});
            Renderizar_Sugerencias_Chat(Sugerencias_Coherentes);
            
            // Si el bot indica añadir al carrito
            if (data.add_to_cart && data.product) {
                Agregar_Al_Carrito(data.product);
            }

            // Si hay filter_action, recargar catálogo y aplicar el filtro
            if (data.filter_action) {
                setTimeout(async () => {
                    // Recargar productos desde el servidor para incluir productos nuevos/editados
                    const Productos_Actualizados = await Cargar_Productos_Desde_Json();
                    if (Productos_Actualizados.length) {
                        Datos_De_Productos = Productos_Actualizados;
                        Configurar_Rango_De_Precio_Inicial();
                    }
                    Aplicar_Filtro_Desde_Chat(data.filter_action);
                }, 500);
            }
        })
        .catch(err => {
            Indicador_De_Escritura.remove();
            console.error('Error:', err);
            Agregar_Mensaje_Chat('El Asistente Vitural esta fuera de linea.', 'bot');
        });
    }

    function Agregar_Mensaje_Chat(Texto_Mensaje, Remitente) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${Remitente}`;
        msgDiv.innerText = Texto_Mensaje;
        Mensajes_Chat.appendChild(msgDiv);
        Mensajes_Chat.scrollTop = Mensajes_Chat.scrollHeight;
    }

    function Limpiar_Sugerencias_Chat() {
        Mensajes_Chat.querySelectorAll('.chat-suggestions').forEach(Nodo => Nodo.remove());
    }

    let Indice_De_Rotacion_Sugerencias = 0;

    function Seleccionar_Sugerencias_Variadas(Lista_De_Sugerencias, Maximo = 3) {
        const Sugerencias_Unicas = [];
        for (const Sugerencia of Lista_De_Sugerencias) {
            if (Sugerencia && !Sugerencias_Unicas.includes(Sugerencia)) {
                Sugerencias_Unicas.push(Sugerencia);
            }
        }

        if (Sugerencias_Unicas.length <= Maximo) {
            return Sugerencias_Unicas;
        }

        const Resultado = [];
        const Inicio = Indice_De_Rotacion_Sugerencias % Sugerencias_Unicas.length;
        for (let i = 0; i < Sugerencias_Unicas.length && Resultado.length < Maximo; i += 1) {
            Resultado.push(Sugerencias_Unicas[(Inicio + i) % Sugerencias_Unicas.length]);
        }

        Indice_De_Rotacion_Sugerencias += 1;
        return Resultado;
    }

    function Obtener_Sugerencias_Coherentes(Tag_Del_Bot, Accion_De_Filtro = {}) {
        const Categoria = Accion_De_Filtro?.category || null;
        const Color = Accion_De_Filtro?.color || null;
        const Genero = Accion_De_Filtro?.genero || null;
        const Talla = Accion_De_Filtro?.talla || null;

        const Sugerencias = [];

        if (Tag_Del_Bot === 'saludo') {
            return Seleccionar_Sugerencias_Variadas([
                '🛒 Cómo comprar',
                '💳 Métodos de pago',
                '🎧 Soporte y reclamos'
            ]);
        }

        if (Tag_Del_Bot === 'buscar_producto' || Tag_Del_Bot === 'filtrar_categoria' || Tag_Del_Bot === 'filtrar_genero') {
            if (Categoria === 'POLOS') {
                Sugerencias.push(
                    '👗 Polos para mujer',
                    '👨 Polos para hombre',
                    '🎨 Polos en color rojo',
                    '📏 Polos en talla M',
                    '💸 Polos menos de 80 soles',
                    '🏃 Polos para entrenamiento'
                );
            } else if (Categoria === 'CALZADO') {
                Sugerencias.push(
                    '👨 Zapatillas para hombre',
                    '👗 Zapatillas para mujer',
                    '🎨 Zapatillas en color negro',
                    '📏 Zapatillas en talla 42',
                    '💸 Zapatillas menos de 150 soles',
                    '🏃 Zapatillas para running'
                );
            } else if (Categoria === 'PANTALONES') {
                Sugerencias.push(
                    '👖 Joggers para hombre',
                    '👗 Leggings para mujer',
                    '🎨 Pantalones en color negro',
                    '📏 Pantalones en talla M',
                    '💸 Pantalones menos de 120 soles',
                    '🏃 Shorts para running'
                );
            } else if (Categoria === 'OTROS') {
                Sugerencias.push(
                    '🎒 Muéstrame mochilas',
                    '🧢 Quiero ver gorras',
                    '🎨 Accesorios en color negro',
                    '💸 Accesorios menos de 60 soles',
                    '🏷️ Quiero ver tomatodos'
                );
            } else {
                Sugerencias.push(
                    '👟 Zapatillas negras',
                    '👕 Polos de mujer',
                    '👖 Pantalones de hombre',
                    '🎒 Mochilas deportivas',
                    '💸 Menos de 100 soles',
                    '🎨 Color rojo'
                );
            }

            if (Color && !Talla) {
                Sugerencias.push(Categoria === 'CALZADO' ? '📏 En talla 42' : '📏 En talla M');
            }
            if (Genero && !Color) {
                Sugerencias.push('🎨 En color negro', '🎨 En color blanco');
            }
            if (Talla && !Genero) {
                Sugerencias.push('👗 Para mujer', '👨 Para hombre');
            }
        }

        if (Tag_Del_Bot === 'consultar_precio_item') {
            Sugerencias.push('📏 ¿Qué tallas tiene?', '🎨 ¿Qué colores hay?', '📦 ¿Hay stock disponible?', '🛍️ Muéstrame similares');
        }

        if (Tag_Del_Bot === 'consultar_stock_item') {
            Sugerencias.push('💰 ¿Cuál es el precio?', '🎨 ¿Qué colores hay?', '🛍️ Muéstrame productos similares', '👕 Quiero otra opción');
        }

        if (Tag_Del_Bot === 'colores') {
            Sugerencias.push('📏 ¿Hay talla M?', '💰 ¿Cuál es el precio?', '🛒 Quiero agregar al carrito', '👀 Muéstrame más opciones');
        }

        return Seleccionar_Sugerencias_Variadas(Sugerencias, 3);
    }

    function Renderizar_Sugerencias_Chat(Lista_De_Sugerencias) {
        Limpiar_Sugerencias_Chat();

        if (!Array.isArray(Lista_De_Sugerencias) || !Lista_De_Sugerencias.length) {
            return;
        }

        const Contenedor = document.createElement('div');
        Contenedor.className = 'chat-suggestions';

        Lista_De_Sugerencias.forEach(Texto_Sugerencia => {
            const Boton = document.createElement('button');
            Boton.type = 'button';
            Boton.className = 'chat-suggestion-btn';
            Boton.innerText = Texto_Sugerencia;
            Boton.addEventListener('click', () => {
                Entrada_Chat.value = Texto_Sugerencia.replace(/^[^\p{L}\p{N}]+/u, '').trim();
                Enviar_Mensaje();
            });
            Contenedor.appendChild(Boton);
        });

        Mensajes_Chat.appendChild(Contenedor);
        Mensajes_Chat.scrollTop = Mensajes_Chat.scrollHeight;
    }

    // Voice recognition logic (nativo del navegador primero, Whisper como fallback)
    const Constructor_De_Reconocimiento_Nativo = window.SpeechRecognition || window.webkitSpeechRecognition || null;
    let Reconocedor_De_Voz_Nativo = null;
    let Reconocimiento_Nativo_Activo = false;
    let Reconocimiento_Nativo_Con_Resultado = false;
    let Reconocimiento_Nativo_Fallo = false;
    let Reconocimiento_Nativo_Cancelado_Manual = false;

    let Grabadora_De_Medios = null;
    let Segmentos_De_Audio = [];

    async function Enviar_Audio_A_Whisper(Blob_De_Audio) {
        const Datos_De_Formulario = new FormData();
        Datos_De_Formulario.append('audio', Blob_De_Audio, 'voice.webm');

        try {
            const Respuesta_De_Transcripcion = await fetch(`${URL_Base_API}/transcribe`, {
                method: 'POST',
                body: Datos_De_Formulario
            });

            if (!Respuesta_De_Transcripcion.ok) {
                throw new Error(`HTTP ${Respuesta_De_Transcripcion.status}`);
            }

            const Datos_Transcritos = await Respuesta_De_Transcripcion.json();
            if (Datos_Transcritos.text) {
                Entrada_Chat.value = Datos_Transcritos.text;
                Enviar_Mensaje();
                return;
            }

            if (Datos_Transcritos.error) {
                Agregar_Mensaje_Chat('Error de voz: ' + Datos_Transcritos.error, 'bot');
                return;
            }

            Agregar_Mensaje_Chat('No pude transcribir tu audio con Whisper.', 'bot');
        } catch (Error_De_Voz) {
            console.error('Error al transcribir con Whisper:', Error_De_Voz);
            Agregar_Mensaje_Chat('No pude procesar tu voz en este momento.', 'bot');
        }
    }

    async function Iniciar_Grabacion_Con_Whisper() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            Agregar_Mensaje_Chat('Tu navegador no soporta captura de audio.', 'bot');
            return;
        }

        if (Grabadora_De_Medios && Grabadora_De_Medios.state === 'recording') {
            Grabadora_De_Medios.stop();
            Boton_Microfono.classList.remove('recording');
            return;
        }

        try {
            const Flujo_De_Audio = await navigator.mediaDevices.getUserMedia({ audio: true });
            Grabadora_De_Medios = new MediaRecorder(Flujo_De_Audio);
            Segmentos_De_Audio = [];

            Grabadora_De_Medios.ondataavailable = (Evento) => {
                Segmentos_De_Audio.push(Evento.data);
            };

            Grabadora_De_Medios.onstop = async () => {
                const Blob_De_Audio = new Blob(Segmentos_De_Audio, { type: 'audio/webm' });
                await Enviar_Audio_A_Whisper(Blob_De_Audio);
                Flujo_De_Audio.getTracks().forEach(Track => Track.stop());
            };

            Grabadora_De_Medios.start();
            Boton_Microfono.classList.add('recording');

            // Evita grabaciones largas cuando el fallback se activa automaticamente.
            setTimeout(() => {
                if (Grabadora_De_Medios && Grabadora_De_Medios.state === 'recording') {
                    Grabadora_De_Medios.stop();
                    Boton_Microfono.classList.remove('recording');
                }
            }, 7000);
        } catch (Error_De_Microfono) {
            console.error('Error accediendo al microfono:', Error_De_Microfono);
            Agregar_Mensaje_Chat('No se pudo acceder al microfono.', 'bot');
        }
    }

    function Asegurar_Reconocedor_Nativo() {
        if (!Constructor_De_Reconocimiento_Nativo || Reconocedor_De_Voz_Nativo) {
            return;
        }

        Reconocedor_De_Voz_Nativo = new Constructor_De_Reconocimiento_Nativo();
        Reconocedor_De_Voz_Nativo.lang = 'es-ES';
        Reconocedor_De_Voz_Nativo.interimResults = false;
        Reconocedor_De_Voz_Nativo.maxAlternatives = 1;
        Reconocedor_De_Voz_Nativo.continuous = false;

        Reconocedor_De_Voz_Nativo.onstart = () => {
            Reconocimiento_Nativo_Activo = true;
            Boton_Microfono.classList.add('recording');
        };

        Reconocedor_De_Voz_Nativo.onresult = (Evento) => {
            const Texto_Transcrito = (Evento.results?.[0]?.[0]?.transcript || '').trim();
            if (!Texto_Transcrito) {
                return;
            }

            Reconocimiento_Nativo_Con_Resultado = true;
            Entrada_Chat.value = Texto_Transcrito;
            Enviar_Mensaje();
        };

        Reconocedor_De_Voz_Nativo.onerror = (Evento) => {
            console.warn('Reconocimiento nativo fallido:', Evento.error);
            if (Evento.error !== 'aborted') {
                Reconocimiento_Nativo_Fallo = true;
            }
        };

        Reconocedor_De_Voz_Nativo.onend = () => {
            Reconocimiento_Nativo_Activo = false;
            Boton_Microfono.classList.remove('recording');

            if (!Reconocimiento_Nativo_Cancelado_Manual && (Reconocimiento_Nativo_Fallo || !Reconocimiento_Nativo_Con_Resultado)) {
                Agregar_Mensaje_Chat('No pude captar tu voz con el navegador. Intentare con Whisper.', 'bot');
                Iniciar_Grabacion_Con_Whisper();
            }
        };
    }

    function Iniciar_Reconocimiento_Nativo() {
        Asegurar_Reconocedor_Nativo();

        if (!Reconocedor_De_Voz_Nativo) {
            Iniciar_Grabacion_Con_Whisper();
            return;
        }

        try {
            Reconocimiento_Nativo_Con_Resultado = false;
            Reconocimiento_Nativo_Fallo = false;
            Reconocimiento_Nativo_Cancelado_Manual = false;
            Reconocedor_De_Voz_Nativo.start();
        } catch (Error_De_Reconocimiento) {
            console.warn('No se pudo iniciar reconocimiento nativo:', Error_De_Reconocimiento);
            Iniciar_Grabacion_Con_Whisper();
        }
    }

    if (Boton_Microfono) {
        Boton_Microfono.addEventListener('click', () => {
            if (Grabadora_De_Medios && Grabadora_De_Medios.state === 'recording') {
                Grabadora_De_Medios.stop();
                Boton_Microfono.classList.remove('recording');
                return;
            }

            if (Reconocimiento_Nativo_Activo && Reconocedor_De_Voz_Nativo) {
                Reconocimiento_Nativo_Cancelado_Manual = true;
                Reconocedor_De_Voz_Nativo.stop();
                Boton_Microfono.classList.remove('recording');
                return;
            }

            if (Constructor_De_Reconocimiento_Nativo) {
                Iniciar_Reconocimiento_Nativo();
                return;
            }

            Iniciar_Grabacion_Con_Whisper();
        });
    }

    if (Boton_Enviar_Chat) Boton_Enviar_Chat.addEventListener('click', Enviar_Mensaje);
    if (Entrada_Chat) {
        Entrada_Chat.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') Enviar_Mensaje();
        });
    }

    Renderizar_Sugerencias_Chat(Obtener_Sugerencias_Coherentes('saludo'));

    Inicializar_Dashboard().catch((Error_De_Inicio) => {
        console.error('No se pudo inicializar el dashboard:', Error_De_Inicio);
    });
});
