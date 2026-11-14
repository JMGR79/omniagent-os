# Ebook «La IA que trabaja por ti»

Producto digital de Estrateg IA Digital 3.0: guía práctica en PDF (A5, 37 páginas) para pymes y autónomos, con 30 prompts, 6 automatizaciones sin código y un plan de 30 días.

## Qué hay aquí y qué no

Este repositorio es **público**, así que el texto del ebook y el PDF **no se suben** (están en `.gitignore`). Se guardan en los archivos privados del proyecto. Aquí solo está:

- `build.py`: genera el PDF y la portada a partir de `contenido/ebook.md`.
- `robot.jpg`: imagen de la portada (la misma de la web).

La página de ventas está en `web/ebook/` y se publica con el resto de la web.

## Regenerar el PDF

1. Copia `ebook.md` en `productos/ebook-ia/contenido/ebook.md`.
2. `pip install markdown playwright` (y `playwright install chromium` si no tienes Chromium).
3. `python3 productos/ebook-ia/build.py`

Salen `build/ebook-ia-para-tu-negocio.pdf` y `build/portada.png` (1600×2400, para la tienda).

## Ponerlo a la venta

1. Sube el PDF y la portada a la plataforma de cobro (Gumroad, Stripe o Shopify). La plataforma envía el PDF al comprador de forma automática.
2. Copia el enlace de pago en `CONFIG.checkoutUrl` al final de `web/ebook/index.html`. Ajusta `CONFIG.precio` si cambias el precio.
3. Mientras `checkoutUrl` esté vacío, el botón de compra lleva al formulario de contacto de la web («Reservar mi copia»).
