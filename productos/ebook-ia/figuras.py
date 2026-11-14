"""Infografías SVG del ebook. Cada función devuelve un <svg> listo para incrustar."""

V, C, D, M, L = "#A855F7", "#22D3EE", "#1B1F3B", "#5B6390", "#F4EEFF"
F = "font-family:'Exo 2',sans-serif"


def _svg(w, h, body, titulo):
    return (f'<figure class="fig"><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{titulo}" style="{F}">{body}</svg><figcaption>{titulo}</figcaption></figure>')


def _t(x, y, s, size=11, w=600, fill=D, anchor="middle"):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{s}</text>'


def _box(x, y, w, h, fill=L, stroke=V, r=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def _arrow(x1, y1, x2, y2, col=C):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="2.5" marker-end="url(#a)"/>')


DEFS = f'<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{C}"/></marker></defs>'


def mapa():
    etapas = [("1–4", "Bases", "Qué es la IA, herramientas, cómo pedir"),
              ("5–8", "Crear", "Prompts, redes, imagen y vídeo"),
              ("9–12", "Automatizar y vender", "Atención, automatizaciones, agentes, ventas"),
              ("13–17", "Aplicar", "Tu sector, legal, métricas y plan")]
    b = DEFS
    for i, (n, t, d) in enumerate(etapas):
        y = 10 + i * 62
        b += _box(10, y, 380, 50, fill="#fff" if i % 2 else L)
        b += f'<circle cx="42" cy="{y+25}" r="20" fill="{V if i%2==0 else C}"/>' + _t(42, y + 29, n, 10, 800, "#fff")
        b += _t(75, y + 22, t, 13, 800, D, "start") + _t(75, y + 39, d, 10, 500, M, "start")
        if i < 3:
            b += _arrow(42, y + 47, 42, y + 60)
    return _svg(400, 258, b, "El camino del libro: de las bases a tu plan")


def tipos():
    items = [("✍", "Texto", "Escribir, resumir,\nanalizar"), ("🎨", "Imagen", "Diseños, fotos,\nbanners"),
             ("🎬", "Vídeo y voz", "Subtítulos, clips,\nlocuciones"), ("⚙", "Automatización", "Conectar apps,\ntareas solas")]
    b = ""
    for i, (ic, t, d) in enumerate(items):
        x = 8 + i * 98
        b += _box(x, 10, 90, 120, fill=L if i % 2 == 0 else "#E9FBFF", stroke=V if i % 2 == 0 else C)
        b += _t(x + 45, 48, ic, 26, 400) + _t(x + 45, 76, t, 11.5, 800)
        for j, line in enumerate(d.split("\n")):
            b += _t(x + 45, 96 + j * 13, line, 9.5, 500, M)
    return _svg(400, 140, b, "Los cuatro tipos de herramientas de IA")


def crea():
    piezas = [("C", "Contexto", "Quién eres y para quién"), ("R", "Rol", "Qué papel hace la IA"),
              ("E", "Encargo", "Qué quieres, con detalle"), ("A", "Ajustes", "Tono, límites, ejemplos")]
    b = DEFS
    for i, (l, t, d) in enumerate(piezas):
        x = 6 + i * 98
        col = V if i % 2 == 0 else C
        b += f'<rect x="{x}" y="10" width="88" height="130" rx="12" fill="{D}"/>'
        b += _t(x + 44, 62, l, 40, 900, col) + _t(x + 44, 92, t, 12, 800, "#fff")
        words = d.split()
        mid = (len(words) + 1) // 2
        b += _t(x + 44, 112, " ".join(words[:mid]), 9, 500, "#C9CEF0") + _t(x + 44, 124, " ".join(words[mid:]), 9, 500, "#C9CEF0")
    b += _t(200, 168, "Contexto + Rol + Encargo + Ajustes = un resultado que suena a ti", 11, 700, V)
    return _svg(400, 180, b, "La fórmula C.R.E.A. para pedir a la IA")


def cadena():
    pasos = ["Preguntas", "Cliente ideal", "Mensaje", "Página web", "Posts y email"]
    b = DEFS
    for i, p in enumerate(pasos):
        x = 4 + i * 80
        b += _box(x, 20, 70, 50, fill=L if i % 2 == 0 else "#E9FBFF", stroke=V if i % 2 == 0 else C)
        b += _t(x + 35, 42, f"Paso {i+1}", 9, 600, M) + _t(x + 35, 58, p, 9.5, 800)
        if i < 4:
            b += _arrow(x + 71, 45, x + 80, 45)
    b += _t(200, 95, "Cada paso usa el resultado del anterior", 11, 700, V)
    return _svg(400, 105, b, "Una cadena de prompts para lanzar un servicio")


def pilares():
    ps = [("Educar", "Consejos, tutoriales", V), ("Confianza", "Equipo, casos, procesos", C),
          ("Comunidad", "Preguntas, encuestas", V), ("Vender", "Ofertas, servicios", C)]
    b = f'<polygon points="200,8 392,52 8,52" fill="{D}"/>' + _t(200, 42, "TU MARCA", 13, 900, "#fff")
    for i, (t, d, col) in enumerate(ps):
        x = 14 + i * 95
        b += f'<rect x="{x}" y="60" width="78" height="110" rx="6" fill="{col}" opacity=".9"/>'
        b += _t(x + 39, 100, t, 12, 800, "#fff")
        for j, w in enumerate(d.split(", ")):
            b += _t(x + 39, 122 + j * 14, w, 9, 600, "#fff")
    b += f'<rect x="8" y="176" width="384" height="14" rx="4" fill="{D}"/>' + _t(200, 187, "1 hora a la semana de constancia", 9, 700, "#fff")
    return _svg(400, 196, b, "Los 4 pilares de tu contenido")


def reciclar():
    b = DEFS + f'<circle cx="200" cy="100" r="44" fill="{D}"/>' + _t(200, 96, "1 vídeo", 13, 800, "#fff") + _t(200, 112, "de 3 minutos", 9, 500, "#C9CEF0")
    sal = [("Artículo de blog", 70, 30), ("Carrusel", 330, 30), ("3 clips cortos", 60, 170), ("3 tuits", 340, 170), ("Email", 200, 190)]
    for t, x, y in sal:
        b += _arrow(200 + (x - 200) * .38, 100 + (y - 100) * .38, 200 + (x - 200) * .78, 100 + (y - 100) * .78)
        b += _box(x - 55, y - 14, 110, 28, fill=L) + _t(x, y + 4, t, 10.5, 700)
    return _svg(400, 210, b, "Graba una vez, publica cinco")


def niveles():
    ns = [("Nivel 3", "Asistente de IA 24/7", "Responde, filtra y te avisa", V, 140),
          ("Nivel 2", "FAQ y reservas online", "Elimina la mitad de mensajes", C, 240),
          ("Nivel 1", "WhatsApp Business", "Bienvenida, ausencia, atajos", D, 340)]
    b = ""
    for i, (n, t, d, col, w) in enumerate(ns):
        y = 10 + i * 52
        x = 200 - w / 2
        b += f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="8" fill="{col}"/>'
        b += _t(200, y + 20, f"{n} · {t}", 11, 800, "#fff") + _t(200, y + 36, d, 9, 500, "#fff")
    b += _t(200, 178, "Empieza por abajo: cada nivel se apoya en el anterior", 10, 700, V)
    return _svg(400, 186, b, "Los tres niveles de la atención al cliente")


def flujo():
    b = DEFS
    nodos = [("⚡", "Disparador", "Llega un formulario"), ("🗂", "Guardar", "Fila en la hoja"),
             ("🤖", "IA", "Redacta la respuesta"), ("✉", "Enviar", "Email al cliente"), ("🔔", "Avisar", "Mensaje para ti")]
    for i, (ic, t, d) in enumerate(nodos):
        x = 4 + i * 80
        b += _box(x, 14, 70, 92, fill=D if i == 0 else L, stroke=C if i == 0 else V)
        fill = "#fff" if i == 0 else D
        b += _t(x + 35, 44, ic, 20, 400) + _t(x + 35, 66, t, 10.5, 800, fill)
        ws = d.split()
        b += _t(x + 35, 82, " ".join(ws[:2]), 8.5, 500, "#C9CEF0" if i == 0 else M) + _t(x + 35, 94, " ".join(ws[2:]), 8.5, 500, "#C9CEF0" if i == 0 else M)
        if i < 4:
            b += _arrow(x + 71, 60, x + 80, 60)
    return _svg(400, 116, b, "Anatomía de una automatización: la receta 1")


def agente():
    b = DEFS + f'<circle cx="200" cy="105" r="50" fill="{D}"/>' + _t(200, 100, "AGENTE", 13, 900, "#fff") + _t(200, 117, "razona y decide", 9, 500, "#C9CEF0")
    pz = [("Instrucciones", "rol, objetivo, límites", 70, 35), ("Herramientas", "email, agenda, redes", 330, 35),
          ("Memoria", "lo que ya sabe", 70, 175), ("Objetivo", "lo que debe lograr", 330, 175)]
    for t, d, x, y in pz:
        b += f'<line x1="200" y1="105" x2="{x}" y2="{y}" stroke="{V}" stroke-width="2" stroke-dasharray="4 3"/>'
        b += _box(x - 62, y - 22, 124, 44, fill=L) + _t(x, y - 3, t, 11, 800) + _t(x, y + 12, d, 9, 500, M)
    return _svg(400, 210, b, "Las piezas de un agente de IA")


def embudo():
    capas = [("Te descubren", 360, V), ("Piden información", 300, C), ("Reciben propuesta", 240, V), ("Deciden", 180, C), ("Repiten y recomiendan", 140, D)]
    b = ""
    for i, (t, w, col) in enumerate(capas):
        y = 8 + i * 36
        b += f'<rect x="{200-w/2}" y="{y}" width="{w}" height="30" rx="6" fill="{col}"/>' + _t(200, y + 19, t, 10.5, 800, "#fff")
    b += _t(394, 112, "← aquí se pierden", 9, 700, V, "end") + _t(394, 124, "más ventas", 9, 700, V, "end")
    return _svg(400, 192, b, "El embudo de ventas de un negocio pequeño")


def formula():
    b = _box(10, 10, 380, 70, fill=D, stroke=C)
    b += _t(200, 38, "Horas ahorradas × valor de tu hora", 14, 800, "#fff")
    b += _t(200, 62, "− coste de las herramientas = ahorro mensual", 12, 600, C)
    b += _box(10, 92, 380, 40, fill=L) + _t(200, 117, "Ejemplo: 26 h × 25 € − 40 € = 610 € al mes", 12, 800, V)
    return _svg(400, 140, b, "La fórmula del ahorro")


def plan():
    semanas = [("Semana 1", "Cimientos", "Cuenta, ficha, WhatsApp"), ("Semana 2", "Contenido", "Pilares, Canva, reels"),
               ("Semana 3", "Ventas", "Propuestas, seguimiento"), ("Semana 4", "Automatizar", "Recetas y métricas")]
    b = DEFS + f'<line x1="20" y1="40" x2="380" y2="40" stroke="{D}" stroke-width="3"/>'
    for i, (s, t, d) in enumerate(semanas):
        x = 50 + i * 100
        col = V if i % 2 == 0 else C
        b += f'<circle cx="{x}" cy="40" r="14" fill="{col}"/>' + _t(x, 45, str(i + 1), 12, 900, "#fff")
        b += _t(x, 76, s, 9, 600, M) + _t(x, 92, t, 12, 800) + _t(x, 108, d.split(", ")[0] + ",", 9, 500, M) + _t(x, 120, ", ".join(d.split(", ")[1:]), 9, 500, M)
    b += _t(200, 18, "Día 1 → Día 30", 10, 800, V)
    return _svg(400, 130, b, "Tu plan de 30 días en cuatro semanas")


TODAS = {f.__name__: f for f in [mapa, tipos, crea, cadena, pilares, reciclar, niveles, flujo, agente, embudo, formula, plan]}
