# Web pública · EstrategIA Digital 3.0

Landing de la agencia. Es un sitio estático (un solo `index.html`, sin compilación), pensado para crecer después hacia la web completa.

## Qué cambiar y dónde

Todo lo editable está en el bloque `CONFIG` al final de `index.html`:

- `redes`: pega la URL de cada perfil (YouTube, TikTok, Instagram, X, LinkedIn, WhatsApp como `https://wa.me/34XXXXXXXXX`). Si una está vacía aparece como «enlace pendiente».
- `email`: correo de contacto.
- `formEndpoint`: URL que recibe el formulario en JSON (`nombre`, `telefono`, `email`, `servicio`, `mensaje`, `origen`, `fecha`). Puede ser un webhook de n8n de OmniAgent (para que el lead entre en el sistema) o Formspree. Mientras esté vacío, el formulario no envía nada y pide escribir al email.

## Casos reales y testimonios

En `CONFIG.casos` y `CONFIG.testimonios`. Mientras estén vacías, la web muestra huecos marcados como «en preparación» o «pendiente». Añade solo casos y testimonios reales, con permiso del cliente; el formato de cada uno está comentado en el propio bloque.

## Estilo

Neón violeta (#A855F7) y cian (#22D3EE) sobre azul noche, tipografías Orbitron (marca) y Exo 2 (texto), y los robots de `assets/`. Es el mismo estilo que el banner de YouTube.

## Vídeos y contenido

La sección «Contenido» lee `contenido.json`. Para publicar un vídeo nuevo, añade un objeto al principio de la lista `videos` con `titulo`, `plataforma`, `url` y, si quieres, `miniatura`, `duracion`, `fecha` y `estado`. Un flujo de n8n puede reescribir este archivo cada vez que se publique un vídeo, y la web se actualiza sola.

## Publicar

- **Render:** el servicio `estrategia-web` del `render.yaml` publica esta carpeta como sitio estático gratuito.
- **Netlify:** arrastra la carpeta `web/` o conecta el repo con «base directory» `web`.
- Después, apunta tu dominio propio al servicio.
