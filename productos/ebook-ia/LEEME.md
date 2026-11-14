# Ebook «La IA que trabaja por ti»

Producto digital de Estrateg IA Digital 3.0: guía práctica en PDF (A5, 87 páginas, interactivo) para pymes y autónomos: 17 capítulos y 2 anexos, 40 prompts, 8 guías por sector, agentes de IA, 12 infografías, 20 tarjetas de vídeo con QR y un plan de 30 días.

## Qué hay aquí y qué no

Este repositorio es **público**, así que el texto del ebook y el PDF **no se suben** (están en `.gitignore`). Se guardan en los archivos privados del proyecto. Aquí solo está:

- `build.py`: genera el PDF y la portada a partir de `contenido/*.md` (un archivo por capítulo). Marcas especiales: `::: figura NOMBRE` y `::: video | Título | búsqueda | texto`.
- `figuras.py`: las infografías en SVG.
- `robot.jpg`, `robot-plata.jpg`, `ciudad.jpg`: imágenes de portada y aperturas de capítulo (las mismas de la web).


La página de ventas está en `web/ebook/` y se publica con el resto de la web.

## Regenerar el PDF

1. Copia los capítulos (`*.md`) en `productos/ebook-ia/contenido/`.
2. `pip install markdown playwright qrcode pillow` (y `playwright install chromium` si no tienes Chromium).
3. `python3 productos/ebook-ia/build.py`

Salen `build/ebook-ia-para-tu-negocio.pdf` y `build/portada.png` (1600×2400, para la tienda).

## Ponerlo a la venta

1. Sube el PDF y la portada a la plataforma de cobro (Gumroad, Stripe o Shopify). La plataforma envía el PDF al comprador de forma automática.
2. Copia el enlace de pago en `CONFIG.checkoutUrl` al final de `web/ebook/index.html`. Ajusta `CONFIG.precio` si cambias el precio.
3. Mientras `checkoutUrl` esté vacío, el botón de compra lleva al formulario de contacto de la web («Reservar mi copia»).
