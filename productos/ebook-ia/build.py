#!/usr/bin/env python3
"""Genera el ebook interactivo (PDF) y la portada (PNG) a partir de contenido/*.md.

Requisitos: pip install markdown playwright qrcode pillow  (y un Chromium para Playwright)
Uso:        python3 productos/ebook-ia/build.py
Salida:     productos/ebook-ia/build/ebook-ia-para-tu-negocio.pdf
            productos/ebook-ia/build/portada.png  (1600x2400, para la tienda)

Marcas especiales en el Markdown (una por línea):
  ::: figura NOMBRE                       -> infografía de figuras.py
  ::: video | Título | búsqueda | texto   -> tarjeta de vídeo con enlace y código QR
"""
import base64, io, os, pathlib, re, urllib.parse
import markdown, qrcode
from PIL import Image
from playwright.sync_api import sync_playwright
import figuras

RAIZ = pathlib.Path(__file__).resolve().parent
CONTENIDO = RAIZ / "contenido"
SALIDA = RAIZ / "build"
SALIDA.mkdir(exist_ok=True)

TITULO = "La IA que trabaja por ti"
SUBTITULO = "Guía práctica para pymes y autónomos: ahorra 10 horas a la semana en 30 días"
AUTOR = "Estrateg IA Digital 3.0"
EDICION = "Segunda edición ampliada · noviembre de 2026"
FUENTES = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Exo+2:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap">'


def img64(nombre, ancho=1000, calidad=78):
    im = Image.open(RAIZ / nombre).convert("RGB")
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=calidad)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


ROBOT = img64("robot.jpg")
IMAGENES = [img64("robot.jpg"), img64("robot-plata.jpg"), img64("ciudad.jpg")]


def qr64(url):
    q = qrcode.QRCode(border=1, box_size=6); q.add_data(url); q.make(fit=True)
    b = io.BytesIO(); q.make_image(fill_color="#1B1F3B", back_color="white").save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def video(titulo, busqueda, texto):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(busqueda)
    return (f'<div class="video"><a class="vthumb" href="{url}"><span>▶</span></a>'
            f'<div class="vtxt"><div class="vtag">Vídeo recomendado</div><a class="vtit" href="{url}">{titulo}</a>'
            f'<p>{texto}</p><a class="vlink" href="{url}">Ver tutoriales en YouTube ↗</a></div>'
            f'<img class="qr" src="{qr64(url)}" alt="Código QR del vídeo"></div>')


def preprocesar(md):
    def rep(m):
        linea = m.group(1).strip()
        if linea.startswith("figura"):
            return "\n" + figuras.TODAS[linea.split()[1]]() + "\n"
        if linea.startswith("video"):
            _, t, q, d = [x.strip() for x in linea.split("|")]
            return "\n" + video(t, q, d) + "\n"
        raise ValueError(linea)
    return re.sub(r"(?m)^::: (.+)$", rep, md)


PORTADA_CSS = """
.cover{width:100%;height:100%;position:relative;overflow:hidden;background:#070A18;color:#EAF0FF;font-family:'Exo 2',sans-serif}
.cover .img{position:absolute;inset:0;background:url(__ROBOT__) 50% 40%/cover;opacity:.75}
.cover .fade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(7,10,24,.92) 0%,rgba(7,10,24,.35) 38%,rgba(7,10,24,.35) 55%,rgba(7,10,24,.97) 82%)}
.cover .grid{position:absolute;inset:0;background-image:linear-gradient(rgba(168,85,247,.12) 1px,transparent 1px),linear-gradient(90deg,rgba(168,85,247,.12) 1px,transparent 1px);background-size:6% 4%}
.cover .txt{position:absolute;inset:7% 8%;display:flex;flex-direction:column;justify-content:space-between}
.cover .tag{font:700 .9em 'Orbitron';letter-spacing:.25em;color:#22D3EE;text-transform:uppercase}
.cover h1{font:900 3.05em/1.02 'Orbitron';text-transform:uppercase;margin:.3em 0 0;text-shadow:0 0 .5em rgba(168,85,247,.6);color:#EAF0FF;border:0;padding:0;page-break-before:auto}
.cover h1 b{background:linear-gradient(90deg,#A855F7,#22D3EE);-webkit-background-clip:text;color:transparent}
.cover .sub{font-size:1.45em;font-weight:600;line-height:1.3;max-width:20em;color:#D5DBF2}
.cover .badge{display:inline-block;margin-top:1em;padding:.4em .9em;border:2px solid #22D3EE;border-radius:.5em;font:700 .95em 'Orbitron';color:#22D3EE;letter-spacing:.08em}
.cover .autor{font:700 1em 'Orbitron';letter-spacing:.18em;text-transform:uppercase;border-top:2px solid #A855F7;padding-top:.8em}
""".replace("__ROBOT__", ROBOT)


def portada_html():
    return f"""<div class="cover"><div class="img"></div><div class="fade"></div><div class="grid"></div>
<div class="txt"><div><div class="tag">Ebook interactivo · Guía práctica</div><h1>La <b>IA</b> que trabaja por ti</h1></div>
<div><div class="sub">{SUBTITULO}</div><div class="badge">40 PROMPTS · 8 SECTORES · AGENTES · PLAN DE 30 DÍAS</div></div>
<div class="autor">{AUTOR}</div></div></div>"""


CSS = PORTADA_CSS + """
@page{size:A5;margin:15mm 13mm 17mm}
@page:first{margin:0}
body{font:10.3pt/1.55 'Exo 2',sans-serif;color:#1B1F3B;margin:0}
.cover{width:148mm;height:210mm;font-size:9.5pt;page-break-after:always}
a{color:#7C3AED;text-decoration:none;border-bottom:1px solid rgba(124,58,237,.35)}
.legal{page-break-after:always;font-size:8.3pt;color:#555;display:flex;flex-direction:column;justify-content:flex-end;height:172mm}
.toc{page-break-after:always}.toc h2{font:900 16pt 'Orbitron';color:#7C3AED;text-transform:uppercase;margin:0 0 .6em}
.toc ol{list-style:none;padding:0;margin:0;font-size:9.6pt}.toc li{padding:.28em 0;border-bottom:1px dotted #C9C3E6}.toc a{color:#1B1F3B;border:0}
.opener{page-break-before:always;height:46mm;margin:0 0 6mm;border-radius:8px;position:relative;overflow:hidden;background-size:cover;background-position:center}
.opener::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(7,10,24,.92),rgba(7,10,24,.45) 60%,rgba(124,58,237,.25))}
.opener span{position:absolute;left:6mm;bottom:5mm;z-index:1;font:900 30pt 'Orbitron';color:#fff;text-shadow:0 0 14px rgba(168,85,247,.9)}
.opener small{position:absolute;left:6mm;top:5mm;z-index:1;font:700 7pt 'Orbitron';letter-spacing:.25em;color:#22D3EE;text-transform:uppercase}
h1{font:900 15.5pt/1.18 'Orbitron';color:#7C3AED;text-transform:uppercase;margin:0 0 .8em;padding-bottom:.4em;border-bottom:3px solid #22D3EE}
h1.sin-opener{page-break-before:always}
h2{font:800 12.5pt 'Exo 2';color:#0E7490;margin:1.3em 0 .4em;page-break-after:avoid}
p,li{orphans:3;widows:3}
blockquote{margin:1em 0;padding:.6em .9em;background:#F4EEFF;border-left:4px solid #A855F7;border-radius:4px;page-break-inside:avoid}
blockquote p{margin:.3em 0}
table{width:100%;border-collapse:collapse;font-size:8.6pt;margin:1em 0;page-break-inside:avoid}
th{background:#1B1F3B;color:#fff;text-align:left;padding:.4em}td{padding:.38em;border-bottom:1px solid #DDD;vertical-align:top}
tr:nth-child(even) td{background:#F7F7FC}
strong{color:#111}
ul li::marker{color:#A855F7}
.fig{margin:1.1em 0;page-break-inside:avoid;background:#fff;border:1px solid #E4DEF7;border-radius:10px;padding:8px 8px 6px}
.fig svg{width:100%;height:auto;display:block}
.fig figcaption{font-size:8pt;color:#5B6390;text-align:center;margin-top:4px;font-style:italic}
.video{display:flex;gap:9px;align-items:center;margin:1em 0;padding:8px;border-radius:10px;background:#0C1026;color:#EAF0FF;page-break-inside:avoid}
.video a{border:0}
.vthumb{flex:0 0 22mm;height:15mm;border-radius:7px;background:linear-gradient(135deg,#A855F7,#22D3EE);display:grid;place-items:center;color:#fff;font-size:15pt}
.vthumb span{width:9mm;height:9mm;border-radius:50%;background:rgba(7,10,24,.55);display:grid;place-items:center;font-size:10pt}
.vtxt{flex:1;min-width:0}
.vtag{font:700 6.5pt 'Orbitron';letter-spacing:.18em;color:#22D3EE;text-transform:uppercase}
.vtit{display:block;color:#fff;font-weight:800;font-size:9.6pt;line-height:1.25;margin:2px 0}
.vtxt p{margin:0;font-size:8pt;color:#A3ADCF;line-height:1.35}
.vlink{color:#22D3EE;font-size:8pt;font-weight:700}
.prompt{page-break-inside:avoid}
li.chk{list-style:none;margin-left:-1.1em}
.qr{flex:0 0 17mm;width:17mm;height:17mm;border-radius:4px;background:#fff}
"""


def libro_html():
    md = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(CONTENIDO.glob("*.md")))
    cuerpo = markdown.markdown(preprocesar(md), extensions=["tables", "attr_list", "sane_lists", "md_in_html"])
    cuerpo = cuerpo.replace("<li>[ ]", '<li class="chk">☐').replace("[ ]", "☐")
    # título de prompt + bloque de prompt siempre juntos
    cuerpo = re.sub(r"(<p><strong>\d+\.[^<]*</strong></p>\s*<blockquote>.*?</blockquote>)", r'<div class="prompt">\1</div>', cuerpo, flags=re.S)
    titulos = re.findall(r'<h1 id="([^"]+)">(.*?)</h1>', cuerpo)
    indice = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in titulos)

    n = 0
    def opener(m):
        nonlocal n
        ident, txt = m.group(1), m.group(2)
        num = re.match(r"(\d+)\.", txt)
        if not num:
            return f'<h1 id="{ident}" class="sin-opener">{txt}</h1>'
        img = IMAGENES[n % len(IMAGENES)]; n += 1
        return (f'<div class="opener" style="background-image:url({img})"><small>Capítulo</small><span>{int(num.group(1)):02d}</span></div>'
                f'<h1 id="{ident}">{txt}</h1>')
    cuerpo = re.sub(r'<h1 id="([^"]+)">(.*?)</h1>', opener, cuerpo)

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{TITULO}</title>{FUENTES}<style>{CSS}</style></head><body>
{portada_html()}
<div class="legal"><p><b>{TITULO}</b><br>{SUBTITULO}</p><p>{EDICION}<br>© 2026 {AUTOR}. Todos los derechos reservados.</p>
<p>Esta copia es para uso personal del comprador. No está permitida su reventa ni su distribución.</p>
<p>Los nombres de herramientas y marcas citados pertenecen a sus propietarios y se mencionan solo con fines informativos; este libro no está patrocinado por ninguna de ellas. Los ejemplos de personas y negocios son ilustrativos. Las tarjetas de vídeo enlazan a búsquedas de YouTube con tutoriales de terceros, cuyo contenido no controlamos. El contenido es orientativo y no constituye asesoramiento legal, fiscal ni profesional.</p></div>
<nav class="toc"><h2>Índice</h2><ol>{indice}</ol></nav>
{cuerpo}</body></html>"""


def main():
    ruta = os.environ.get("CHROMIUM_PATH") or ("/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None)
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=ruta) if ruta else p.chromium.launch()
        pag = nav.new_page()
        html = libro_html()
        (SALIDA / "ebook.html").write_text(html, encoding="utf-8")
        pag.set_content(html, wait_until="networkidle")
        pag.pdf(path=str(SALIDA / "ebook-ia-para-tu-negocio.pdf"), format="A5", print_background=True,
                display_header_footer=True, header_template="<span></span>",
                footer_template='<div style="width:100%;font:7px sans-serif;color:#999;text-align:center"><span class="pageNumber"></span></div>')
        pag = nav.new_page(viewport={"width": 800, "height": 1200}, device_scale_factor=2)
        pag.set_content(f'<!doctype html><html><head><meta charset="utf-8">{FUENTES}<style>{PORTADA_CSS}body{{margin:0;width:800px;height:1200px}}.cover{{font-size:21px}}</style></head><body>{portada_html()}</body></html>', wait_until="networkidle")
        pag.screenshot(path=str(SALIDA / "portada.png"))
        nav.close()
    print("Listo:", *sorted(x.name for x in SALIDA.iterdir()))


if __name__ == "__main__":
    main()
