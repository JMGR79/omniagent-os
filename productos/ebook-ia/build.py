#!/usr/bin/env python3
"""Genera el ebook (PDF) y la portada (PNG) a partir de contenido/ebook.md.

Requisitos: pip install markdown playwright  (y un Chromium para Playwright)
Uso:        python3 productos/ebook-ia/build.py
Salida:     productos/ebook-ia/build/ebook-ia-para-tu-negocio.pdf
            productos/ebook-ia/build/portada.png  (1600x2400, para la tienda)
            productos/ebook-ia/build/portada-mockup.png (1200x900, para la web)
"""
import base64, pathlib, re, markdown
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent
SALIDA = RAIZ / "build"
SALIDA.mkdir(exist_ok=True)

TITULO = "La IA que trabaja por ti"
SUBTITULO = "Guía práctica para pymes y autónomos: ahorra 10 horas a la semana en 30 días"
AUTOR = "Estrateg IA Digital 3.0"
EDICION = "Primera edición · noviembre de 2026"

robot = base64.b64encode((RAIZ / "robot.jpg").read_bytes()).decode()
FUENTES = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Exo+2:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap">'

PORTADA_CSS = """
.cover{width:100%;height:100%;position:relative;overflow:hidden;background:#070A18;color:#EAF0FF;font-family:'Exo 2',sans-serif}
.cover .img{position:absolute;inset:0;background:url(data:image/jpeg;base64,__ROBOT__) 50% 40%/cover;opacity:.75}
.cover .fade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(7,10,24,.92) 0%,rgba(7,10,24,.35) 38%,rgba(7,10,24,.35) 55%,rgba(7,10,24,.97) 82%)}
.cover .grid{position:absolute;inset:0;background-image:linear-gradient(rgba(168,85,247,.12) 1px,transparent 1px),linear-gradient(90deg,rgba(168,85,247,.12) 1px,transparent 1px);background-size:6% 4%}
.cover .txt{position:absolute;inset:7% 8%;display:flex;flex-direction:column;justify-content:space-between}
.cover .tag{font:700 .9em 'Orbitron';letter-spacing:.25em;color:#22D3EE;text-transform:uppercase}
.cover h1{font:900 3.05em/1.02 'Orbitron';text-transform:uppercase;margin:.3em 0 0;text-shadow:0 0 .5em rgba(168,85,247,.6)}
.cover h1 b{background:linear-gradient(90deg,#A855F7,#22D3EE);-webkit-background-clip:text;color:transparent}
.cover .sub{font-size:1.45em;font-weight:600;line-height:1.3;max-width:20em;color:#D5DBF2}
.cover .badge{display:inline-block;margin-top:1em;padding:.4em .9em;border:2px solid #22D3EE;border-radius:.5em;font:700 .95em 'Orbitron';color:#22D3EE;letter-spacing:.08em}
.cover .autor{font:700 1em 'Orbitron';letter-spacing:.18em;text-transform:uppercase;border-top:2px solid #A855F7;padding-top:.8em;box-shadow:0 -6px 12px -10px #A855F7}
""".replace("__ROBOT__", robot)

def portada_html():
    return f"""<div class="cover"><div class="img"></div><div class="fade"></div><div class="grid"></div>
<div class="txt"><div><div class="tag">Ebook · Guía práctica</div><h1>La <b>IA</b> que trabaja por ti</h1></div>
<div><div class="sub">{SUBTITULO}</div><div class="badge">+30 PROMPTS · 6 AUTOMATIZACIONES · PLAN DE 30 DÍAS</div></div>
<div class="autor">{AUTOR}</div></div></div>"""

def libro_html():
    md = (RAIZ / "contenido" / "ebook.md").read_text(encoding="utf-8")
    cuerpo = markdown.markdown(md, extensions=["tables", "attr_list", "sane_lists"])
    cuerpo = cuerpo.replace("[ ]", "☐")
    # índice a partir de los h1
    indice = "".join(
        f'<li><a href="#{i}">{t}</a></li>'
        for i, t in re.findall(r'<h1 id="([^"]+)">(.*?)</h1>', cuerpo)
    )
    css = PORTADA_CSS + """
@page{size:A5;margin:16mm 14mm 18mm}
@page:first{margin:0}
body{font:10.5pt/1.55 'Exo 2',sans-serif;color:#1B1F3B;margin:0}
.cover{width:148mm;height:210mm;font-size:9.5pt;page-break-after:always}
.legal{page-break-after:always;font-size:8.5pt;color:#555;display:flex;flex-direction:column;justify-content:flex-end;height:170mm}
.toc{page-break-after:always}.toc h2{font:900 16pt 'Orbitron';color:#7C3AED;text-transform:uppercase}
.toc ol{list-style:none;padding:0}.toc li{padding:.35em 0;border-bottom:1px dotted #C9C3E6}.toc a{color:#1B1F3B;text-decoration:none}
h1{font:900 17pt/1.15 'Orbitron';color:#7C3AED;text-transform:uppercase;page-break-before:always;margin:0 0 .8em;padding-bottom:.4em;border-bottom:3px solid #22D3EE}
h2{font:800 13pt 'Exo 2';color:#0E7490;margin:1.4em 0 .4em}
p,li{orphans:3;widows:3}
blockquote{margin:1em 0;padding:.7em 1em;background:#F4EEFF;border-left:4px solid #A855F7;border-radius:4px;page-break-inside:avoid}
blockquote p{margin:.3em 0}
table{width:100%;border-collapse:collapse;font-size:9pt;margin:1em 0;page-break-inside:avoid}
th{background:#1B1F3B;color:#fff;text-align:left;padding:.4em}td{padding:.4em;border-bottom:1px solid #DDD}
tr:nth-child(even) td{background:#F7F7FC}
strong{color:#111}
ul li::marker{color:#A855F7}
.cover h1{page-break-before:auto;border:0;padding:0;color:#EAF0FF;font-size:3.05em;margin:.3em 0 0}
"""
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">{FUENTES}<style>{css}</style></head><body>
{portada_html()}
<div class="legal"><p><b>{TITULO}</b><br>{SUBTITULO}</p><p>{EDICION}<br>© 2026 {AUTOR}. Todos los derechos reservados.</p>
<p>Esta copia es para uso personal del comprador. No está permitida su reventa ni su distribución.</p>
<p>Los nombres de herramientas y marcas citados pertenecen a sus propietarios y se mencionan solo con fines informativos. El contenido es orientativo y no constituye asesoramiento legal, fiscal ni profesional.</p></div>
<nav class="toc"><h2>Índice</h2><ol>{indice}</ol></nav>
{cuerpo}</body></html>"""

def main():
    with sync_playwright() as p:
        import os
        ruta = os.environ.get("CHROMIUM_PATH") or ("/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None)
        nav = p.chromium.launch(executable_path=ruta) if ruta else p.chromium.launch()
        pag = nav.new_page()
        pag.set_content(libro_html(), wait_until="networkidle")
        pag.pdf(path=str(SALIDA / "ebook-ia-para-tu-negocio.pdf"), format="A5", print_background=True,
                display_header_footer=True, header_template="<span></span>",
                footer_template='<div style="width:100%;font:8px sans-serif;color:#999;text-align:center"><span class="pageNumber"></span></div>')
        # portada sola en alta resolución
        pag = nav.new_page(viewport={"width": 800, "height": 1200}, device_scale_factor=2)
        pag.set_content(f'<!doctype html><html><head><meta charset="utf-8">{FUENTES}<style>{PORTADA_CSS}body{{margin:0;width:800px;height:1200px}}.cover{{font-size:21px}}</style></head><body>{portada_html()}</body></html>', wait_until="networkidle")
        pag.screenshot(path=str(SALIDA / "portada.png"))
        nav.close()
    print("Listo:", *sorted(x.name for x in SALIDA.iterdir()))

if __name__ == "__main__":
    main()
