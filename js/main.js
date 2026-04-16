document.addEventListener('DOMContentLoaded', () => {
    // State management
    let Productos_Mostrados = [];
    let Datos_De_Productos = Normalizar_Lista_De_Productos(Array.isArray(window.PRODUCT_DATA) ? window.PRODUCT_DATA : []);
    const URL_Base_API = window.SENATI_API_URL || 'http://localhost:5000';
    let Categoria_Actual = 'all';
    let Color_Actual = null;
    let Talla_Actual = null;
    let Genero_Actual = null;
    let Precio_Minimo_Actual = null;
    let Precio_Maximo_Actual = null;
    let Precio_Minimo_Base = 0;
    let Precio_Maximo_Base = 500;
    let Texto_De_Busqueda = '';
    let Cantidad_A_Mostrar = 12;
    let Carrito_Actual = JSON.parse(localStorage.getItem('senati_cart')) || [];

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
    const Boton_Limpiar_Precio = document.getElementById('clear-price-filter');
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

    function Normalizar_Categoria_Producto(Categoria_Original) {
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
                category: Normalizar_Categoria_Producto(Producto.category),
            }));
    }

    // Initialization
    async function Cargar_Productos_Desde_Json() {
        const Rutas_De_Carga = ['data/products_scraped.json', `${URL_Base_API}/products?source=scraped`];

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
                console.error(`No se pudo cargar productos desde ${Ruta}:`, Error_De_Carga);
            }
        }

        return [];
    }

    function Restablecer_Filtros_Visuales_Y_Estado() {
        Categoria_Actual = 'all';
        Color_Actual = null;
        Talla_Actual = null;
        Genero_Actual = null;
        Texto_De_Busqueda = '';
        Cantidad_A_Mostrar = 12;

        if (Entrada_Busqueda) Entrada_Busqueda.value = '';

        Tarjetas_De_Categoria.forEach(Boton => {
            Boton.classList.toggle('active', Boton.dataset.category === 'all');
        });

        const Circulos_De_Color = document.querySelectorAll('.color-circle');
        Circulos_De_Color.forEach(Circulo => {
            Circulo.classList.toggle('active', Circulo.dataset.color === 'all');
        });

        Actualizar_Botones_De_Genero();
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

    // ============================================================
    // PRODUCT RENDERING (Con soporte para filtro por color)
    // ============================================================
    function Renderizar_Productos() {
        Lista_De_Productos.classList.toggle('source-scraped', true);

        const Texto_Busqueda_En_Minusculas = Texto_De_Busqueda.toLowerCase();
        const Productos_Filtrados = Datos_De_Productos.filter(Producto => {
            const Texto_Nombre = (Producto.name || '').toLowerCase();
            const Texto_Descripcion = (Producto.description || '').toLowerCase();
            const Colores_Disponibles = Obtener_Colores_Producto(Producto);
            const Texto_Colores = Colores_Disponibles.join(' ').toLowerCase();

            const Coincide_Categoria = Categoria_Actual === 'all' || Producto.category === Categoria_Actual;
            const Coincide_Color = !Color_Actual || Colores_Disponibles.includes(Color_Actual);
            const Coincide_Talla = !Talla_Actual || (Producto.tallas && Producto.tallas.includes(Talla_Actual));
            const Coincide_Genero = !Genero_Actual || Producto.genero === Genero_Actual;
            const Coincide_Precio_Minimo = Precio_Minimo_Actual === null || Producto.price >= Precio_Minimo_Actual;
            const Coincide_Precio_Maximo = Precio_Maximo_Actual === null || Producto.price <= Precio_Maximo_Actual;
            const Coincide_Busqueda =
                Texto_Nombre.includes(Texto_Busqueda_En_Minusculas)
                || Texto_Descripcion.includes(Texto_Busqueda_En_Minusculas)
                || Texto_Colores.includes(Texto_Busqueda_En_Minusculas);

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
        const Dots_Colores = Colores_Disponibles
            .map(Color_Item => `<div class="card-color-dot" style="background-color: ${Obtener_Color_Hex(Color_Item)};" title="${Color_Item}"></div>`)
            .join('');
        const catEmoji = Obtener_Emoji_Categoria(product.category);
        const Url_Imagen_Producto = Obtener_Imagen_Producto(product);
        const Visual_De_Tarjeta = Url_Imagen_Producto
            ? `<img class="card-image" src="${Url_Imagen_Producto}" alt="${product.name}" loading="lazy" referrerpolicy="no-referrer">`
            : `<span class="card-emoji">${catEmoji}</span>`;
        
        div.innerHTML = `
            <div class="card-top">
                <div class="card-media">${Visual_De_Tarjeta}</div>
                <div class="card-color-dots">${Dots_Colores}</div>
            </div>
            
            <span class="card-cat">${product.category}</span>
            <h3>${product.name}</h3>
            
            <div class="card-meta">
                <span>Colores: ${Colores_Como_Texto}</span>
                <br>
                <span>Genero: ${Genero_Producto}</span>
            </div>
            <div class="card-tallas-visor">
                <span class="tallas-etiqueta">Tallas disponibles</span>
                <span class="tallas-valores">${Tallas_Como_Texto}</span>
            </div>

            <div class="card-stock">Stock: ${Stock_Producto !== null ? `${Stock_Producto} unidades` : 'No disponible'}</div>
            
            <div class="card-price-row">
                <span class="card-price">S/ ${product.price.toFixed(2)}</span>
                <div class="card-actions">
                    <button class="card-btn consult-bot-quick" title="Preguntar" data-id="${product.id}">
                        <i class="fa-solid fa-robot"></i>
                    </button>
                    <button class="card-btn add-to-cart-quick" title="Agregar al carrito" data-id="${product.id}">
                        <i class="fa-solid fa-plus"></i>
                    </button>
                </div>
            </div>
        `;

        div.querySelector('.add-to-cart-quick').addEventListener('click', () => Agregar_Al_Carrito(product));
        div.querySelector('.consult-bot-quick').addEventListener('click', () => Consultar_Producto(product));

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

    function Consultar_Producto(product) {
        // Enviar un mensaje visual distinto al chat
        const infoMsg = `[Consulta iniciada para: ${product.name}]`;
        Agregar_Mensaje_Chat(infoMsg, 'user');
        
        // Enviar al backend indicándole el contexto del producto ocultamente
        Obtener_Respuesta_Chat('quiero saber mas de este producto', product.id);
    }

    // ============================================================
    // FILTRADO DESDE EL CHAT (filter_action)
    // ============================================================
    function Aplicar_Filtro_Desde_Chat(Accion_De_Filtro) {
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

        if (Array.isArray(Accion_De_Filtro.keywords) && Accion_De_Filtro.keywords.length) {
            Texto_De_Busqueda = Accion_De_Filtro.keywords.join(' ').trim();
        } else {
            Texto_De_Busqueda = '';
        }
        if (Entrada_Busqueda) {
            Entrada_Busqueda.value = Texto_De_Busqueda;
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

        Cantidad_A_Mostrar = 12;
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
                itemDiv.innerHTML = `
                    <div class="cart-item-emoji">${Obtener_Emoji_Categoria(item.category)}</div>
                    <div class="cart-item-info">
                        <h4>${item.name}</h4>
                        <p>S/ ${item.price.toFixed(2)} x ${item.quantity}</p>
                    </div>
                    <button class="remove-item" data-id="${item.id}">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                `;
                Lista_Items_Carrito.appendChild(itemDiv);
                itemDiv.querySelector('.remove-item').addEventListener('click', () => Quitar_Del_Carrito(item.id));
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
            Cantidad_A_Mostrar = 12;
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
                Cantidad_A_Mostrar = 12;
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

        if (Boton_Limpiar_Precio) {
            Boton_Limpiar_Precio.addEventListener('click', () => {
                Precio_Minimo_Actual = Precio_Minimo_Base;
                Precio_Maximo_Actual = Precio_Maximo_Base;
                if (Slider_Precio_Minimo) Slider_Precio_Minimo.value = String(Precio_Minimo_Base);
                if (Slider_Precio_Maximo) Slider_Precio_Maximo.value = String(Precio_Maximo_Base);
                Actualizar_Textos_Rango_De_Precio();
                Cantidad_A_Mostrar = 12;
                Renderizar_Productos();
            });
        }

        Tarjetas_De_Categoria.forEach(card => {
            card.addEventListener('click', () => {
                Tarjetas_De_Categoria.forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                Categoria_Actual = card.dataset.category;
                Cantidad_A_Mostrar = 12;
                Renderizar_Productos();
            });
        });

        if (Botones_De_Genero && Botones_De_Genero.length) {
            Botones_De_Genero.forEach(Boton => {
                Boton.addEventListener('click', () => {
                    Genero_Actual = Boton.dataset.gender === 'all' ? null : Boton.dataset.gender;
                    Actualizar_Botones_De_Genero();
                    Cantidad_A_Mostrar = 12;
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
                } else {
                    Color_Actual = circle.dataset.color;
                }
                Cantidad_A_Mostrar = 12;
                Renderizar_Productos();
            });
        });

        if (Boton_Cargar_Mas) {
            Boton_Cargar_Mas.addEventListener('click', () => {
                Cantidad_A_Mostrar += 12;
                Renderizar_Productos();
            });
        }

        if (Boton_Carrito) Boton_Carrito.addEventListener('click', Abrir_Panel_Carrito);
        if (Boton_Cerrar_Carrito) Boton_Cerrar_Carrito.addEventListener('click', Cerrar_Panel_Carrito);
        if (Overlay_Carrito) Overlay_Carrito.addEventListener('click', Cerrar_Panel_Carrito);
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

    // ============================================================
    // CHATBOT LOGIC (Conexión real con PyTorch backend)
    // ============================================================
    const Boton_Enviar_Chat = document.getElementById('send-chat');
    const Entrada_Chat = document.getElementById('chat-input');
    const Mensajes_Chat = document.getElementById('chat-messages');
    const Boton_Microfono = document.getElementById('mic-btn');

    function Enviar_Mensaje() {
        const Texto_Usuario = Entrada_Chat.value.trim();
        if (!Texto_Usuario) return;
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
            session_id: 'user_local',
            catalog_source: 'scraped',
        };
        
        if (Id_Producto_En_Contexto !== null) {
            Carga_Util.context_product_id = Id_Producto_En_Contexto;
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
            
            Agregar_Mensaje_Chat(data.response || 'No pude procesar la respuesta del servidor.', 'bot');
            
            // Si hay filter_action, aplicar el filtro en el catálogo
            if (data.filter_action) {
                setTimeout(() => {
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

    // Voice recording logic
    let Grabadora_De_Medios = null;
    let Segmentos_De_Audio = [];

    if (Boton_Microfono) {
        Boton_Microfono.addEventListener('click', async () => {
            if (Grabadora_De_Medios && Grabadora_De_Medios.state === 'recording') {
                Grabadora_De_Medios.stop();
                Boton_Microfono.classList.remove('recording');
                return;
            }

            try {
                const Flujo_De_Audio = await navigator.mediaDevices.getUserMedia({ audio: true });
                Grabadora_De_Medios = new MediaRecorder(Flujo_De_Audio);
                Segmentos_De_Audio = [];

                Grabadora_De_Medios.ondataavailable = e => {
                    Segmentos_De_Audio.push(e.data);
                };

                Grabadora_De_Medios.onstop = async () => {
                    const Blob_De_Audio = new Blob(Segmentos_De_Audio, { type: 'audio/webm' });
                    const Datos_De_Formulario = new FormData();
                    Datos_De_Formulario.append('audio', Blob_De_Audio, 'voice.webm');

                    try {
                        const Respuesta_De_Transcripcion = await fetch(`${URL_Base_API}/transcribe`, {
                            method: 'POST',
                            body: Datos_De_Formulario
                        });

                        const Datos_Transcritos = await Respuesta_De_Transcripcion.json();
                        if (Datos_Transcritos.text) {
                            Entrada_Chat.value = Datos_Transcritos.text;
                            Enviar_Mensaje();
                        } else if (Datos_Transcritos.error) {
                            Agregar_Mensaje_Chat('Error de voz: ' + Datos_Transcritos.error, 'bot');
                        }
                    } catch (Error_De_Voz) {
                        console.error('Error al transcribir:', Error_De_Voz);
                        Agregar_Mensaje_Chat('No pude procesar tu voz en este momento.', 'bot');
                    }

                    Flujo_De_Audio.getTracks().forEach(track => track.stop());
                };

                Grabadora_De_Medios.start();
                Boton_Microfono.classList.add('recording');
            } catch (Error_De_Microfono) {
                console.error('Error accediendo al microfono:', Error_De_Microfono);
                Agregar_Mensaje_Chat('No se pudo acceder al microfono.', 'bot');
            }
        });
    }

    if (Boton_Enviar_Chat) Boton_Enviar_Chat.addEventListener('click', Enviar_Mensaje);
    if (Entrada_Chat) {
        Entrada_Chat.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') Enviar_Mensaje();
        });
    }

    Inicializar_Dashboard().catch((Error_De_Inicio) => {
        console.error('No se pudo inicializar el dashboard:', Error_De_Inicio);
    });
});
