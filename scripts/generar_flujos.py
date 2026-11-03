#!/usr/bin/env python3
"""Genera los flujos de n8n de OmniAgent OS en n8n/workflows/*.json.

Uso:  python3 scripts/generar_flujos.py
Los IDs son fijos para que los flujos puedan llamarse entre sí y para que la
importación sea idempotente (el arranque solo importa los que aún no existen).
"""
import json
import pathlib
import uuid

SALIDA = pathlib.Path(__file__).resolve().parent.parent / "n8n" / "workflows"
PG = {"postgres": {"id": "omniPostgres0001", "name": "Postgres OmniAgent"}}
SMTP = {"smtp": {"id": "omniGmailSmtp001", "name": "Gmail SMTP"}}
IMAP = {"imap": {"id": "omniGmailImap001", "name": "Gmail IMAP"}}
TG = {"telegramApi": {"id": "omniTelegram0001", "name": "Telegram OmniAgent"}}

ID = {
    "SYS00": "omniSYS00errores",
    "SYS01": "omniSYS01reintnt",
    "SYS20": "omniSYS20control",
    "AGT00": "omniAGT00agentes",
    "CNT01": "omniCNT01directr",
    "PUB01": "omniPUB01publica",
    "TEL01": "omniTEL01telegrm",
    "MSG01": "omniMSG01emailld",
    "RPT01": "omniRPT01resumen",
    "SYS21": "omniSYS21herrams",
    "PUB02": "omniPUB02linkdin",
    "PUB03": "omniPUB03xtwittr",
    "WA01": "omniWA01entrante",
    "WA02": "omniWA02enviarms",
    "GEN01": "omniGEN01imagen0",
    "GEN02": "omniGEN02video00",
    "GEN03": "omniGEN03webs000",
    "WEB01": "omniWEB01servir0",
    "VID01": "omniVID01fabrica",
    "NEG01": "omniNEG01negocio",
    "PUB04": "omniPUB04youtube",
    "MCP01": "omniMCP01servidr",
}


def nodo(nombre, tipo, version, params, pos, **extra):
    n = {
        "parameters": params,
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "omniagent/" + nombre + tipo)),
        "name": nombre,
        "type": tipo,
        "typeVersion": version,
        "position": list(pos),
    }
    n.update(extra)
    return n


def code(nombre, js, pos, modo="runOnceForAllItems", **extra):
    p = {"jsCode": js.strip() + "\n"}
    if modo != "runOnceForAllItems":
        p["mode"] = modo
    return nodo(nombre, "n8n-nodes-base.code", 2, p, pos, **extra)


def pg(nombre, sql, params_expr, pos, **extra):
    opts = {"queryReplacement": params_expr} if params_expr else {}
    return nodo(nombre, "n8n-nodes-base.postgres", 2.8,
                {"operation": "executeQuery", "query": sql.strip(), "options": opts},
                pos, credentials=PG, **extra)


def http(nombre, metodo, url, cuerpo_expr, pos, cabeceras=None, **extra):
    p = {"method": metodo, "url": url, "options": {"timeout": 60000}}
    if cabeceras:
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": [{"name": k, "value": v} for k, v in cabeceras]}
    if cuerpo_expr:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = cuerpo_expr
    return nodo(nombre, "n8n-nodes-base.httpRequest", 4.2, p, pos, **extra)


def telegram_http(nombre, pos, **extra):
    """Envía $json.metodo con $json.cuerpo a la API de Telegram."""
    return http(nombre, "POST",
                "={{ 'https://api.telegram.org/bot' + $env.TELEGRAM_BOT_TOKEN + '/' + ($json.metodo || 'sendMessage') }}",
                "={{ JSON.stringify($json.cuerpo) }}", pos,
                onError="continueRegularOutput", **extra)


def llamar_agente(nombre, pos):
    return nodo(nombre, "n8n-nodes-base.executeWorkflow", 1.1, {
        "source": "database",
        "workflowId": {"__rl": True, "value": ID["AGT00"], "mode": "id"},
        "mode": "each",
        "options": {"waitForSubWorkflow": True},
    }, pos)


def cron(nombre, expresion, pos):
    return nodo(nombre, "n8n-nodes-base.scheduleTrigger", 1.2,
                {"rule": {"interval": [{"field": "cronExpression", "expression": expresion}]}}, pos)


def enlazar(*pares):
    """pares: (origen, destino) o (origen, destino, salida)."""
    c = {}
    for par in pares:
        o, d = par[0], par[1]
        salida = par[2] if len(par) > 2 else 0
        ramas = c.setdefault(o, {"main": []})["main"]
        while len(ramas) <= salida:
            ramas.append([])
        ramas[salida].append({"node": d, "type": "main", "index": 0})
    return c


def con_ejecutar_ahora(nodos, conexiones, primero):
    """Añade un disparador manual/subflujo que arranca en el mismo nodo que el programado."""
    nodos.append(nodo("Ejecutar ahora", "n8n-nodes-base.executeWorkflowTrigger", 1.1,
                      {"inputSource": "passthrough"}, (0, 200)))
    conexiones["Ejecutar ahora"] = {"main": [[{"node": primero, "type": "main", "index": 0}]]}


def flujo(clave, nombre, nodos, conexiones, con_errores=True):
    ajustes = {"executionOrder": "v1", "timezone": "Europe/Madrid", "saveManualExecutions": True}
    if con_errores:
        ajustes["errorWorkflow"] = ID["SYS00"]
    return {
        "id": ID[clave],
        "name": nombre,
        "nodes": nodos,
        "connections": conexiones,
        "settings": ajustes,
        "active": False,
        "pinData": {},
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True},
    }


# Fragmento JS reutilizado: extrae JSON de la respuesta de un agente
JSON_DE_TEXTO = r"""
function jsonDeTexto(t) {
  const s = String(t || '').replace(/```(?:json)?/gi, '').trim();
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) throw new Error('El agente no devolvió JSON: ' + s.slice(0, 200));
  return JSON.parse(s.slice(a, b + 1));
}
"""

AVISO_TG = r"""
// Aviso genérico para el dueño: después sale por Telegram y por WhatsApp (los que estén configurados).
// teclado: [[{ text, callback_data }]] → botones [{ id, titulo }]
function avisoTelegram(texto, teclado) {
  const botones = teclado ? teclado.flat().map((b) => ({ id: b.callback_data, titulo: b.text })) : null;
  return [{ json: { texto: String(texto).slice(0, 4000), botones } }];
}
"""


def con_avisos(nodos, conexiones, origen, x, y):
    """Tras `origen` (que emite {texto, botones}) añade el envío por Telegram y por WhatsApp."""
    nodos.append(code("A Telegram", r"""
if (!$env.TELEGRAM_BOT_TOKEN || !$env.TELEGRAM_CHAT_ID) return [];
return $input.all().map((it) => {
  const j = it.json;
  const texto = String(j.texto);
  const teclado = j.botones?.length ? { inline_keyboard: [j.botones.map((b) => ({ text: b.titulo, callback_data: b.id }))] } : null;
  // Si el aviso trae un vídeo o una imagen, se envía como archivo para verlo dentro de Telegram
  // (Telegram lo descarga de la URL pública; el texto va como pie, con el enlace por si acaso).
  if (j.media_url && ['video', 'imagen'].includes(j.media_tipo)) {
    const campo = j.media_tipo === 'video' ? 'video' : 'photo';
    const cuerpo = { chat_id: $env.TELEGRAM_CHAT_ID, [campo]: j.media_url, caption: texto.slice(0, 1024) };
    if (campo === 'video') cuerpo.supports_streaming = true;
    if (teclado) cuerpo.reply_markup = teclado;
    return { json: { metodo: campo === 'video' ? 'sendVideo' : 'sendPhoto', cuerpo } };
  }
  const cuerpo = { chat_id: $env.TELEGRAM_CHAT_ID, text: texto.slice(0, 4000), disable_web_page_preview: true };
  if (teclado) cuerpo.reply_markup = teclado;
  return { json: { metodo: 'sendMessage', cuerpo } };
});
""", (x, y - 90)))
    nodos.append(telegram_http("Telegram", (x + 220, y - 90)))
    # Si Telegram no pudo descargar el vídeo o la imagen, se manda el aviso como texto con el enlace
    nodos.append(code("Respaldo de texto", r"""
const enviados = $('A Telegram').all();
return $input.all().flatMap((it, i) => {
  const orig = enviados[i]?.json;
  if (!orig || orig.metodo === 'sendMessage' || it.json.ok === true) return [];
  const c = orig.cuerpo;
  const enlace = c.video || c.photo || '';
  const texto = String(c.caption || '') + (enlace && !String(c.caption || '').includes(enlace) ? '\n' + enlace : '');
  const cuerpo = { chat_id: c.chat_id, text: texto.slice(0, 4000), disable_web_page_preview: true };
  if (c.reply_markup) cuerpo.reply_markup = c.reply_markup;
  return [{ json: { metodo: 'sendMessage', cuerpo } }];
});
""", (x + 440, y - 90)))
    nodos.append(telegram_http("Telegram (texto)", (x + 660, y - 90)))
    nodos.append(nodo("WhatsApp", "n8n-nodes-base.executeWorkflow", 1.1, {
        "source": "database", "workflowId": {"__rl": True, "value": ID["WA02"], "mode": "id"},
        "mode": "each", "options": {"waitForSubWorkflow": True}}, (x, y + 90), onError="continueRegularOutput"))
    for a, b in ((origen, "A Telegram"), (origen, "WhatsApp"), ("A Telegram", "Telegram"),
                 ("Telegram", "Respaldo de texto"), ("Respaldo de texto", "Telegram (texto)")):
        ramas = conexiones.setdefault(a, {"main": [[]]})["main"]
        ramas[0].append({"node": b, "type": "main", "index": 0})

# ═════════════════════════════════════════════════════════════════════
# AGT-00 · Ejecutar agente (motor común de los 15 agentes)
# ═════════════════════════════════════════════════════════════════════
def agt00():
    n = [
        nodo("Desde otro flujo", "n8n-nodes-base.executeWorkflowTrigger", 1.1,
             {"inputSource": "passthrough"}, (0, 0)),
        nodo("Webhook agente", "n8n-nodes-base.webhook", 2,
             {"httpMethod": "POST", "path": "omniagent-agente", "responseMode": "lastNode", "options": {}},
             (0, 200), webhookId="6f1d1c1e-0a00-4c00-9a00-000000000a00"),
        code("Normalizar", r"""
// Acepta llamadas de otros flujos (datos directos) o del webhook (con token).
return $input.all().map((it) => {
  const j = it.json;
  let d = j;
  if (j.headers && j.body !== undefined) {
    const auth = String(j.headers.authorization || '').replace(/^Bearer\s+/i, '');
    if (!$env.OMNIAGENT_CONTROL_TOKEN || auth !== $env.OMNIAGENT_CONTROL_TOKEN) throw new Error('No autorizado');
    d = j.body || {};
  }
  const agente_id = parseInt(d.agente_id, 10);
  if (!(agente_id >= 0 && agente_id <= 16)) throw new Error('agente_id no válido: ' + d.agente_id);
  const input = String(d.input || '').slice(0, 30000);
  if (!input.trim()) throw new Error('El agente necesita un texto de entrada');
  const max_tokens = Math.min(parseInt(d.max_tokens || 2000, 10) || 2000, 8000);
  return { json: { agente_id, input, max_tokens, origen: String(d.origen || 'manual') } };
});
""", (220, 100)),
        pg("Prompt activo", """
SELECT p.sistema, p.version, p.modelo,
       (SELECT coalesce(sum(coste_eur), 0) FROM ejecuciones_agente WHERE creado_en::date = current_date) AS gastado_hoy
FROM prompts p WHERE p.agente_id = $1::int AND p.estado = 'activa' ORDER BY p.version DESC LIMIT 1
""", "={{ [$json.agente_id] }}", (440, 100)),
        code("Preparar llamada", r"""
const n = $('Normalizar').first().json;
const p = $input.first().json;
if (!p.sistema) throw new Error('El agente ' + n.agente_id + ' no tiene un prompt activo');
const tope = parseFloat($env.PRESUPUESTO_TOKENS_DIARIO_EUR || '5');
if (parseFloat(p.gastado_hoy) >= tope) throw new Error('Presupuesto diario de IA agotado (' + tope + ' EUR). Se reanuda mañana.');
// Proveedor: anthropic (Claude), openai (ChatGPT) o gemini (Google). Se elige con PROVEEDOR_IA.
const prov = String($env.PROVEEDOR_IA || 'anthropic').toLowerCase();
const porDefecto = { anthropic: p.modelo || 'claude-sonnet-5-5', openai: 'gpt-5-mini', gemini: 'gemini-3.5-flash' };
if (!porDefecto[prov]) throw new Error('PROVEEDOR_IA no válido: ' + prov + ' (usa anthropic, openai o gemini)');
const modelo = $env.MODELO_IA || porDefecto[prov];
const sistema = p.sistema + '\nFecha y hora actuales (Madrid): ' + new Date().toLocaleString('es-ES', { timeZone: 'Europe/Madrid' }) + '.';
let url, cabeceras, cuerpo;
if (prov === 'anthropic') {
  if (!$env.ANTHROPIC_API_KEY) throw new Error('Falta ANTHROPIC_API_KEY');
  url = ($env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com') + '/v1/messages';
  cabeceras = { 'x-api-key': $env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' };
  cuerpo = { model: modelo, max_tokens: n.max_tokens, system: sistema, messages: [{ role: 'user', content: n.input }] };
} else if (prov === 'openai') {
  if (!$env.OPENAI_API_KEY) throw new Error('Falta OPENAI_API_KEY');
  url = ($env.OPENAI_BASE_URL || 'https://api.openai.com') + '/v1/chat/completions';
  cabeceras = { Authorization: 'Bearer ' + $env.OPENAI_API_KEY };
  cuerpo = { model: modelo, max_completion_tokens: n.max_tokens, messages: [{ role: 'system', content: sistema }, { role: 'user', content: n.input }] };
} else {
  if (!$env.GEMINI_API_KEY) throw new Error('Falta GEMINI_API_KEY');
  url = ($env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com') + '/v1beta/models/' + encodeURIComponent(modelo) + ':generateContent';
  cabeceras = { 'x-goog-api-key': $env.GEMINI_API_KEY };
  cuerpo = { systemInstruction: { parts: [{ text: sistema }] }, contents: [{ role: 'user', parts: [{ text: n.input }] }],
    generationConfig: { maxOutputTokens: n.max_tokens } };
  // Los modelos Gemini 3+ «piensan» antes de responder y ese razonamiento gasta el límite de tokens: lo dejamos al mínimo.
  if (/^gemini-([3-9]|\d\d)/.test(modelo)) cuerpo.generationConfig.thinkingConfig = { thinkingLevel: $env.GEMINI_RAZONAMIENTO || 'minimal' };
}
return [{ json: { proveedor: prov, modelo, version: p.version, url, cabeceras, cuerpo } }];
""", (660, 100)),
        nodo("Modelo de IA", "n8n-nodes-base.httpRequest", 4.2, {
            "method": "POST", "url": "={{ $json.url }}",
            "sendHeaders": True, "specifyHeaders": "json", "jsonHeaders": "={{ JSON.stringify($json.cabeceras) }}",
            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.cuerpo) }}",
            "options": {"timeout": 120000}}, (880, 100),
            retryOnFail=True, maxTries=3, waitBetweenTries=5000),
        code("Calcular coste", r"""
const r = $input.first().json;
const prep = $('Preparar llamada').first().json;
const n = $('Normalizar').first().json;
let texto = '', ent = 0, sal = 0, cortado = false;
if (prep.proveedor === 'anthropic') {
  texto = (r.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
  ent = r.usage?.input_tokens || 0; sal = r.usage?.output_tokens || 0; cortado = r.stop_reason === 'max_tokens';
} else if (prep.proveedor === 'openai') {
  texto = r.choices?.[0]?.message?.content || '';
  ent = r.usage?.prompt_tokens || 0; sal = r.usage?.completion_tokens || 0; cortado = r.choices?.[0]?.finish_reason === 'length';
} else {
  texto = (r.candidates?.[0]?.content?.parts || []).map((x) => x.text || '').join('');
  ent = r.usageMetadata?.promptTokenCount || 0; sal = r.usageMetadata?.candidatesTokenCount || 0; cortado = r.candidates?.[0]?.finishReason === 'MAX_TOKENS';
}
texto = String(texto).trim();
if (!texto) throw new Error('El modelo (' + prep.proveedor + ') no devolvió texto: ' + JSON.stringify(r).slice(0, 300));
// Precios orientativos en EUR por millón de tokens; ajústalos con variables de entorno.
const pe = parseFloat($env.PRECIO_ENTRADA_EUR_MTOK || '3'), ps = parseFloat($env.PRECIO_SALIDA_EUR_MTOK || '15');
const coste = Math.round(((ent * pe + sal * ps) / 1e6) * 10000) / 10000;
return [{ json: { respuesta: texto, agente_id: n.agente_id, version: prep.version, modelo: prep.proveedor + ':' + prep.modelo,
  tokens_entrada: ent, tokens_salida: sal, coste_eur: coste, origen: n.origen, cortado } }];
""", (1100, 100)),
        pg("Registrar ejecución", """
INSERT INTO ejecuciones_agente (agente_id, prompt_version, modelo, tokens_entrada, tokens_salida, coste_eur, origen)
VALUES ($1::int, $2::int, $3, $4::int, $5::int, $6::numeric, $7) RETURNING id
""", "={{ [$json.agente_id, $json.version, $json.modelo, $json.tokens_entrada, $json.tokens_salida, $json.coste_eur, $json.origen] }}",
           (1320, 100)),
        code("Respuesta", r"""
const c = $('Calcular coste').first().json;
return [{ json: { respuesta: c.respuesta, agente_id: c.agente_id, coste_eur: c.coste_eur, cortado: c.cortado } }];
""", (1540, 100)),
    ]
    c = enlazar(("Desde otro flujo", "Normalizar"), ("Webhook agente", "Normalizar"),
                ("Normalizar", "Prompt activo"), ("Prompt activo", "Preparar llamada"),
                ("Preparar llamada", "Modelo de IA"), ("Modelo de IA", "Calcular coste"),
                ("Calcular coste", "Registrar ejecución"), ("Registrar ejecución", "Respuesta"))
    return flujo("AGT00", "AGT-00 Ejecutar agente", n, c)


# ═════════════════════════════════════════════════════════════════════
# CNT-01 · Director de contenido (genera, evalúa y encola piezas)
# ═════════════════════════════════════════════════════════════════════
def cnt01():
    n = [
        cron("Ciclo 08 · 13 · 19 h", "0 8,13,19 * * *", (0, 0)),
        pg("Contexto", """
SELECT
  (SELECT coalesce(json_agg(json_build_object('id', id, 'texto', texto)), '[]'::json)
     FROM (SELECT id, texto FROM ordenes WHERE estado = 'pendiente' ORDER BY creado_en LIMIT 10) o) AS ordenes,
  (SELECT coalesce(json_agg(json_build_object('id', x.id, 'canal', x.canal, 'texto', x.brief, 'cambio', x.comentario)), '[]'::json)
     FROM (SELECT p.id, p.canal, p.brief,
             (SELECT a.comentario FROM aprobaciones a WHERE a.pieza_id = p.id ORDER BY a.respondido_en DESC NULLS LAST LIMIT 1) AS comentario
           FROM piezas p WHERE p.estado = 'generando' ORDER BY p.actualizado_en LIMIT 5) x) AS rehacer,
  (SELECT coalesce(json_agg(tema), '[]'::json) FROM (SELECT tema FROM piezas WHERE tema IS NOT NULL ORDER BY creado_en DESC LIMIT 30) t) AS temas_recientes,
  (SELECT count(*) FROM piezas WHERE estado IN ('en_cola', 'pendiente_aprobacion'))::int AS en_cola,
  coalesce((SELECT valor = 'si' FROM ajustes WHERE clave = 'pausa'), false) AS en_pausa
""", None, (220, 0)),
        code("Encargo al Director", r"""
const c = $input.first().json;
if (c.en_pausa) return [];  // piloto automático en pausa (WhatsApp «pausar», app o IA)
const canales = String($env.CANALES_ACTIVOS || 'facebook,instagram,linkedin,x,tiktok,youtube')
  .split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
const porCiclo = parseInt($env.PIEZAS_POR_CICLO || '3', 10);
const maxCola = parseInt($env.PIEZAS_MAX_COLA || '20', 10);
const ordenes = c.ordenes || [], rehacer = c.rehacer || [];
const nuevas = c.en_cola >= maxCola ? 0 : porCiclo;
if (!canales.length || (nuevas === 0 && !ordenes.length && !rehacer.length)) return [];
const reglas = {
  facebook: 'Facebook: 300-800 caracteres, cercano, 1-3 emojis como mucho, pregunta final para comentar.',
  instagram: 'Instagram: post con pie de foto de 600-1500 caracteres, 5-10 hashtags en el campo hashtags y un texto_imagen de máximo 6 palabras; o formato "reel" con un guion de 20-30 s con [TEXTO EN PANTALLA] y [VOZ].',
  linkedin: 'LinkedIn: 700-1300 caracteres, tono profesional, primera línea gancho, sin hashtags en exceso (máximo 3).',
  x: 'X: un tuit de máximo 260 caracteres (máximo 2 hashtags) o, si el tema lo merece, formato "hilo" de 4 a 7 tuits separados por una línea con --- (cada tuit de máximo 270 caracteres).',
  telegram: 'Telegram: 300-900 caracteres, directo.',
  tiktok: 'TikTok: guion de vídeo vertical de 30-45 s con [TEXTO EN PANTALLA] y [VOZ] por escenas.',
  youtube: 'YouTube Shorts: guion de 30-50 s con [TEXTO EN PANTALLA] y [VOZ], más un título de máximo 70 caracteres en el campo tema.',
};
const input = [
  'Negocio: EstrategIA Digital 3.0 — consultoría y formación en inteligencia artificial, automatización y marketing digital para pymes y profesionales.',
  'Canales activos: ' + canales.join(', ') + '.',
  'Reglas por canal:\n' + canales.map((k) => '- ' + (reglas[k] || k)).join('\n'),
  nuevas ? 'Crea ' + nuevas + ' piezas NUEVAS repartidas entre los canales activos (varía los temas: casos prácticos, errores comunes, herramientas, tutoriales breves, novedades de IA para negocio, llamadas a reservar una consultoría).' : 'No crees piezas nuevas: la cola está llena.',
  ordenes.length ? 'Órdenes del dueño que debes cumplir (prioridad máxima):\n' + ordenes.map((o) => '- [' + o.id + '] ' + o.texto).join('\n') : '',
  rehacer.length ? 'Piezas que el dueño pidió cambiar (devuélvelas con el mismo id):\n' + rehacer.map((r) => '- id ' + r.id + ' (' + r.canal + '). Cambio pedido: ' + (r.cambio || 'mejorar') + '\nTexto actual: ' + r.texto).join('\n') : '',
  'Temas recientes que NO debes repetir: ' + JSON.stringify(c.temas_recientes || []),
  'Normas: español de España; no inventes cifras, estudios, clientes ni testimonios; nada de promesas de resultados garantizados; una sola llamada a la acción por pieza.',
  'Responde SOLO con este JSON: {"piezas":[{"id":"(solo si rehaces una pieza)","canal":"uno de los canales activos","formato":"post|carrusel|hilo|reel|short","tema":"título breve","texto":"texto final listo para publicar","hashtags":"#uno #dos","texto_imagen":"máx 6 palabras","publicar_en_horas":0,"orden_id":"(id de la orden si responde a una)"}],"respuesta_ordenes":"qué has hecho con las órdenes, en una frase"}',
  'Usa publicar_en_horas entre 0 y 20 para repartir las publicaciones a lo largo del día.',
].filter(Boolean).join('\n\n');
return [{ json: { agente_id: 0, input, max_tokens: 8000, origen: 'CNT-01', _ordenes: ordenes.map((o) => o.id), _canales: canales } }];
""", (440, 0)),
        llamar_agente("Director", (660, 0)),
        code("Preparar evaluación", JSON_DE_TEXTO + r"""
const enc = $('Encargo al Director').first().json;
const plan = jsonDeTexto($input.first().json.respuesta);
const piezas = (plan.piezas || []).filter((p) => p && enc._canales.includes(String(p.canal || '').toLowerCase()) && String(p.texto || '').trim());
if (!piezas.length && !enc._ordenes.length) throw new Error('El Director no devolvió piezas válidas');
const input = 'Evalúa cada pieza. Responde SOLO JSON: {"evaluaciones":[{"i":0,"puntuacion":0,"sensible":false,"motivo":""}]}\n\n' +
  piezas.map((p, i) => '### Pieza ' + i + ' (' + p.canal + ')\n' + p.texto + (p.hashtags ? '\n' + p.hashtags : '')).join('\n\n');
return [{ json: { agente_id: 8, input: piezas.length ? input : 'Sin piezas. Responde {"evaluaciones":[]}', max_tokens: 2000, origen: 'CNT-01',
  _piezas: piezas, _respuesta_ordenes: plan.respuesta_ordenes || '' } }];
""", (880, 0)),
        llamar_agente("Evaluador", (1100, 0)),
        code("Decidir estado", JSON_DE_TEXTO + r"""
const prev = $('Preparar evaluación').first().json;
let ev = [];
try { ev = jsonDeTexto($input.first().json.respuesta).evaluaciones || []; } catch (e) { ev = []; }
const auto = String($env.MODO_AUTOMATICO || 'true') === 'true';
const nota = parseFloat($env.PUNTUACION_MINIMA || '6');
const plantilla = $env.IMAGEN_PLANTILLA_URL || 'https://placehold.co/1080x1080/0B3D91/FFFFFF/jpeg?font=montserrat&text={texto}';
const ahora = Date.now();
return prev._piezas.map((p, i) => {
  const e = ev.find((x) => Number(x.i) === i) || { puntuacion: 0, sensible: true, motivo: 'Sin evaluación: revisar a mano' };
  const canal = String(p.canal).toLowerCase();
  const video = canal === 'tiktok' || canal === 'youtube' || (canal === 'instagram' && /reel|short|video/i.test(String(p.formato || '')));
  let estado;
  if (Number(e.puntuacion) < nota) estado = 'descartada';
  else if (video) estado = 'requiere_video';
  else if (e.sensible || !auto) estado = 'pendiente_aprobacion';
  else estado = 'en_cola';
  const horas = Math.max(0, Math.min(24, Number(p.publicar_en_horas) || 0));
  const media = canal === 'instagram' && !video
    ? plantilla.replace('{texto}', encodeURIComponent(String(p.texto_imagen || p.tema || 'EstrategIA Digital 3.0').slice(0, 60))) : '';
  const id = /^[0-9a-f-]{36}$/i.test(String(p.id || '')) ? p.id : '';
  const orden = /^[0-9a-f-]{36}$/i.test(String(p.orden_id || '')) ? p.orden_id : '';
  return { json: { params: [id, canal, String(p.texto).trim(), String(p.hashtags || ''), media, !!e.sensible, estado,
    new Date(ahora + horas * 3600e3).toISOString(), String(p.formato || 'post'), String(p.tema || '').slice(0, 200),
    estado === 'descartada' ? 'Evaluador ' + e.puntuacion + '/10: ' + (e.motivo || '') : '', orden, String(p.texto_imagen || '').slice(0, 60)] } };
});
""", (1320, 0)),
        pg("Guardar piezas", """
WITH upd AS (
  UPDATE piezas SET brief = $3, hashtags = $4, media_url = nullif($5, ''), sensible = $6::boolean, estado = $7,
         programado_para = $8::timestamptz, formato = $9, tema = $10, error = nullif($11, ''), texto_imagen = nullif($13, ''), actualizado_en = now()
  WHERE $1 <> '' AND id = nullif($1, '')::uuid RETURNING id),
ins AS (
  INSERT INTO piezas (canal, brief, hashtags, media_url, sensible, estado, programado_para, formato, tema, error, orden_id, texto_imagen)
  SELECT $2, $3, $4, nullif($5, ''), $6::boolean, $7, $8::timestamptz, $9, $10, nullif($11, ''), nullif($12, '')::uuid, nullif($13, '')
  WHERE NOT EXISTS (SELECT 1 FROM upd) RETURNING id)
SELECT id, $7 AS estado, $2 AS canal, left($3, 700) AS texto, $10 AS tema, $13 AS texto_imagen FROM upd
UNION ALL SELECT id, $7, $2, left($3, 700), $10, $13 FROM ins
""", "={{ $json.params }}", (1540, 0)),
        code("Cerrar órdenes", r"""
const enc = $('Encargo al Director').first().json;
const ev = $('Preparar evaluación').first().json;
if (!enc._ordenes.length) return [];
return [{ json: { ids: enc._ordenes.join(','), resultado: ev._respuesta_ordenes || 'Procesada por el Director' } }];
""", (1760, -120)),
        pg("Marcar órdenes hechas", """
UPDATE ordenes SET estado = 'hecha', resultado = $2, actualizado_en = now()
WHERE id = ANY(string_to_array($1, ',')::uuid[]) RETURNING id
""", "={{ [$json.ids, $json.resultado] }}", (1980, -120)),
        code("Avisos", AVISO_TG + r"""
const filas = $input.all().map((i) => i.json).filter((f) => f.id);
const out = [];
for (const f of filas) {
  if (f.estado === 'pendiente_aprobacion') {
    out.push(...avisoTelegram('🟡 Pieza para aprobar · ' + f.canal + '\n' + (f.tema ? '«' + f.tema + '»\n\n' : '') + f.texto,
      [[{ text: '✅ Aprobar', callback_data: 'a:' + f.id }, { text: '🗑 Descartar', callback_data: 'd:' + f.id }]]));
  } else if (f.estado === 'requiere_video') {
    out.push(...avisoTelegram('🎬 Guion de vídeo listo para grabar · ' + f.canal + '\n' + (f.tema ? '«' + f.tema + '»\n\n' : '') + f.texto));
  }
}
return out;
""", (1760, 120)),
        code("¿Imágenes?", r"""
// Con PROVEEDOR_IMAGEN configurado, cada post de Instagram (y de Facebook si IMAGEN_EN_TODAS=true) lleva una imagen generada.
if (!$env.PROVEEDOR_IMAGEN) return [];
const todas = String($env.IMAGEN_EN_TODAS || 'false') === 'true';
return $input.all().map((i) => i.json).filter((f) => f.id && !['descartada', 'requiere_video'].includes(f.estado)
    && (f.canal === 'instagram' || (todas && f.canal === 'facebook')))
  .map((f) => ({ json: { pieza_id: f.id, tipo: 'post', formato: 'cuadrado', tema: f.tema || f.texto.slice(0, 300), texto_imagen: f.texto_imagen || '' } }));
""", (1760, 300)),
        sub("Generar imágenes", "GEN01", (1980, 300)),
    ]
    c = enlazar(("Ciclo 08 · 13 · 19 h", "Contexto"), ("Contexto", "Encargo al Director"),
                ("Encargo al Director", "Director"), ("Director", "Preparar evaluación"),
                ("Preparar evaluación", "Evaluador"), ("Evaluador", "Decidir estado"),
                ("Decidir estado", "Guardar piezas"), ("Preparar evaluación", "Cerrar órdenes"),
                ("Guardar piezas", "Avisos"), ("Cerrar órdenes", "Marcar órdenes hechas"),
                ("Guardar piezas", "¿Imágenes?"), ("¿Imágenes?", "Generar imágenes"),
                )
    con_avisos(n, c, "Avisos", 1980, 120)
    con_ejecutar_ahora(n, c, "Contexto")
    return flujo("CNT01", "CNT-01 Director de contenido", n, c)


# ═════════════════════════════════════════════════════════════════════
# PUB-01 · Publicador (Facebook, Instagram, LinkedIn, X, Telegram)
# ═════════════════════════════════════════════════════════════════════
def pub01():
    graph = "($env.META_GRAPH_URL || 'https://graph.facebook.com') + '/' + ($env.META_API_VERSION || 'v21.0') + '/'"
    canales = ["facebook", "instagram", "linkedin", "x", "telegram", "youtube"]
    n = [
        nodo("Cada 15 min", "n8n-nodes-base.scheduleTrigger", 1.2,
             {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}}, (0, 300)),
        pg("Reservar piezas", """
UPDATE piezas SET estado = 'publicando', intentos = intentos + 1, actualizado_en = now()
WHERE id IN (SELECT id FROM piezas WHERE estado = 'en_cola' AND programado_para <= now()
             AND NOT EXISTS (SELECT 1 FROM ajustes WHERE clave = 'pausa' AND valor = 'si')
             ORDER BY programado_para LIMIT 5 FOR UPDATE SKIP LOCKED)
RETURNING id, canal, formato, brief, hashtags, media_url, intentos, tema,
  (SELECT m.tipo FROM medios m WHERE m.pieza_id = piezas.id ORDER BY m.creado_en DESC LIMIT 1) AS media_tipo
""", None, (220, 300)),
        code("Preparar texto", r"""
const out = [];
for (const it of $input.all()) {
  const p = it.json;
  if (!p.id) continue;
  let texto = String(p.brief || '').trim();
  if (p.hashtags && !texto.includes(String(p.hashtags).trim())) texto += '\n\n' + String(p.hashtags).trim();
  const corta = (t) => { if (t.length <= 280) return t; const c = t.slice(0, 277); return c.slice(0, Math.max(c.lastIndexOf(' '), 200)) + '…'; };
  let tweets = [];
  if (p.canal === 'x') {
    const partes = /hilo/i.test(p.formato || '') ? String(p.brief || '').split(/\n\s*-{3,}\s*\n/).map((x) => x.trim()).filter(Boolean) : [String(p.brief || '').trim()];
    if (p.hashtags && partes.length) partes[partes.length - 1] += ' ' + String(p.hashtags).trim();
    tweets = partes.map(corta);
    texto = tweets[0];
  }
  const media_tipo = p.media_tipo || (p.media_url ? 'imagen' : '');
  out.push({ json: { id: p.id, canal: p.canal, texto, tweets, media_url: p.media_url || '', media_tipo, tema: p.tema || '' }, pairedItem: it.pairedItem });
}
return out;
""", (440, 300)),
        nodo("Canal", "n8n-nodes-base.switch", 3.2, {
            "mode": "expression", "numberOutputs": 7,
            "output": "={{ (i => i < 0 ? 6 : i)(" + json.dumps(canales) + ".indexOf($json.canal)) }}",
        }, (660, 300)),
        http("Facebook", "POST", "={{ " + graph + " + $env.META_PAGE_ID + ($json.media_tipo === 'video' ? '/videos' : $json.media_url ? '/photos' : '/feed') }}",
             "={{ JSON.stringify($json.media_tipo === 'video' ? { file_url: $json.media_url, description: $json.texto, access_token: $env.META_PAGE_TOKEN } : $json.media_url ? { url: $json.media_url, message: $json.texto, access_token: $env.META_PAGE_TOKEN } : { message: $json.texto, access_token: $env.META_PAGE_TOKEN }) }}",
             (900, 0), onError="continueRegularOutput"),
        http("Instagram · contenedor", "POST", "={{ " + graph + " + $env.IG_USER_ID + '/media' }}",
             "={{ JSON.stringify($json.media_tipo === 'video' ? { media_type: 'REELS', video_url: $json.media_url, caption: $json.texto, share_to_feed: true, access_token: $env.META_PAGE_TOKEN } : { image_url: $json.media_url, caption: $json.texto, access_token: $env.META_PAGE_TOKEN }) }}",
             (900, 150), onError="continueRegularOutput"),
        http("Instagram · publicar", "POST", "={{ " + graph + " + $env.IG_USER_ID + '/media_publish' }}",
             "={{ JSON.stringify({ creation_id: $json.id || 'sin-contenedor', access_token: $env.META_PAGE_TOKEN }) }}",
             (1340, 150), onError="continueRegularOutput", retryOnFail=True, maxTries=5, waitBetweenTries=5000),
        nodo("¿Es un reel?", "n8n-nodes-base.if", 2.2, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [{"id": "c0ffee00-0000-4000-8000-000000000001", "leftValue": "={{ $('Preparar texto').item.json.media_tipo }}", "rightValue": "video",
                            "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}, "options": {}}, (1120, 150)),
        nodo("Procesar reel (90 s)", "n8n-nodes-base.wait", 1.1, {"amount": 90, "unit": "seconds"}, (1230, 60),
             webhookId="6f1d1c1e-0a00-4c00-9a00-000000001500"),
        sub("YouTube", "PUB04", (900, 900)),
        nodo("LinkedIn", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["PUB02"], "mode": "id"},
            "mode": "each", "options": {"waitForSubWorkflow": True}}, (900, 300), onError="continueRegularOutput"),
        nodo("X", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["PUB03"], "mode": "id"},
            "mode": "each", "options": {"waitForSubWorkflow": True}}, (900, 450), onError="continueRegularOutput"),
        http("Canal de Telegram", "POST", "={{ 'https://api.telegram.org/bot' + $env.TELEGRAM_BOT_TOKEN + '/sendMessage' }}",
             "={{ JSON.stringify({ chat_id: $env.TELEGRAM_CANAL_ID, text: $json.texto }) }}",
             (900, 600), onError="continueRegularOutput"),
        code("Sin publicador", r"""
return $input.all().map((it) => ({ json: { error: { message: 'El canal ' + it.json.canal + ' no tiene publicación automática (requiere vídeo o subida manual)' } }, pairedItem: it.pairedItem }));
""", (900, 750)),
        code("Resultado", r"""
const p = $('Preparar texto').item.json;
const j = $json;
let error = '';
if (j.error) error = typeof j.error === 'string' ? j.error : (j.error.message || JSON.stringify(j.error));
const idExt = String(j.id || j.post_id || j.data?.id || j.urn || j.result?.message_id || '');
if (!error && !idExt) error = 'Respuesta sin identificador de publicación: ' + JSON.stringify(j).slice(0, 300);
const subflujo = { linkedin: ['LinkedIn', 'PUB-02'], x: ['X', 'PUB-03'], youtube: ['YouTube', 'PUB-04'] }[p.canal];
if (subflujo && /not active|no está activ|has issues|credential/i.test(error))
  error = 'Cuenta de ' + subflujo[0] + ' sin conectar: abre ' + subflujo[1] + ' en n8n, conecta la cuenta y pulsa Publish. (' + error.slice(0, 120) + ')';
let url = '';
if (!error) {
  if (p.canal === 'facebook') url = 'https://www.facebook.com/' + idExt;
  else if (p.canal === 'x') url = 'https://x.com/i/web/status/' + idExt;
  else if (p.canal === 'linkedin') url = 'https://www.linkedin.com/feed/update/' + idExt;
  else if (p.canal === 'youtube') url = 'https://youtube.com/shorts/' + idExt;
}
return { json: { params: [p.id, String(error).slice(0, 1000), idExt, url] } };
""", (1560, 300), modo="runOnceForEachItem"),
        pg("Guardar resultado", """
WITH p AS (
  UPDATE piezas SET
    estado = CASE WHEN $2 = '' THEN 'publicada' WHEN $2 LIKE 'El canal % no tiene publicación automática%' THEN 'requiere_video'
                  WHEN intentos >= 3 THEN 'error' ELSE 'en_cola' END,
    error = nullif($2, ''),
    programado_para = CASE WHEN $2 = '' THEN programado_para ELSE now() + interval '30 minutes' END,
    actualizado_en = now()
  WHERE id = $1::uuid RETURNING id, canal, estado),
pub AS (INSERT INTO publicaciones (pieza_id, canal, id_externo, url)
        SELECT id, canal, nullif($3, ''), nullif($4, '') FROM p WHERE $2 = '' RETURNING id),
inc AS (INSERT INTO incidentes (workflow, workflow_id, nodo, error, intentos)
        SELECT 'PUB-01 Publicador', 'omniPUB01publica', canal, $2, 3 FROM p WHERE estado = 'error' RETURNING id)
SELECT (SELECT count(*) FROM pub)::int AS publicadas, (SELECT count(*) FROM inc)::int AS incidentes
""", "={{ $json.params }}", (1780, 300)),
    ]
    c = enlazar(("Cada 15 min", "Reservar piezas"), ("Reservar piezas", "Preparar texto"),
                ("Preparar texto", "Canal"),
                ("Canal", "Facebook", 0), ("Canal", "Instagram · contenedor", 1), ("Canal", "LinkedIn", 2),
                ("Canal", "X", 3), ("Canal", "Canal de Telegram", 4), ("Canal", "Sin publicador", 6),
                ("Instagram · contenedor", "¿Es un reel?"), ("¿Es un reel?", "Procesar reel (90 s)", 0),
                ("¿Es un reel?", "Instagram · publicar", 1), ("Procesar reel (90 s)", "Instagram · publicar"),
                ("Canal", "YouTube", 5), ("YouTube", "Resultado"),
                ("Facebook", "Resultado"), ("Instagram · publicar", "Resultado"), ("LinkedIn", "Resultado"),
                ("X", "Resultado"), ("Canal de Telegram", "Resultado"), ("Sin publicador", "Resultado"),
                ("Resultado", "Guardar resultado"))
    con_ejecutar_ahora(n, c, "Reservar piezas")
    return flujo("PUB01", "PUB-01 Publicador de redes", n, c)


# ═════════════════════════════════════════════════════════════════════
# TEL-01 · Telegram: aprobar con botones y dar órdenes por chat
# ═════════════════════════════════════════════════════════════════════
def tel01():
    n = [
        nodo("Telegram", "n8n-nodes-base.telegramTrigger", 1.2,
             {"updates": ["message", "callback_query"], "additionalFields": {}}, (0, 0),
             credentials=TG, webhookId="6f1d1c1e-0a00-4c00-9a00-000000000c00"),
        code("Interpretar", r"""
const u = $input.first().json;
const dueno = String($env.TELEGRAM_CHAT_ID || '');
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
if (u.callback_query) {
  const c = u.callback_query;
  if (!dueno || String(c.from?.id) !== dueno) return [];
  const [t, id] = String(c.data || '').split(':');
  const decision = t === 'a' ? 'aprobar' : t === 'd' ? 'descartar' : '';
  if (!decision || !uuid.test(id || '')) return [];
  return [{ json: { tipo: 'decision', callback_id: c.id, chat_id: c.message?.chat?.id,
    sql: "WITH a AS (INSERT INTO aprobaciones (pieza_id, tipo_traspaso, enviado_en, respondido_en, decision, comentario, usuario) VALUES ($1::uuid, 'contenido', now(), now(), $2, '', 'telegram') RETURNING pieza_id) UPDATE piezas SET estado = CASE $2 WHEN 'aprobar' THEN 'en_cola' ELSE 'descartada' END, programado_para = least(programado_para, now() + interval '1 hour'), actualizado_en = now() WHERE id = (SELECT pieza_id FROM a) AND estado = 'pendiente_aprobacion' RETURNING id, estado",
    params: [id, decision], decision } }];
}
const m = u.message;
if (!m || !m.text) return [];
const texto = m.text.trim();
if (texto === '/id' || texto === '/start') {
  return [{ json: { tipo: 'info', chat_id: m.chat.id, sql: 'SELECT 1 AS ok', params: [],
    aviso: 'Tu chat_id es ' + m.chat.id + (dueno ? '' : '. Ponlo en TELEGRAM_CHAT_ID para que OmniAgent te reconozca como dueño.') } }];
}
if (!dueno || String(m.chat.id) !== dueno) return [];
return [{ json: { tipo: 'orden', chat_id: m.chat.id,
  sql: "INSERT INTO ordenes (texto, origen) VALUES ($1, 'telegram') RETURNING id", params: [texto.slice(0, 2000)] } }];
""", (220, 0)),
        pg("Aplicar", "{{ $json.sql }}", "={{ $json.params }}", (440, 0), alwaysOutputData=True),
        code("Contestar", r"""
const i = $('Interpretar').first().json;
const fila = $input.first().json || {};
if (i.tipo === 'decision') {
  const txt = !fila.id ? 'Esta pieza ya estaba decidida' : i.decision === 'aprobar' ? '✅ Aprobada: se publicará en la próxima hora' : '🗑 Descartada';
  return [{ json: { metodo: 'answerCallbackQuery', cuerpo: { callback_query_id: i.callback_id, text: txt } } },
          { json: { metodo: 'sendMessage', cuerpo: { chat_id: i.chat_id, text: txt } } }];
}
if (i.tipo === 'info') return [{ json: { metodo: 'sendMessage', cuerpo: { chat_id: i.chat_id, text: i.aviso } } }];
return [{ json: { metodo: 'sendMessage', cuerpo: { chat_id: i.chat_id,
  text: '📝 Orden registrada. El Director la procesará en el próximo ciclo (8:00, 13:00 o 19:00) y te avisaré si hay algo que aprobar.' } } }];
""", (660, 0)),
        telegram_http("Responder", (880, 0)),
    ]
    n[2]["parameters"]["query"] = "={{ $json.sql }}"
    c = enlazar(("Telegram", "Interpretar"), ("Interpretar", "Aplicar"), ("Aplicar", "Contestar"),
                ("Contestar", "Responder"))
    return flujo("TEL01", "TEL-01 Telegram del dueño", n, c)


# ═════════════════════════════════════════════════════════════════════
# MSG-01 · Responder emails de leads (etiqueta de Gmail OmniAgent-Leads)
# ═════════════════════════════════════════════════════════════════════
def msg01():
    n = [
        nodo("Email nuevo", "n8n-nodes-base.emailReadImap", 2.1, {
            "mailbox": "OmniAgent-Leads", "postProcessAction": "read", "format": "simple",
            "options": {"customEmailConfig": "[\"UNSEEN\"]"},
        }, (0, 0), credentials=IMAP),
        code("Filtrar", r"""
const propio = String($env.GMAIL_USUARIO || $env.EMAIL_DUENO || '').toLowerCase();
const out = [];
for (const it of $input.all()) {
  const e = it.json;
  const deTxt = String(e.from || '');
  const m = deTxt.match(/<([^>]+)>/);
  const email = (m ? m[1] : deTxt).trim().toLowerCase();
  const nombre = m ? deTxt.replace(/<[^>]+>/, '').replace(/"/g, '').trim() : '';
  if (!email.includes('@') || email === propio) continue;
  if (/(no-?reply|mailer-daemon|postmaster|notifications?@|newsletter|bounce)/i.test(email)) continue;
  const cuerpo = String(e.textPlain || e.text || e.textHtml || '').replace(/<[^>]+>/g, ' ').slice(0, 6000);
  out.push({ json: { email, nombre, asunto: String(e.subject || '(sin asunto)'), cuerpo, message_id: e.messageId || e['message-id'] || '' } });
}
return out;
""", (220, 0)),
        pg("Contacto", """
INSERT INTO contactos (email, nombre, origen, ultimo_contacto) VALUES ($1, nullif($2, ''), 'email', now())
ON CONFLICT (email) DO UPDATE SET ultimo_contacto = now(), nombre = coalesce(contactos.nombre, excluded.nombre)
RETURNING id, score, (SELECT coalesce(string_agg('Cliente: ' || left(m.entrante, 300) || E'\\nNosotros: ' || left(coalesce(m.respuesta, ''), 300), E'\\n---\\n'), '')
                      FROM (SELECT * FROM mensajes WHERE contacto_id = contactos.id ORDER BY creado_en DESC LIMIT 3) m) AS historial
""", "={{ [$json.email, $json.nombre] }}", (440, 0)),
        code("Encargo", r"""
return $input.all().map((it, i) => {
  const e = $('Filtrar').all()[i].json;
  const c = it.json;
  const input = 'Ha llegado este email a EstrategIA Digital 3.0.\nDe: ' + (e.nombre || e.email) + '\nAsunto: ' + e.asunto + '\n\n' + e.cuerpo +
    (c.historial ? '\n\nConversación anterior:\n' + c.historial : '') +
    '\n\nResponde SOLO JSON: {"respuesta":"email de respuesta en texto plano, firmado como Asistente de IA de EstrategIA Digital 3.0","requiere_humano":false,"motivo":"","score":0,"intencion":"info|compra|soporte|queja|spam|otro"}' +
    '\nPon requiere_humano=true si hay intención clara de compra, presupuesto, queja, tema legal, datos personales sensibles o si no sabes la respuesta. Si es spam, intencion=spam y respuesta vacía.';
  return { json: { agente_id: 3, input, max_tokens: 1500, origen: 'MSG-01' } };
});
""", (660, 0)),
        llamar_agente("Agente de conversación", (880, 0)),
        code("Decidir", JSON_DE_TEXTO + r"""
return $input.all().map((it, i) => {
  const e = $('Filtrar').all()[i].json;
  const c = $('Contacto').all()[i].json;
  let r;
  try { r = jsonDeTexto(it.json.respuesta); } catch (err) { r = { respuesta: '', requiere_humano: true, motivo: 'Respuesta del agente no válida', score: 0, intencion: 'otro' }; }
  const spam = r.intencion === 'spam';
  const auto = String($env.MODO_AUTOMATICO || 'true') === 'true';
  const humano = !spam && (!!r.requiere_humano || !auto || !String(r.respuesta || '').trim());
  const pie = '\n\n—\nEste mensaje lo ha escrito el asistente de IA de EstrategIA Digital 3.0. Si prefieres hablar con una persona, responde con la palabra «persona».';
  return { json: { enviar: !humano && !spam, humano, spam, email: e.email, asunto: /^re:/i.test(e.asunto) ? e.asunto : 'Re: ' + e.asunto,
    respuesta: String(r.respuesta || '').trim() + pie, motivo: r.motivo || '', score: Math.max(0, Math.min(100, Number(r.score) || 0)),
    intencion: r.intencion || 'otro', contacto_id: c.id, entrante: e.cuerpo.slice(0, 4000) } };
});
""", (1100, 0)),
        nodo("¿Responder solo?", "n8n-nodes-base.if", 2.2, {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{"id": "b1c2d3e4-0000-4000-8000-000000000001", "leftValue": "={{ $json.enviar }}",
                                "rightValue": True, "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                "combinator": "and"},
            "options": {},
        }, (1320, 0)),
        nodo("Enviar respuesta", "n8n-nodes-base.emailSend", 2.1, {
            "fromEmail": "={{ 'EstrategIA Digital 3.0 <' + ($env.GMAIL_USUARIO || $env.EMAIL_DUENO) + '>' }}",
            "toEmail": "={{ $json.email }}", "subject": "={{ $json.asunto }}",
            "emailFormat": "text", "text": "={{ $json.respuesta }}",
            "options": {"appendAttribution": False},
        }, (1540, -150), credentials=SMTP),
        pg("Registrar conversación", """
WITH m AS (INSERT INTO mensajes (canal, contacto_id, entrante, respuesta, estado)
           VALUES ('email', $1::uuid, $2, CASE WHEN $3 = 'respondido' THEN $4 END, $3) RETURNING id)
UPDATE contactos SET score = greatest(score, $5::int), estado = CASE WHEN $6 = 'compra' THEN 'caliente' WHEN $6 = 'spam' THEN 'spam' ELSE estado END
WHERE id = $1::uuid RETURNING id
""", "={{ [$json.contacto_id, $json.entrante, $json.spam ? 'ignorado' : ($json.humano ? 'pendiente_humano' : 'respondido'), $json.respuesta, $json.score, $json.intencion] }}",
           (1320, 150)),
        code("Avisar al dueño", AVISO_TG + r"""
const out = [];
for (const it of $('Decidir').all()) {
  const d = it.json;
  if (d.humano) out.push(...avisoTelegram('📩 Email que necesita a una persona (' + d.intencion + ', score ' + d.score + ')\nDe: ' + d.email + '\nMotivo: ' + d.motivo + '\n\n' + d.entrante.slice(0, 1500)));
  else if (d.score >= 70) out.push(...avisoTelegram('🔥 Lead caliente respondido (score ' + d.score + '): ' + d.email));
}
return out;
""", (1540, 150)),
    ]
    # El registro va por una rama y el envío por otra, para que ningún nodo se ejecute dos veces.
    c = enlazar(("Email nuevo", "Filtrar"), ("Filtrar", "Contacto"), ("Contacto", "Encargo"),
                ("Encargo", "Agente de conversación"), ("Agente de conversación", "Decidir"),
                ("Decidir", "¿Responder solo?"), ("¿Responder solo?", "Enviar respuesta", 0),
                ("Decidir", "Registrar conversación"), ("Registrar conversación", "Avisar al dueño"))
    con_avisos(n, c, "Avisar al dueño", 1760, 150)
    return flujo("MSG01", "MSG-01 Responder emails de leads", n, c)


# ═════════════════════════════════════════════════════════════════════
# RPT-01 · Resumen diario por email y Telegram
# ═════════════════════════════════════════════════════════════════════
def rpt01():
    n = [
        cron("Cada día 20:30", "30 20 * * *", (0, 0)),
        pg("Datos del día", """
SELECT
  (SELECT count(*) FROM publicaciones WHERE publicado_en::date = current_date)::int AS publicadas_hoy,
  (SELECT coalesce(string_agg(canal || ': ' || n, ', '), '—') FROM (SELECT canal, count(*) n FROM publicaciones WHERE publicado_en::date = current_date GROUP BY canal) c) AS por_canal,
  (SELECT count(*) FROM piezas WHERE estado = 'pendiente_aprobacion')::int AS pendientes,
  (SELECT count(*) FROM piezas WHERE estado = 'en_cola')::int AS en_cola,
  (SELECT coalesce(string_agg('· ' || canal || ' — ' || coalesce(tema, left(brief, 60)), E'\\n'), '') FROM (SELECT * FROM piezas WHERE estado = 'requiere_video' ORDER BY creado_en DESC LIMIT 5) v) AS videos,
  (SELECT count(*) FROM contactos WHERE fecha_alta::date = current_date)::int AS leads_hoy,
  (SELECT count(*) FROM mensajes WHERE creado_en::date = current_date AND estado = 'respondido')::int AS respondidos,
  (SELECT count(*) FROM mensajes WHERE estado = 'pendiente_humano' AND creado_en > now() - interval '3 days')::int AS para_ti,
  (SELECT round(coalesce(sum(coste_eur), 0), 2) FROM ejecuciones_agente WHERE creado_en::date = current_date) AS coste_ia,
  (SELECT count(*) FROM incidentes WHERE resuelto_en IS NULL AND NOT autorreparado)::int AS incidentes,
  (SELECT coalesce(string_agg('· ' || canal || ': ' || left(error, 120), E'\\n'), '') FROM (SELECT * FROM piezas WHERE estado = 'error' AND actualizado_en::date = current_date LIMIT 5) e) AS errores
""", None, (220, 0)),
        code("Redactar", r"""
const d = $input.first().json;
const fecha = new Date().toLocaleDateString('es-ES', { timeZone: 'Europe/Madrid', weekday: 'long', day: 'numeric', month: 'long' });
const lineas = [
  'Resumen de OmniAgent · EstrategIA Digital 3.0 · ' + fecha, '',
  '📣 Publicadas hoy: ' + d.publicadas_hoy + ' (' + d.por_canal + ')',
  '⏳ En cola: ' + d.en_cola + ' · Para aprobar: ' + d.pendientes,
  '👤 Leads nuevos: ' + d.leads_hoy + ' · Emails respondidos por la IA: ' + d.respondidos + ' · Esperan tu respuesta: ' + d.para_ti,
  '💶 Coste de IA hoy: ' + d.coste_ia + ' €',
  '🛠 Incidentes abiertos: ' + d.incidentes,
];
if (d.videos) lineas.push('', '🎬 Guiones de vídeo pendientes de grabar:', d.videos);
if (d.errores) lineas.push('', '⚠ Errores de publicación de hoy:', d.errores);
const texto = lineas.join('\n');
return [{ json: { tipo: 'email', texto } }, { json: { tipo: 'aviso', texto } }];
""", (440, 0)),
        nodo("¿Email?", "n8n-nodes-base.if", 2.2, {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{"id": "b1c2d3e4-0000-4000-8000-000000000002", "leftValue": "={{ $json.tipo }}",
                                "rightValue": "email", "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and"},
            "options": {},
        }, (660, 0)),
        nodo("Email al dueño", "n8n-nodes-base.emailSend", 2.1, {
            "fromEmail": "={{ 'OmniAgent <' + ($env.GMAIL_USUARIO || $env.EMAIL_DUENO) + '>' }}",
            "toEmail": "={{ $env.EMAIL_DUENO || $env.GMAIL_USUARIO }}",
            "subject": "={{ 'OmniAgent · resumen del ' + $now.setZone('Europe/Madrid').toFormat('dd/MM') }}",
            "emailFormat": "text", "text": "={{ $json.texto }}", "options": {"appendAttribution": False},
        }, (880, -100), credentials=SMTP, onError="continueRegularOutput"),
        code("Aviso", "return $input.all().map((it) => ({ json: { texto: it.json.texto, botones: null } }));", (880, 100)),
    ]
    c = enlazar(("Cada día 20:30", "Datos del día"), ("Datos del día", "Redactar"), ("Redactar", "¿Email?"),
                ("¿Email?", "Email al dueño", 0), ("¿Email?", "Aviso", 1))
    con_avisos(n, c, "Aviso", 1100, 100)
    con_ejecutar_ahora(n, c, "Datos del día")
    return flujo("RPT01", "RPT-01 Resumen diario", n, c)


# ═════════════════════════════════════════════════════════════════════
# SYS-00 · Debugger global (recibe los errores de todos los flujos)
# ═════════════════════════════════════════════════════════════════════
def sys00():
    n = [
        nodo("Error en un flujo", "n8n-nodes-base.errorTrigger", 1, {}, (0, 0)),
        code("Extraer", r"""
const e = $input.first().json;
const msg = String(e.execution?.error?.message || e.trigger?.error?.message || 'Error desconocido');
// Errores que no se arreglan reintentando: credenciales, permisos, presupuesto, cuota del proveedor, datos.
// Tampoco se reintenta una ejecución que ya era un reintento (evita la cascada de incidentes).
const esReintento = !!(e.execution?.retryOf);
const noReintentable = esReintento || /(No autorizado|credential|credencial|permission|permiso|Presupuesto|401|403|429|quota|cuota|rate.?limit|too many requests|exceeded|invalid|no válido)/i.test(msg);
return [{ json: { params: [e.workflow?.name || 'desconocido', String(e.workflow?.id || ''), String(e.execution?.id || ''),
  e.execution?.lastNodeExecuted || '', msg.slice(0, 2000), noReintentable ? 'no' : 'si'],
  aviso: '🛠 Error en ' + (e.workflow?.name || 'un flujo') + ' · nodo «' + (e.execution?.lastNodeExecuted || '?') + '»\n' + msg.slice(0, 800) +
    (noReintentable ? '\n\nNo se reintentará solo: revisa la configuración.' : '\n\nSe reintentará automáticamente.') } }];
""", (220, 0)),
        pg("Guardar incidente", """
INSERT INTO incidentes (workflow, workflow_id, ejecucion_id, nodo, error, proximo_reintento)
VALUES ($1, $2, nullif($3, ''), $4, $5, CASE WHEN $6 = 'si' THEN now() + interval '5 minutes' END) RETURNING id
""", "={{ $json.params }}", (440, 0), onError="continueRegularOutput"),
        code("Aviso", AVISO_TG + r"""
return avisoTelegram($('Extraer').first().json.aviso);
""", (660, 0)),
    ]
    c = enlazar(("Error en un flujo", "Extraer"), ("Extraer", "Guardar incidente"),
                ("Guardar incidente", "Aviso"))
    con_avisos(n, c, "Aviso", 880, 0)
    return flujo("SYS00", "SYS-00 Debugger global", n, c, con_errores=False)


# ═════════════════════════════════════════════════════════════════════
# SYS-01 · Autorreparación: reintenta ejecuciones fallidas
# ═════════════════════════════════════════════════════════════════════
def sys01():
    n = [
        nodo("Cada 10 min", "n8n-nodes-base.scheduleTrigger", 1.2,
             {"rule": {"interval": [{"field": "minutes", "minutesInterval": 10}]}}, (0, 0)),
        pg("Incidentes a reintentar", """
UPDATE incidentes SET intentos = intentos + 1, proximo_reintento = now() + (intentos + 1) * interval '30 minutes'
WHERE id IN (SELECT id FROM incidentes WHERE resuelto_en IS NULL AND NOT autorreparado AND ejecucion_id IS NOT NULL
             AND proximo_reintento <= now() AND intentos < 3 ORDER BY proximo_reintento LIMIT 5 FOR UPDATE SKIP LOCKED)
RETURNING id, ejecucion_id, workflow
""", None, (220, 0)),
        code("¿Hay API?", r"""
if (!$env.N8N_API_KEY) return [];
return $input.all().filter((i) => i.json.ejecucion_id).map((i) => ({ json: i.json, pairedItem: i.pairedItem }));
""", (440, 0)),
        http("Reintentar ejecución", "POST",
             "={{ ($env.N8N_API_URL || 'http://localhost:5678') + '/api/v1/executions/' + $json.ejecucion_id + '/retry' }}",
             "={{ JSON.stringify({ loadWorkflow: true }) }}", (660, 0),
             cabeceras=[("X-N8N-API-KEY", "={{ $env.N8N_API_KEY }}")], onError="continueRegularOutput"),
        code("Resultado", r"""
const inc = $('¿Hay API?').item.json;
const ok = !$json.error && ($json.status === 'success' || $json.finished === true);
return { json: { params: [inc.id, ok ? 'si' : 'no'] } };
""", (880, 0), modo="runOnceForEachItem"),
        pg("Marcar", """
UPDATE incidentes SET autorreparado = ($2 = 'si'), resuelto_en = CASE WHEN $2 = 'si' THEN now() END WHERE id = $1::uuid RETURNING id
""", "={{ $json.params }}", (1100, 0)),
    ]
    c = enlazar(("Cada 10 min", "Incidentes a reintentar"), ("Incidentes a reintentar", "¿Hay API?"),
                ("¿Hay API?", "Reintentar ejecución"), ("Reintentar ejecución", "Resultado"), ("Resultado", "Marcar"))
    con_ejecutar_ahora(n, c, "Incidentes a reintentar")
    return flujo("SYS01", "SYS-01 Autorreparación", n, c)


# ═════════════════════════════════════════════════════════════════════
# SYS-20 · API de control para la app OmniAgent Control (corregido)
# ═════════════════════════════════════════════════════════════════════
SYS20_VALIDAR = r"""
// Valida el token y traduce cada acción de la app a una consulta SQL o a una llamada HTTP.
// Solo se ejecutan consultas de esta lista blanca: la app nunca envía SQL.
const req = $input.first().json;
const auth = String(req.headers?.authorization || '').replace(/^Bearer\s+/i, '');
const esperado = $env.OMNIAGENT_CONTROL_TOKEN;
if (!esperado || auth !== esperado) return [{ json: { tipo: 'error', codigo: 401, r: { error: 'No autorizado' } } }];

const { accion, datos = {} } = req.body || {};
const API = ($env.N8N_API_URL || 'http://localhost:5678') + '/api/v1';
const uuid = (v) => (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(v || '')) ? String(v) : '00000000-0000-0000-0000-000000000000');
const SQL = {
  resumen: [`SELECT json_build_object(
      'leads_hoy', (SELECT count(*) FROM contactos WHERE fecha_alta::date = current_date),
      'leads_semana', (SELECT count(*) FROM contactos WHERE fecha_alta >= current_date - 7),
      'piezas_hoy', (SELECT count(*) FROM piezas WHERE creado_en::date = current_date),
      'publicadas_semana', (SELECT count(*) FROM publicaciones WHERE publicado_en >= now() - interval '7 days'),
      'coste_ia_hoy', (SELECT round(coalesce(sum(coste_eur), 0), 2) FROM ejecuciones_agente WHERE creado_en::date = current_date),
      'presupuesto_ia', $1::numeric,
      'ingresos_mes', (SELECT coalesce(sum(importe), 0) FROM pedidos WHERE estado = 'pagado' AND date_trunc('month', creado_en) = date_trunc('month', now())),
      'ingresos_var', (SELECT coalesce(round(100 * (sum(importe) FILTER (WHERE date_trunc('month', creado_en) = date_trunc('month', now()))
                          / nullif(sum(importe) FILTER (WHERE date_trunc('month', creado_en) = date_trunc('month', now() - interval '1 month')), 0) - 100)), 0)
                       FROM pedidos WHERE estado = 'pagado'),
      'cpl', (SELECT round(coalesce(sum(gasto) / nullif(sum(leads), 0), 0), 2) FROM ads_diario WHERE fecha >= current_date - 30),
      'aprobaciones', (SELECT count(*) FROM piezas WHERE estado = 'pendiente_aprobacion'),
      'incidentes', (SELECT count(*) FROM incidentes WHERE NOT autorreparado AND resuelto_en IS NULL),
      'en_pausa', coalesce((SELECT valor = 'si' FROM ajustes WHERE clave = 'pausa'), false)) AS kpis,
    (SELECT coalesce(json_agg(json_build_array(to_char(t AT TIME ZONE 'Europe/Madrid', 'HH24:MI'), txt, nivel) ORDER BY t DESC), '[]'::json) FROM (
       (SELECT publicado_en AS t, 'Publicado en ' || canal AS txt, 'ok' AS nivel FROM publicaciones ORDER BY publicado_en DESC LIMIT 5)
       UNION ALL (SELECT creado_en, workflow || ' · ' || coalesce(nodo, ''), CASE WHEN autorreparado THEN 'warn' ELSE 'info' END FROM incidentes ORDER BY creado_en DESC LIMIT 5)
       UNION ALL (SELECT fecha_alta, 'Nuevo lead · origen: ' || origen, 'info' FROM contactos ORDER BY fecha_alta DESC LIMIT 5)
       ORDER BY 1 DESC LIMIT 8) x) AS actividad`, [$env.PRESUPUESTO_TOKENS_DIARIO_EUR || 5], 'uno'],
  aprobaciones: [`SELECT id, canal, formato, sensible, to_char(creado_en AT TIME ZONE 'Europe/Madrid', 'DD/MM HH24:MI') AS creado,
      brief || CASE WHEN hashtags IS NOT NULL AND hashtags <> '' THEN E'\n\n' || hashtags ELSE '' END AS texto
    FROM piezas WHERE estado = 'pendiente_aprobacion' ORDER BY creado_en LIMIT 50`, [], 'lista'],
  decidir: [`WITH a AS (INSERT INTO aprobaciones (pieza_id, tipo_traspaso, enviado_en, respondido_en, decision, comentario, usuario)
      VALUES ($1::uuid, 'contenido', now(), now(), $2, $3, 'app') RETURNING pieza_id)
    UPDATE piezas SET estado = CASE $2 WHEN 'aprobar' THEN 'en_cola' WHEN 'descartar' THEN 'descartada' ELSE 'generando' END,
      programado_para = least(programado_para, now() + interval '1 hour'), actualizado_en = now()
    WHERE id = (SELECT pieza_id FROM a) RETURNING id`,
    [uuid(datos.id), ['aprobar', 'cambiar', 'descartar'].includes(datos.decision) ? datos.decision : 'cambiar', String(datos.comentario || '').slice(0, 1000)], 'ok'],
  agentes: [`SELECT p.agente_id AS id, p.agente AS nombre, 'v' || p.version AS version, round(coalesce(p.puntuacion_media, 0), 1) AS puntuacion,
      count(e.id)::int AS ejecuciones_7d, round(coalesce(sum(e.coste_eur), 0), 2) AS coste_7d, p.estado
    FROM prompts p LEFT JOIN ejecuciones_agente e ON e.agente_id = p.agente_id AND e.prompt_version = p.version AND e.creado_en >= now() - interval '7 days'
    WHERE p.estado IN ('activa', 'candidata') GROUP BY p.agente_id, p.agente, p.version, p.puntuacion_media, p.estado ORDER BY p.agente_id`, [], 'lista'],
  archivos: [`SELECT nombre_nuevo AS nombre, ruta, tipo, to_char(creado_en, 'DD/MM/YYYY') AS fecha FROM archivos
    WHERE NOT sensible AND ($1 = '' OR nombre_nuevo ILIKE '%' || $1 || '%' OR ruta ILIKE '%' || $1 || '%' OR resumen ILIKE '%' || $1 || '%')
    ORDER BY creado_en DESC LIMIT 30`, [String(datos.q || '').slice(0, 80)], 'lista'],
  incidentes: [`SELECT id, workflow, nodo, left(error, 200) AS error, autorreparado, intentos, to_char(creado_en AT TIME ZONE 'Europe/Madrid', 'DD/MM HH24:MI') AS cuando
    FROM incidentes ORDER BY creado_en DESC LIMIT 30`, [], 'lista'],
  incidente_reintentar: [`UPDATE incidentes SET proximo_reintento = now(), intentos = 0 WHERE id = $1::uuid RETURNING id`, [uuid(datos.id)], 'ok'],
  leads: [`SELECT 'Lead #' || left(id::text, 6) AS nombre, score, estado, origen, to_char(fecha_alta, 'DD/MM') AS fecha
    FROM contactos WHERE estado <> 'spam' ORDER BY fecha_alta DESC LIMIT 30`, [], 'lista'],
  piloto: [`INSERT INTO ajustes (clave, valor) VALUES ('pausa', $1) ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor, actualizado_en = now()
    RETURNING CASE WHEN valor = 'si' THEN '⏸ En pausa: no se crea ni se publica nada hasta que digas «reanudar».' ELSE '▶️ Reanudado: vuelven la creación y la publicación automáticas.' END AS respuesta`,
    [datos.pausa ? 'si' : 'no'], 'uno'],
  medios: [`SELECT tipo, url, descripcion, to_char(creado_en AT TIME ZONE 'Europe/Madrid', 'DD/MM HH24:MI') AS fecha FROM (
       SELECT tipo, $1 || '/webhook/medio?id=' || id AS url, coalesce(left(prompt, 140), '') AS descripcion, creado_en FROM medios
       UNION ALL SELECT 'web', $1 || '/webhook/web?s=' || slug, coalesce(titulo, slug) || ' · ' || visitas || ' visitas', creado_en FROM webs
       UNION ALL SELECT 'proyecto', CASE WHEN web_slug IS NULL THEN '' ELSE $1 || '/webhook/web?s=' || web_slug END, tipo || ': ' || nombre, creado_en FROM proyectos
     ) x ORDER BY creado_en DESC LIMIT 40`, [String($env.WEBHOOK_URL || 'http://localhost:5678/').replace(/\/$/, '')], 'lista'],
  orden: [`INSERT INTO ordenes (texto, origen) VALUES ($1, 'app') RETURNING 'Orden registrada. El Director la procesará en el próximo ciclo (8:00, 13:00 o 19:00) y te pedirá aprobación si hace falta.' AS respuesta`,
    [String(datos.texto || '').slice(0, 2000)], 'uno'],
};
const HTTP = {
  flujos: ['GET', `${API}/workflows?limit=100`, null, 'flujos'],
  flujo_activar: ['POST', `${API}/workflows/${encodeURIComponent(String(datos.id || '').replace(/[^A-Za-z0-9]/g, ''))}/${datos.activo ? 'activate' : 'deactivate'}`, {}, 'ok'],
  agente_ejecutar: ['POST', $env.AGENTE_WEBHOOK_URL || 'http://localhost:5678/webhook/omniagent-agente',
    { agente_id: datos.agente_id, input: String(datos.input || '').slice(0, 8000), origen: 'app' }, 'uno'],
};
if (SQL[accion]) { const [sql, params, forma] = SQL[accion]; return [{ json: { tipo: 'sql', accion, sql, params, forma } }]; }
const CREAR = { imagen: ['generar_imagen', 'post'], portada: ['generar_imagen', 'portada'], miniatura: ['generar_imagen', 'miniatura'],
  video: ['generar_video', 'vertical'], web: ['crear_web', ''], negocio: ['crear_negocio', 'negocio'], canal: ['crear_negocio', 'canal'] };
if (accion === 'crear') {
  const c = CREAR[datos.tipo];
  const texto = String(datos.texto || '').trim().slice(0, 3000);
  if (!c || !texto) return [{ json: { tipo: 'error', codigo: 400, r: { error: 'Indica qué crear y descríbelo' } } }];
  return [{ json: { tipo: 'herramienta', accion, forma: 'herramienta', herramienta: { accion: c[0], formato: c[1], texto, id: '', decision: '', agente_id: '' } } }];
}
if (HTTP[accion]) {
  if (accion !== 'agente_ejecutar' && !$env.N8N_API_KEY) return [{ json: { tipo: 'error', codigo: 503, r: { error: 'Falta N8N_API_KEY en el servidor' } } }];
  const [metodo, url, cuerpo, forma] = HTTP[accion];
  return [{ json: { tipo: 'http', accion, metodo, url, cuerpo, forma } }];
}
return [{ json: { tipo: 'error', codigo: 400, r: { error: 'Acción desconocida' } } }];
"""

SYS20_FORMATEAR = r"""
// Da a cada respuesta la forma que espera la app.
const ruta = $('Validar y enrutar').first().json;
const filas = $input.all().map((i) => i.json).filter((j) => j && Object.keys(j).length && !(Object.keys(j).length === 1 && j.success === true));
let r;
if (ruta.forma === 'lista') r = filas;
else if (ruta.forma === 'uno') r = filas[0] || {};
else if (ruta.forma === 'herramienta') { const t = filas[0]?.resultado ?? ''; let d; try { d = JSON.parse(t); } catch (e) { d = t; }
  r = typeof d === 'string' ? { respuesta: d } : { respuesta: d.respuesta || JSON.stringify(d), url: d.url || '', media_tipo: d.media_tipo || '' }; }
else if (ruta.forma === 'flujos') r = (filas[0]?.data || []).map((w) => ({ id: w.id, nombre: w.name, activo: w.active, ultima: (w.updatedAt || '').slice(0, 16).replace('T', ' '), estado: w.active ? 'ok' : 'pausado' }));
else r = { ok: true };
return [{ json: { r } }];
"""


def sys20():
    def si(nombre, valor, pos):
        return nodo(nombre, "n8n-nodes-base.if", 2.2, {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, nombre)), "leftValue": "={{ $json.tipo }}",
                                "rightValue": valor, "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and"},
            "options": {},
        }, pos)

    n = [
        nodo("Webhook de control", "n8n-nodes-base.webhook", 2, {
            "httpMethod": "POST", "path": "omniagent-control", "responseMode": "responseNode",
            "options": {"allowedOrigins": "*"},  # el acceso lo protege el token Bearer
        }, (0, 300), webhookId="6f1d1c1e-0a00-4c00-9a00-000000000d00"),
        code("Validar y enrutar", SYS20_VALIDAR, (220, 300)),
        si("¿Consulta SQL?", "sql", (440, 300)),
        si("¿Llamada HTTP?", "http", (660, 400)),
        si("¿Herramienta?", "herramienta", (880, 560)),
        nodo("Datos de la herramienta", "n8n-nodes-base.code", 2, {"jsCode": "return [{ json: $input.first().json.herramienta }];\n"}, (1100, 520)),
        sub("Crear", "SYS21", (1320, 520), modo="once"),
        pg("Postgres", "={{ $json.sql }}", "={{ $json.params }}", (660, 200), alwaysOutputData=True),
        http("API de n8n / agente", "={{ $json.metodo }}", "={{ $json.url }}",
             "={{ JSON.stringify($json.cuerpo || {}) }}", (880, 400),
             cabeceras=[("X-N8N-API-KEY", "={{ $env.N8N_API_KEY || '' }}"),
                        ("Authorization", "={{ 'Bearer ' + $env.OMNIAGENT_CONTROL_TOKEN }}")],
             alwaysOutputData=True),
        code("Formatear", SYS20_FORMATEAR, (1100, 300)),
        nodo("Responder", "n8n-nodes-base.respondToWebhook", 1.1,
             {"respondWith": "json", "responseBody": "={{ JSON.stringify($json.r) }}", "options": {}}, (1320, 300)),
        nodo("Responder error", "n8n-nodes-base.respondToWebhook", 1.1,
             {"respondWith": "json", "responseBody": "={{ JSON.stringify($json.r) }}",
              "options": {"responseCode": "={{ $json.codigo }}"}}, (1100, 700)),
    ]
    n[4]["parameters"]["query"] = "={{ $json.sql }}"
    c = enlazar(("Webhook de control", "Validar y enrutar"), ("Validar y enrutar", "¿Consulta SQL?"),
                ("¿Consulta SQL?", "Postgres", 0), ("¿Consulta SQL?", "¿Llamada HTTP?", 1),
                ("¿Llamada HTTP?", "API de n8n / agente", 0), ("¿Llamada HTTP?", "¿Herramienta?", 1),
                ("¿Herramienta?", "Datos de la herramienta", 0), ("¿Herramienta?", "Responder error", 1),
                ("Datos de la herramienta", "Crear"), ("Crear", "Formatear"),
                ("Postgres", "Formatear"), ("API de n8n / agente", "Formatear"), ("Formatear", "Responder"))
    return flujo("SYS20", "SYS-20 API de control (OmniAgent Control)", n, c)


# ═════════════════════════════════════════════════════════════════════
# SYS-21 · Herramientas para IAs (Claude, ChatGPT, Gemini vía MCP)
# ═════════════════════════════════════════════════════════════════════
ENTRADAS_HERRAMIENTAS = ["accion", "id", "decision", "texto", "agente_id", "formato"]


def sys21():
    n = [
        nodo("Llamada de herramienta", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {
            "inputSource": "workflowInputs",
            "workflowInputs": {"values": [{"name": k} for k in ENTRADAS_HERRAMIENTAS]},
        }, (0, 200)),
        code("Enrutar", r"""
const i = $input.first().json;
const a = String(i.accion || '');
const mapa = {
  resumen: {}, aprobaciones: {}, leads: {}, incidentes: {}, agentes: {},
  decidir: { id: i.id, decision: i.decision, comentario: i.texto || '' },
  orden: { texto: i.texto },
  agente_ejecutar: { agente_id: Number(i.agente_id), input: i.texto },
  incidente_reintentar: { id: i.id },
};
if (a === 'ciclo_contenido') return [{ json: { ruta: 1 } }];
const f = String(i.formato || '').toLowerCase();
if (a === 'generar_imagen') return [{ json: { ruta: 4, tipo: ['portada', 'miniatura'].includes(f) ? f : 'post',
  formato: ['cuadrado', 'vertical', 'horizontal'].includes(f) ? f : undefined, tema: i.texto } }];
if (a === 'generar_video') return [{ json: { ruta: 5, prompt: i.texto, formato: f === 'horizontal' ? 'horizontal' : 'vertical', avisar: true, titulo: String(i.texto || '').slice(0, 60) } }];
if (a === 'producir_videos') return [{ json: { ruta: 8 } }];
if (a === 'crear_web') return [{ json: { ruta: 6, encargo: i.texto, avisar: true } }];
if (a === 'crear_negocio') return [{ json: { ruta: 7, texto: i.texto, tipo: f === 'canal' ? 'canal' : 'negocio' } }];
if (a === 'pausar' || a === 'reanudar') return [{ json: { ruta: 0, cuerpo: { accion: 'piloto', datos: { pausa: a === 'pausar' } } } }];
if (a === 'publicar_ahora') return [{ json: { ruta: 2 } }];
if (!(a in mapa)) return [{ json: { ruta: 3, resultado: 'Acción desconocida: ' + a } }];
return [{ json: { ruta: 0, cuerpo: { accion: a, datos: mapa[a] } } }];
""", (220, 200)),
        nodo("Ruta", "n8n-nodes-base.switch", 3.2,
             {"mode": "expression", "numberOutputs": 9, "output": "={{ $json.ruta }}"}, (440, 200)),
        http("API de control", "POST",
             "={{ ($env.N8N_INTERNAL_URL || 'http://localhost:5678') + '/webhook/omniagent-control' }}",
             "={{ JSON.stringify($json.cuerpo) }}", (680, 0),
             cabeceras=[("Authorization", "={{ 'Bearer ' + $env.OMNIAGENT_CONTROL_TOKEN }}")],
             onError="continueRegularOutput", alwaysOutputData=True),
        nodo("Lanzar ciclo de contenido", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["CNT01"], "mode": "id"},
            "mode": "once", "options": {"waitForSubWorkflow": False}}, (680, 150)),
        nodo("Lanzar publicador", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["PUB01"], "mode": "id"},
            "mode": "once", "options": {"waitForSubWorkflow": False}}, (680, 300)),
        sub("Imagen", "GEN01", (680, 450)),
        sub("Vídeo", "GEN02", (680, 600), esperar=False),
        sub("Web", "GEN03", (680, 750), esperar=False),
        sub("Negocio o canal", "NEG01", (680, 900), esperar=False),
        sub("Producir vídeos", "VID01", (680, 1050), esperar=False, modo="once"),
        code("Resultado", r"""
const xs = $input.all().map((i) => i.json);
const r = xs[0] || {};
if (r.ruta === 1) return [{ json: { resultado: 'Ciclo de contenido lanzado. En 1-3 minutos las piezas nuevas estarán en la cola o en Aprobar.' } }];
if (r.ruta === 2) return [{ json: { resultado: 'Publicador lanzado: se publican ahora las piezas en cola cuya hora ya ha llegado.' } }];
if (r.ruta === 3) return [{ json: { resultado: r.resultado } }];
if (r.ruta === 5) return [{ json: { resultado: '🎬 Vídeo en marcha con IA: tarda entre 1 y 6 minutos. Te lo envío por WhatsApp y Telegram en cuanto esté.' } }];
if (r.ruta === 8) return [{ json: { resultado: '🎬 Fábrica de vídeo en marcha: convierte en vídeo el siguiente guion pendiente (respetando VIDEOS_POR_DIA). Te aviso con cada vídeo.' } }];
if (r.ruta === 6) return [{ json: { resultado: '🌐 Creando la web: en 1-2 minutos te mando el enlace.' } }];
if (r.ruta === 7) return [{ json: { resultado: '🚀 Creando el proyecto completo (plan, portada, web y la primera semana de contenido). Tarda 2-4 minutos; te aviso al terminar.' } }];
if (r.url && r.media_tipo === 'imagen') return [{ json: { resultado: JSON.stringify({ respuesta: '🖼 Imagen lista: ' + r.url, url: r.url, media_tipo: 'imagen' }) } }];
if (r.error) return [{ json: { resultado: 'Error: ' + (r.error.message || JSON.stringify(r.error)) } }];
return [{ json: { resultado: JSON.stringify(xs.length === 1 ? r : xs) } }];
""", (920, 200)),
    ]
    c = enlazar(("Llamada de herramienta", "Enrutar"), ("Enrutar", "Ruta"),
                ("Ruta", "API de control", 0), ("Ruta", "Lanzar ciclo de contenido", 1),
                ("Ruta", "Lanzar publicador", 2), ("Ruta", "Resultado", 3),
                ("API de control", "Resultado"), ("Lanzar ciclo de contenido", "Resultado"),
                ("Lanzar publicador", "Resultado"),
                ("Ruta", "Imagen", 4), ("Ruta", "Vídeo", 5), ("Ruta", "Web", 6), ("Ruta", "Negocio o canal", 7), ("Ruta", "Producir vídeos", 8), ("Producir vídeos", "Resultado"),
                ("Imagen", "Resultado"), ("Vídeo", "Resultado"), ("Web", "Resultado"), ("Negocio o canal", "Resultado"))
    return flujo("SYS21", "SYS-21 Herramientas para IAs", n, c)


# ═════════════════════════════════════════════════════════════════════
# MCP-01 · Servidor MCP: dirige OmniAgent desde Claude, ChatGPT o Gemini
# ═════════════════════════════════════════════════════════════════════
HERRAMIENTAS = [
    ("ver_resumen", "resumen", "KPIs del negocio EstrategIA Digital 3.0: leads, piezas, publicaciones, coste de IA, ingresos, aprobaciones e incidentes, y la actividad reciente.", {}),
    ("ver_aprobaciones", "aprobaciones", "Lista las piezas de contenido que esperan aprobación (id, canal, texto).", {}),
    ("decidir_pieza", "decidir", "Aprueba, pide cambios o descarta una pieza de contenido pendiente. Confirma con el usuario antes de aprobar o descartar.", {
        "id": "id (uuid) de la pieza, tal como aparece en ver_aprobaciones",
        "decision": "aprobar, cambiar o descartar",
        "texto": "comentario con los cambios pedidos (vacío si apruebas o descartas)"}),
    ("dar_orden", "orden", "Envía una orden en lenguaje natural al Director de contenido (por ejemplo: prepara 3 posts sobre automatización para mañana). Se procesa en el siguiente ciclo o al lanzar el ciclo.", {
        "texto": "la orden completa en español"}),
    ("ver_leads", "leads", "Últimos leads (seudonimizados) con su score, estado y origen.", {}),
    ("ver_incidentes", "incidentes", "Errores recientes de los flujos y si se autorrepararon.", {}),
    ("reintentar_incidente", "incidente_reintentar", "Programa el reintento inmediato de un incidente.", {
        "id": "id (uuid) del incidente"}),
    ("ver_agentes", "agentes", "Los 15 agentes de OmniAgent con su id, versión de prompt, uso y coste de los últimos 7 días.", {}),
    ("consultar_agente", "agente_ejecutar", "Ejecuta uno de los 15 agentes con un texto y devuelve su respuesta (0 Director, 1 Estrategia, 2 Copywriting, 3 Conversación, 4 Visual, 5 Vídeo y voz, 6 Productos formativos, 7 Humanizador, 8 Evaluador, 9 Anuncios, 10 SEO y blog, 11 Marca faceless, 12 Traducción, 13 Analista de comunidad, 14 Archivista).", {
        "agente_id": "número del agente, de 0 a 14",
        "texto": "lo que quieres que haga el agente"}),
    ("lanzar_ciclo_contenido", "ciclo_contenido", "Lanza ahora un ciclo del Director: procesa las órdenes pendientes, genera y evalúa piezas nuevas.", {}),
    ("publicar_ahora", "publicar_ahora", "Ejecuta ya el publicador para las piezas en cola cuya hora ha llegado.", {}),
    ("generar_imagen", "generar_imagen", "Genera una imagen con IA para la marca: post de redes, portada o miniatura de YouTube. Devuelve la URL pública.", {
        "texto": "qué debe mostrar la imagen (tema, estilo, texto que debe aparecer)",
        "formato": "post, portada o miniatura"}),
    ("generar_video", "generar_video", "Genera un vídeo corto (unos 8 s, con audio) con IA (Veo u OpenAI) para un short o reel. Tarda unos minutos; el resultado llega por WhatsApp y Telegram.", {
        "texto": "descripción del vídeo: escena, estilo y lo que dice el narrador",
        "formato": "vertical (short o reel) u horizontal"}),
    ("crear_web", "crear_web", "Crea y publica una landing page con formulario de captación de leads. Avisa con el enlace al terminar.", {
        "texto": "encargo de la web: negocio, oferta, público y llamada a la acción"}),
    ("crear_negocio", "crear_negocio", "Crea un negocio digital o un canal automatizado completo: plan, portada, web y la primera semana de contenido. Avisa al terminar.", {
        "texto": "la idea, el nicho o el tipo de negocio o canal",
        "formato": "negocio o canal"}),
    ("producir_videos", "producir_videos", "Convierte ya en vídeo (con IA) el siguiente guion pendiente de TikTok, YouTube o Reels.", {}),
    ("pausar_automatico", "pausar", "Pone en pausa la creación y la publicación automáticas. Pide confirmación antes.", {}),
    ("reanudar_automatico", "reanudar", "Reanuda la creación y la publicación automáticas.", {}),
]


def mcp01():
    esquema = [{"id": k, "displayName": k, "required": False, "defaultMatch": False, "display": True,
                "canBeUsedToMatch": True, "type": "string", "removed": False} for k in ENTRADAS_HERRAMIENTAS]
    n = [nodo("MCP OmniAgent", "@n8n/n8n-nodes-langchain.mcpTrigger", 2.1, {
        "authentication": "n8nOAuth2", "requireExecuteAccess": True, "includeUserInOutput": False,
        "path": "omniagent",
        "instructions": "Eres el puente con OmniAgent OS, el sistema que gestiona en automático las redes sociales, el email y los leads de EstrategIA Digital 3.0. Usa ver_resumen para orientarte. Antes de aprobar o descartar contenido, enseña el texto al usuario y pide confirmación.",
    }, (600, 0), webhookId="6f1d1c1e-0a00-4c00-9a00-000000000e00")]
    c = {}
    for i, (nombre, accion, desc, args) in enumerate(HERRAMIENTAS):
        valor = {k: "" for k in ENTRADAS_HERRAMIENTAS}
        valor["accion"] = accion
        for k, d in args.items():
            valor[k] = "={{ $fromAI('%s', %s, 'string') }}" % (k, json.dumps(d, ensure_ascii=False).replace("'", "\\'"))
        n.append(nodo(nombre, "@n8n/n8n-nodes-langchain.toolWorkflow", 2.2, {
            "description": desc, "source": "database",
            "workflowId": {"__rl": True, "value": ID["SYS21"], "mode": "id"},
            "workflowInputs": {"mappingMode": "defineBelow", "value": valor, "matchingColumns": [], "schema": esquema,
                               "attemptToConvertTypes": False, "convertFieldsToString": False},
        }, (i * 160, 300)))
        c[nombre] = {"ai_tool": [[{"node": "MCP OmniAgent", "type": "ai_tool", "index": 0}]]}
    return flujo("MCP01", "MCP-01 Servidor MCP para IAs", n, c)


# ═════════════════════════════════════════════════════════════════════
# PUB-02 / PUB-03 · Publicar en LinkedIn y en X (subflujos aislados)
# Van aparte porque sus nodos exigen una cuenta conectada; así, si aún no
# la has conectado, solo falla esa red y el resto sigue publicando.
# ═════════════════════════════════════════════════════════════════════
def pub_red(clave, nombre, nodo_red):
    n = [
        nodo("Desde el publicador", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        nodo_red,
    ]
    c = enlazar(("Desde el publicador", nodo_red["name"]))
    return flujo(clave, nombre, n, c)


def pub02():
    return pub_red("PUB02", "PUB-02 Publicar en LinkedIn", nodo("LinkedIn", "n8n-nodes-base.linkedIn", 1, {
        "postAs": "person", "person": "", "text": "={{ $json.texto }}",
        "shareMediaCategory": "NONE", "additionalFields": {"visibility": "PUBLIC"},
    }, (240, 0)))


def pub03():
    n = [
        nodo("Desde el publicador", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Preparar hilo", r"""
const j = $input.first().json;
const tweets = (j.tweets && j.tweets.length ? j.tweets : [j.texto]).map((t) => String(t || '').trim()).filter(Boolean);
return [{ json: { texto: tweets[0], resto: tweets.slice(1), responder_a: String(j.responder_a || '') } }];
""", (220, 0)),
        si_campo("¿Es respuesta?", "responder_a", "", (440, 0), operador="notEmpty"),
        nodo("X · responder", "n8n-nodes-base.twitter", 2, {"text": "={{ $json.texto }}",
             "additionalFields": {"inReplyToStatusId": {"__rl": True, "mode": "id", "value": "={{ $json.responder_a }}"}}}, (660, -80)),
        nodo("X", "n8n-nodes-base.twitter", 2, {"text": "={{ $json.texto }}", "additionalFields": {}}, (660, 80)),
        code("Seguir el hilo", r"""
const prev = $('Preparar hilo').first().json;
const id = $input.first().json.id;
if (!id) throw new Error('X no devolvió el id del tuit');
return [{ json: { id, resto: prev.resto, hay_mas: prev.resto.length > 0 } }];
""", (880, 0)),
        si_campo("¿Quedan tuits?", "hay_mas", True, (1100, 0), operador="true", tipo="boolean"),
        code("Siguiente tuit", "const j = $input.first().json; return [{ json: { tweets: j.resto, responder_a: j.id } }];", (1320, -80)),
        nodo("Publicar resto del hilo", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["PUB03"], "mode": "id"},
            "mode": "once", "options": {"waitForSubWorkflow": True}}, (1540, -80)),
        code("Resultado", "return [{ json: { id: $('Seguir el hilo').first().json.id } }];", (1760, 0)),
    ]
    c = enlazar(("Desde el publicador", "Preparar hilo"), ("Preparar hilo", "¿Es respuesta?"),
                ("¿Es respuesta?", "X · responder", 0), ("¿Es respuesta?", "X", 1),
                ("X · responder", "Seguir el hilo"), ("X", "Seguir el hilo"), ("Seguir el hilo", "¿Quedan tuits?"),
                ("¿Quedan tuits?", "Siguiente tuit", 0), ("Siguiente tuit", "Publicar resto del hilo"),
                ("Publicar resto del hilo", "Resultado"), ("¿Quedan tuits?", "Resultado", 1))
    return flujo("PUB03", "PUB-03 Publicar en X (tuits e hilos)", n, c)


# ═════════════════════════════════════════════════════════════════════
# WA-02 · Enviar un WhatsApp (texto, botones, imagen o vídeo). Si el dueño lleva
# más de 24 h sin escribir, Meta exige plantilla: se reintenta con WHATSAPP_PLANTILLA_AVISO.
# ═════════════════════════════════════════════════════════════════════
GRAPH = "($env.META_GRAPH_URL || 'https://graph.facebook.com') + '/' + ($env.META_API_VERSION || 'v21.0') + '/'"


def wa02():
    n = [
        nodo("Enviar WhatsApp", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Preparar mensaje", r"""
if (!$env.WHATSAPP_TOKEN || !$env.WHATSAPP_PHONE_ID) return [];
const num = (s) => String(s || '').replace(/\D/g, '');
const out = [];
for (const it of $input.all()) {
  const j = it.json;
  const to = num(j.to || $env.WHATSAPP_NUMERO_DUENO);
  if (!to || !String(j.texto || '').trim()) continue;
  const botones = (j.botones || []).slice(0, 3);
  const texto = String(j.texto).slice(0, botones.length ? 1000 : 4000);
  const media = !botones.length && j.media_url && ['imagen', 'video'].includes(j.media_tipo) ? (j.media_tipo === 'imagen' ? 'image' : 'video') : '';
  const cuerpo = media
    ? { messaging_product: 'whatsapp', to, type: media, [media]: { link: j.media_url, caption: texto.slice(0, 1024) } }
    : botones.length
    ? { messaging_product: 'whatsapp', to, type: 'interactive', interactive: { type: 'button', body: { text: texto },
        action: { buttons: botones.map((b) => ({ type: 'reply', reply: { id: String(b.id).slice(0, 256), title: String(b.titulo).slice(0, 20) } })) } } }
    : { messaging_product: 'whatsapp', to, type: 'text', text: { body: texto, preview_url: false } };
  out.push({ json: { to, texto, cuerpo } });
}
return out;
""", (220, 0)),
        http("Enviar", "POST", "={{ " + GRAPH + " + $env.WHATSAPP_PHONE_ID + '/messages' }}",
             "={{ JSON.stringify($json.cuerpo) }}", (440, 0),
             cabeceras=[("Authorization", "={{ 'Bearer ' + $env.WHATSAPP_TOKEN }}")], onError="continueRegularOutput"),
        code("¿Hace falta plantilla?", r"""
// Error 131047: han pasado más de 24 h desde el último mensaje del destinatario.
const out = [];
const num = (s) => String(s || '').replace(/\D/g, '');
$input.all().forEach((it, i) => {
  const p = $('Preparar mensaje').all()[i]?.json;
  if (!p || !it.json.error) return;
  const fuera24h = /131047|re-engagement|24 hours/i.test(JSON.stringify(it.json.error));
  if (!fuera24h || !$env.WHATSAPP_PLANTILLA_AVISO || p.to !== num($env.WHATSAPP_NUMERO_DUENO)) return;
  const texto = String(p.texto).replace(/\s*\n+\s*/g, ' · ').replace(/\s{4,}/g, ' ').slice(0, 1000);
  out.push({ json: { cuerpo: { messaging_product: 'whatsapp', to: p.to, type: 'template', template: {
    name: $env.WHATSAPP_PLANTILLA_AVISO, language: { code: $env.WHATSAPP_PLANTILLA_IDIOMA || 'es' },
    components: [{ type: 'body', parameters: [{ type: 'text', text: texto }] }] } } } });
});
return out;
""", (660, 0)),
        http("Enviar plantilla", "POST", "={{ " + GRAPH + " + $env.WHATSAPP_PHONE_ID + '/messages' }}",
             "={{ JSON.stringify($json.cuerpo) }}", (880, 0),
             cabeceras=[("Authorization", "={{ 'Bearer ' + $env.WHATSAPP_TOKEN }}")], onError="continueRegularOutput"),
    ]
    c = enlazar(("Enviar WhatsApp", "Preparar mensaje"), ("Preparar mensaje", "Enviar"),
                ("Enviar", "¿Hace falta plantilla?"), ("¿Hace falta plantilla?", "Enviar plantilla"))
    return flujo("WA02", "WA-02 Enviar WhatsApp", n, c)


# ═════════════════════════════════════════════════════════════════════
# WA-01 · WhatsApp entrante: control total para el dueño y atención a clientes
# ═════════════════════════════════════════════════════════════════════
AYUDA_WA = (
    "🤖 *OmniAgent* · lo que puedes escribirme:\n"
    "• *resumen* → cómo va el negocio\n"
    "• *pendientes* → piezas por aprobar (con botones)\n"
    "• *leads* · *incidentes* · *agentes*\n"
    "• *ciclo* → crear contenido ahora\n"
    "• *publicar* → publicar ya lo que toca\n"
    "• *pausar* / *reanudar* → piloto automático\n"
    "• *agente 2: tu petición* → hablar con un agente (0-14)\n"
    "• *orden: …* → encargo al Director\n"
    "• *imagen: …* · *portada: …* · *miniatura: …* → imagen con IA\n"
    "• *video: …* → short o reel con IA · *videos* → convertir ya en vídeo los guiones pendientes\n"
    "• *web: …* → landing con formulario\n"
    "• *negocio: …* · *canal: …* → negocio o canal completo\n"
    "O escríbeme normal («prepara 3 posts para mañana sobre WhatsApp») y lo entiendo."
)


def si_campo(nombre, campo, valor, pos, operador="equals", tipo="string"):
    cond = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "si/" + nombre)), "leftValue": "={{ $json.%s }}" % campo,
            "rightValue": valor, "operator": {"type": tipo, "operation": operador}}
    if tipo == "boolean":
        cond["operator"]["singleValue"] = True
    return nodo(nombre, "n8n-nodes-base.if", 2.2, {
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                       "conditions": [cond], "combinator": "and"}, "options": {}}, pos)


def a_whatsapp(nombre, pos):
    return nodo(nombre, "n8n-nodes-base.executeWorkflow", 1.1, {
        "source": "database", "workflowId": {"__rl": True, "value": ID["WA02"], "mode": "id"},
        "mode": "each", "options": {"waitForSubWorkflow": True}}, pos, onError="continueRegularOutput")


def wa01():
    n = [
        # Verificación del webhook (Meta la pide una vez al configurarlo)
        nodo("Verificación de Meta", "n8n-nodes-base.webhook", 2,
             {"httpMethod": "GET", "path": "whatsapp", "responseMode": "responseNode", "options": {}},
             (0, -300), webhookId="6f1d1c1e-0a00-4c00-9a00-000000000f00"),
        code("Comprobar token", r"""
const q = $input.first().json.query || {};
const ok = q['hub.mode'] === 'subscribe' && !!$env.WHATSAPP_VERIFY_TOKEN && q['hub.verify_token'] === $env.WHATSAPP_VERIFY_TOKEN;
return [{ json: { codigo: ok ? 200 : 403, texto: ok ? String(q['hub.challenge'] || '') : 'forbidden' } }];
""", (220, -300)),
        nodo("Responder a Meta", "n8n-nodes-base.respondToWebhook", 1.1,
             {"respondWith": "text", "responseBody": "={{ $json.texto }}", "options": {"responseCode": "={{ $json.codigo }}"}},
             (440, -300)),
        # Mensajes
        nodo("Mensaje entrante", "n8n-nodes-base.webhook", 2,
             {"httpMethod": "POST", "path": "whatsapp", "responseMode": "onReceived", "options": {"rawBody": True}},
             (0, 0), webhookId="6f1d1c1e-0a00-4c00-9a00-000000001000"),
        code("Verificar firma e interpretar", r"""
// Solo se aceptan mensajes firmados por Meta (cabecera X-Hub-Signature-256 con tu App Secret).
const crypto = require('crypto');
const secreto = $env.WHATSAPP_APP_SECRET;
if (!secreto) throw new Error('Falta WHATSAPP_APP_SECRET: por seguridad se ignoran los mensajes de WhatsApp');
const it = $input.first();
const firma = String(it.json.headers?.['x-hub-signature-256'] || '');
const crudo = await this.helpers.getBinaryDataBuffer(0, 'data');
const esperada = 'sha256=' + crypto.createHmac('sha256', secreto).update(crudo).digest('hex');
if (firma.length !== esperada.length || !crypto.timingSafeEqual(Buffer.from(firma), Buffer.from(esperada))) return [];
const body = JSON.parse(crudo.toString('utf8'));
const num = (s) => String(s || '').replace(/\D/g, '');
const dueno = num($env.WHATSAPP_NUMERO_DUENO);
const out = [];
for (const e of body.entry || []) for (const ch of e.changes || []) {
  const v = ch.value || {};
  const nombres = {};
  (v.contacts || []).forEach((c) => { nombres[c.wa_id] = c.profile?.name || ''; });
  for (const m of v.messages || []) {
    let texto = '', boton = '';
    if (m.type === 'text') texto = m.text?.body || '';
    else if (m.type === 'interactive') { boton = m.interactive?.button_reply?.id || m.interactive?.list_reply?.id || ''; texto = m.interactive?.button_reply?.title || m.interactive?.list_reply?.title || ''; }
    else if (m.type === 'button') { boton = m.button?.payload || ''; texto = m.button?.text || ''; }
    else texto = '[Ha enviado un mensaje de tipo ' + m.type + ', que todavía no puedo leer]';
    const de = num(m.from);
    out.push({ json: { rol: dueno && de === dueno ? 'dueno' : 'cliente', de, nombre: nombres[m.from] || '',
      texto: String(texto).slice(0, 4000), boton, tipo: m.type, msg_id: m.id } });
  }
}
return out;
""", (220, 0)),
        si_campo("¿Es el dueño?", "rol", "dueno", (440, 0)),

        # ── Dueño: control total ───────────────────────────────────────
        code("Entender orden", r"""
return $input.all().map((it) => {
  const j = it.json, t = String(j.texto || '').trim(), b = String(j.boton || '');
  let a = null, m;
  if (/^[ad]:[0-9a-f-]{36}$/i.test(b)) a = { accion: 'decidir', id: b.slice(2), decision: b[0] === 'a' ? 'aprobar' : 'descartar' };
  else if (/^(hola|men[uú]|ayuda|\?|\/start)$/i.test(t)) a = { accion: 'ayuda' };
  else if (/^(resumen|estado|kpis?|c[oó]mo va.*)$/i.test(t)) a = { accion: 'resumen' };
  else if (/^(pendientes|aprobar|aprobaciones)$/i.test(t)) a = { accion: 'aprobaciones' };
  else if (/^leads?$/i.test(t)) a = { accion: 'leads' };
  else if (/^incidentes?$/i.test(t)) a = { accion: 'incidentes' };
  else if (/^agentes$/i.test(t)) a = { accion: 'agentes' };
  else if (/^ciclo$/i.test(t)) a = { accion: 'ciclo_contenido' };
  else if (/^publicar$/i.test(t)) a = { accion: 'publicar_ahora' };
  else if (/^pausar$/i.test(t)) a = { accion: 'pausar' };
  else if (/^reanudar$/i.test(t)) a = { accion: 'reanudar' };
  else if (/^v[ií]deos$/i.test(t)) a = { accion: 'producir_videos' };
  else if ((m = t.match(/^agente\s+(\d{1,2})\s*[:\-]?\s+([\s\S]+)/i))) a = { accion: 'agente_ejecutar', agente_id: m[1], texto: m[2] };
  else if ((m = t.match(/^orden\s*[:\-]?\s+([\s\S]+)/i))) a = { accion: 'orden', texto: m[1] };
  else if ((m = t.match(/^(imagen|portada|miniatura)\s*[:\-]\s*([\s\S]+)/i))) a = { accion: 'generar_imagen', formato: m[1].toLowerCase() === 'imagen' ? 'post' : m[1].toLowerCase(), texto: m[2] };
  else if ((m = t.match(/^v[ií]deo\s*[:\-]\s*([\s\S]+)/i))) a = { accion: 'generar_video', formato: 'vertical', texto: m[1] };
  else if ((m = t.match(/^web\s*[:\-]\s*([\s\S]+)/i))) a = { accion: 'crear_web', texto: m[1] };
  else if ((m = t.match(/^(negocio|canal)\s*[:\-]\s*([\s\S]+)/i))) a = { accion: 'crear_negocio', formato: m[1].toLowerCase(), texto: m[2] };
  return { json: Object.assign({ accion: 'interpretar', id: '', decision: '', texto: t, agente_id: '', formato: '' }, a || {}, { de: j.de, original: t }) };
});
""", (660, -150)),
        si_campo("¿Hay que interpretar?", "accion", "interpretar", (880, -150)),
        code("Pedir a la IA", r"""
return $input.all().map((it) => ({ json: { agente_id: 0, max_tokens: 400, origen: 'WA-01', input:
  'Eres el asistente de control de OmniAgent OS (EstrategIA Digital 3.0). El dueño escribe por WhatsApp: «' + it.json.original + '».\n' +
  'Elige UNA acción y responde SOLO JSON: {"accion":"","id":"","decision":"","texto":"","agente_id":"","formato":""}.\n' +
  'Acciones: resumen (cómo va el negocio), aprobaciones (ver pendientes), leads, incidentes, agentes, ciclo_contenido (crear contenido ya), ' +
  'publicar_ahora, pausar (parar el piloto automático), reanudar, agente_ejecutar (pedir algo a un agente: agente_id 0-14 y texto; ' +
  '0 Director, 1 Estrategia, 2 Copywriting, 3 Conversación, 4 Visual, 5 Vídeo y voz, 6 Productos formativos, 7 Humanizador, 8 Evaluador, ' +
  '9 Anuncios, 10 SEO y blog, 11 Marca faceless, 12 Traducción, 13 Analista de comunidad, 14 Archivista), ' +
  'generar_imagen (texto: qué mostrar; formato: post, portada o miniatura), generar_video (texto: descripción del vídeo), ' +
  'crear_web (texto: encargo de la web), crear_negocio (texto: la idea; formato: negocio o canal), ' +
  'orden (encargo de contenido o tarea para el Director: pon en texto la petición completa), ayuda. Si dudas, usa orden.' } }));
""", (1100, -250)),
        llamar_agente("IA de control", (1320, -250)),
        code("Leer intención", JSON_DE_TEXTO + r"""
const previos = $('Entender orden').all().filter((x) => x.json.accion === 'interpretar');
const validas = ['resumen', 'aprobaciones', 'leads', 'incidentes', 'agentes', 'ciclo_contenido', 'publicar_ahora', 'pausar', 'reanudar', 'agente_ejecutar', 'orden', 'ayuda',
  'generar_imagen', 'generar_video', 'crear_web', 'crear_negocio', 'producir_videos'];
return $input.all().map((it, i) => {
  const p = previos[i]?.json || {};
  let r = {};
  try { r = jsonDeTexto(it.json.respuesta); } catch (e) { r = {}; }
  const accion = validas.includes(r.accion) ? r.accion : 'orden';
  return { json: { accion, id: '', decision: '', texto: String(r.texto || p.original || ''), agente_id: String(r.agente_id ?? ''), formato: String(r.formato || ''), de: p.de, original: p.original } };
});
""", (1540, -250)),
        code("Preparar herramienta", r"""
return $input.all().map((it) => ({ json: it.json }));
""", (1760, -150)),
        nodo("Ejecutar herramienta", "n8n-nodes-base.executeWorkflow", 1.1, {
            "source": "database", "workflowId": {"__rl": True, "value": ID["SYS21"], "mode": "id"},
            "mode": "each", "options": {"waitForSubWorkflow": True}}, (1980, -150), onError="continueRegularOutput"),
        code("Redactar respuesta", r"""
const ctx = $('Preparar herramienta').all();
const AYUDA = """ + json.dumps(AYUDA_WA, ensure_ascii=False) + r""";
const lista = (d) => (Array.isArray(d) ? d : d && Object.keys(d).length ? [d] : []);
const out = [];
$input.all().forEach((it, i) => {
  const c = ctx[i]?.json || {};
  const r = it.json.resultado ?? (it.json.error ? 'Error: ' + (it.json.error.message || JSON.stringify(it.json.error)) : '');
  let d; try { d = JSON.parse(r); } catch (e) { d = r; }
  let texto = '';
  const extra = [];
  switch (c.accion) {
    case 'ayuda': texto = AYUDA; break;
    case 'resumen': { const k = d.kpis || {};
      texto = '📊 *EstrategIA Digital 3.0 · hoy*\n👤 Leads: ' + k.leads_hoy + ' (semana: ' + k.leads_semana + ')\n📝 Piezas creadas: ' + k.piezas_hoy +
        ' · publicadas 7 días: ' + k.publicadas_semana + '\n💶 IA: ' + k.coste_ia_hoy + ' € de ' + k.presupuesto_ia + ' €\n💰 Ingresos del mes: ' + k.ingresos_mes +
        ' €\n🟡 Por aprobar: ' + k.aprobaciones + ' · 🛠 Incidentes: ' + k.incidentes + (k.en_pausa ? '\n⏸ Piloto automático EN PAUSA (escribe *reanudar*)' : '') + (k.aprobaciones ? '\n\nEscribe *pendientes* para verlas.' : '');
      break; }
    case 'aprobaciones': { const l = lista(d);
      if (!l.length) { texto = '✅ No hay nada pendiente de aprobar.'; break; }
      texto = '🟡 ' + l.length + ' pieza(s) por aprobar' + (l.length > 5 ? ' (te mando las 5 primeras)' : '') + ':';
      l.slice(0, 5).forEach((p) => extra.push({ texto: '*' + p.canal + '* · ' + p.formato + (p.sensible ? ' · ⚠ sensible' : '') + '\n\n' + String(p.texto || '').slice(0, 900),
        botones: [{ id: 'a:' + p.id, titulo: '✅ Aprobar' }, { id: 'd:' + p.id, titulo: '🗑 Descartar' }] }));
      break; }
    case 'decidir': texto = d && d.ok ? (c.decision === 'aprobar' ? '✅ Aprobada: se publicará en la próxima hora.' : '🗑 Descartada.') : 'No pude aplicarlo: ' + String(r).slice(0, 300); break;
    case 'leads': { const l = lista(d); texto = l.length ? '👤 *Últimos leads*\n' + l.slice(0, 10).map((x) => '• ' + x.nombre + ' · ' + x.score + ' pts · ' + x.estado + ' · ' + x.origen + ' · ' + x.fecha).join('\n') : 'Aún no hay leads.'; break; }
    case 'incidentes': { const l = lista(d); texto = l.length ? '🛠 *Incidentes*\n' + l.slice(0, 8).map((x) => '• ' + x.cuando + ' ' + x.workflow + (x.autorreparado ? ' ✅' : ' ⚠') + '\n  ' + String(x.error || '').slice(0, 120)).join('\n') : '✅ Sin incidentes.'; break; }
    case 'agentes': { const l = lista(d); texto = '🤖 *Agentes*\n' + l.map((x) => x.id + ' · ' + x.nombre + ' (' + x.ejecuciones_7d + ' usos, ' + x.coste_7d + ' €)').join('\n'); break; }
    case 'agente_ejecutar': case 'orden': texto = (d && d.respuesta) || String(r); break;
    case 'generar_imagen':
      if (d && d.url) { out.push({ json: { to: c.de, texto: '🖼 ' + String(c.texto || '').slice(0, 200), media_url: d.url, media_tipo: 'imagen' } }); texto = 'Enlace: ' + d.url; }
      else texto = String(r);
      break;
    default: texto = typeof d === 'string' ? d : (d.respuesta || JSON.stringify(d).slice(0, 1500));
  }
  out.push({ json: { to: c.de, texto } });
  extra.forEach((e) => out.push({ json: Object.assign({ to: c.de }, e) }));
});
return out;
""", (2200, -150)),
        a_whatsapp("Contestar al dueño", (2420, -150)),

        # ── Clientes: atención con IA ─────────────────────────────────
        pg("Contacto", """
INSERT INTO contactos (telefono, nombre, origen, ultimo_contacto) VALUES ($1, nullif($2, ''), 'whatsapp', now())
ON CONFLICT (telefono) DO UPDATE SET ultimo_contacto = now(), nombre = coalesce(contactos.nombre, excluded.nombre)
RETURNING id, score, (SELECT coalesce(string_agg('Cliente: ' || left(m.entrante, 300) || E'\\nNosotros: ' || left(coalesce(m.respuesta, ''), 300), E'\\n---\\n'), '')
                      FROM (SELECT * FROM mensajes WHERE contacto_id = contactos.id ORDER BY creado_en DESC LIMIT 4) m) AS historial
""", "={{ [$json.de, $json.nombre] }}", (660, 200)),
        code("Encargo", r"""
const msgs = $('¿Es el dueño?').all();
return $input.all().map((it, i) => {
  const e = $('Verificar firma e interpretar').all().filter((x) => x.json.rol === 'cliente')[i].json;
  const c = it.json;
  const input = 'Mensaje de WhatsApp de un cliente (' + (e.nombre || 'sin nombre') + '):\n«' + e.texto + '»' +
    (c.historial ? '\n\nConversación anterior (de la más reciente a la más antigua):\n' + c.historial : '\n\nEs su primer mensaje.') +
    '\n\nResponde como en WhatsApp: breve (máximo 5 líneas), cercano, sin listas largas. Responde SOLO JSON: {"respuesta":"","requiere_humano":false,"motivo":"","score":0,"intencion":"info|compra|soporte|queja|spam|otro"}' +
    '\nPon requiere_humano=true si quiere precio cerrado, contratar, reservar, se queja, pide hablar con una persona, o no sabes la respuesta.';
  return { json: { agente_id: 3, input, max_tokens: 800, origen: 'WA-01' } };
});
""", (880, 200)),
        llamar_agente("Agente de conversación", (1100, 200)),
        code("Decidir respuesta", JSON_DE_TEXTO + r"""
const clientes = $('Verificar firma e interpretar').all().filter((x) => x.json.rol === 'cliente');
const contactos = $('Contacto').all();
const auto = String($env.MODO_AUTOMATICO || 'true') === 'true';
return $input.all().map((it, i) => {
  const e = clientes[i].json, c = contactos[i].json;
  let r;
  try { r = jsonDeTexto(it.json.respuesta); } catch (err) { r = { respuesta: '', requiere_humano: true, motivo: 'Respuesta del agente no válida', score: 0, intencion: 'otro' }; }
  const pidePersona = /\bpersona\b|humano|hablar con alguien/i.test(e.texto);
  const spam = r.intencion === 'spam';
  const humano = !spam && (pidePersona || !!r.requiere_humano || !auto || !String(r.respuesta || '').trim());
  let respuesta = String(r.respuesta || '').trim();
  if (!c.historial) respuesta += '\n\n_(Te atiende el asistente de IA de EstrategIA Digital 3.0. Escribe «persona» para hablar con el equipo.)_';
  if (humano) respuesta = (respuesta && !pidePersona ? respuesta + '\n\n' : '') + 'Le paso tu mensaje al equipo y te escribimos en cuanto podamos. 🙌';
  return { json: { to: e.de, texto: spam ? '' : respuesta, humano, spam, score: Math.max(0, Math.min(100, Number(r.score) || 0)),
    intencion: r.intencion || 'otro', motivo: r.motivo || '', contacto_id: c.id, entrante: e.texto, nombre: e.nombre } };
});
""", (1320, 200)),
        a_whatsapp("Responder al cliente", (1540, 100)),
        pg("Registrar conversación", """
WITH m AS (INSERT INTO mensajes (canal, contacto_id, entrante, respuesta, estado)
           VALUES ('whatsapp', $1::uuid, $2, nullif($3, ''), $4) RETURNING id)
UPDATE contactos SET score = greatest(score, $5::int), estado = CASE WHEN $6 = 'compra' THEN 'caliente' WHEN $6 = 'spam' THEN 'spam' ELSE estado END
WHERE id = $1::uuid RETURNING id
""", "={{ [$json.contacto_id, $json.entrante, $json.texto, $json.spam ? 'ignorado' : ($json.humano ? 'pendiente_humano' : 'respondido'), $json.score, $json.intencion] }}",
           (1540, 300)),
        code("Avisar al dueño", AVISO_TG + r"""
const out = [];
for (const it of $('Decidir respuesta').all()) {
  const d = it.json;
  const quien = (d.nombre ? d.nombre + ' · ' : '') + '+' + d.to;
  if (d.humano) out.push(...avisoTelegram('💬 WhatsApp que necesita a una persona (' + d.intencion + ', score ' + d.score + ')\nDe: ' + quien + '\nMotivo: ' + d.motivo + '\n\n«' + d.entrante.slice(0, 1200) + '»\n\nRespóndele en wa.me/' + d.to));
  else if (d.score >= 70) out.push(...avisoTelegram('🔥 Lead caliente por WhatsApp (score ' + d.score + '): ' + quien + '\n«' + d.entrante.slice(0, 300) + '»'));
}
return out;
""", (1760, 300)),
    ]
    c = enlazar(("Verificación de Meta", "Comprobar token"), ("Comprobar token", "Responder a Meta"),
                ("Mensaje entrante", "Verificar firma e interpretar"), ("Verificar firma e interpretar", "¿Es el dueño?"),
                ("¿Es el dueño?", "Entender orden", 0), ("¿Es el dueño?", "Contacto", 1),
                ("Entender orden", "¿Hay que interpretar?"),
                ("¿Hay que interpretar?", "Pedir a la IA", 0), ("¿Hay que interpretar?", "Preparar herramienta", 1),
                ("Pedir a la IA", "IA de control"), ("IA de control", "Leer intención"), ("Leer intención", "Preparar herramienta"),
                ("Preparar herramienta", "Ejecutar herramienta"), ("Ejecutar herramienta", "Redactar respuesta"),
                ("Redactar respuesta", "Contestar al dueño"),
                ("Contacto", "Encargo"), ("Encargo", "Agente de conversación"), ("Agente de conversación", "Decidir respuesta"),
                ("Decidir respuesta", "Responder al cliente"), ("Decidir respuesta", "Registrar conversación"),
                ("Registrar conversación", "Avisar al dueño"))
    con_avisos(n, c, "Avisar al dueño", 1980, 300)
    return flujo("WA01", "WA-01 WhatsApp (dueño y clientes)", n, c)


# ═════════════════════════════════════════════════════════════════════
# FÁBRICA DE CONTENIDO · imágenes, vídeos, webs, negocios y canales
# ═════════════════════════════════════════════════════════════════════
BASE_PUBLICA = "const BASE = String($env.WEBHOOK_URL || $env.N8N_EDITOR_BASE_URL || 'http://localhost:5678/').replace(/\\/$/, '');\n"


def sub(nombre, clave, pos, esperar=True, modo="each"):
    return nodo(nombre, "n8n-nodes-base.executeWorkflow", 1.1, {
        "source": "database", "workflowId": {"__rl": True, "value": ID[clave], "mode": "id"},
        "mode": modo, "options": {"waitForSubWorkflow": esperar}}, pos, onError="continueRegularOutput")


def http_json(nombre, pos, metodo="POST", **extra):
    """HTTP cuyo url, cabeceras y cuerpo vienen en $json.url / $json.cab / $json.cuerpo."""
    p = {"method": metodo, "url": "={{ $json.url }}", "sendHeaders": True, "specifyHeaders": "json",
         "jsonHeaders": "={{ JSON.stringify($json.cab || {}) }}", "options": {"timeout": 300000}}
    if metodo == "POST":
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.cuerpo || {}) }}"})
    return nodo(nombre, "n8n-nodes-base.httpRequest", 4.2, p, pos, **extra)


# ── GEN-01 · Generar imagen (post, portada o miniatura) ──────────────
def gen01():
    n = [
        nodo("Generar imagen", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Preparar", r"""
const prov = String($env.PROVEEDOR_IMAGEN || '').toLowerCase();
if (!prov) throw new Error('Configura PROVEEDOR_IMAGEN (cloudflare, openai o gemini) para generar imágenes');
return $input.all().map((it) => {
  const j = it.json;
  const tipo = ['post', 'portada', 'miniatura'].includes(j.tipo) ? j.tipo : 'post';
  const formato = ['cuadrado', 'vertical', 'horizontal'].includes(j.formato) ? j.formato
    : (tipo === 'miniatura' ? 'horizontal' : tipo === 'portada' ? 'vertical' : 'cuadrado');
  const estilo = $env.ESTILO_MARCA || 'Estética moderna y profesional; colores de marca azul profundo #0B3D91 y blanco con acentos amarillos; composición limpia y con mucho contraste.';
  const prompt = j.prompt ? String(j.prompt) : [
    tipo === 'miniatura' ? 'Miniatura de YouTube muy llamativa: sujeto grande y expresivo, alto contraste, fondo sencillo.'
      : tipo === 'portada' ? 'Portada impactante para un reel, short o la cabecera de un proyecto.'
      : 'Imagen para una publicación en redes sociales.',
    'Marca: ' + ($env.NOMBRE_NEGOCIO || 'EstrategIA Digital 3.0') + '.', estilo,
    j.tema ? 'Tema o petición: ' + String(j.tema).slice(0, 600) + '.' : '',
    j.texto_imagen ? 'Incluye este texto grande, bien escrito y legible: "' + String(j.texto_imagen).slice(0, 60) + '".' : 'Sin texto en la imagen.',
  ].filter(Boolean).join(' ');
  let url, cab, cuerpo;
  if (prov === 'openai') {
    if (!$env.OPENAI_API_KEY) throw new Error('Falta OPENAI_API_KEY');
    url = ($env.OPENAI_BASE_URL || 'https://api.openai.com') + '/v1/images/generations';
    cab = { Authorization: 'Bearer ' + $env.OPENAI_API_KEY };
    cuerpo = { model: $env.MODELO_IMAGEN || 'gpt-image-2', prompt, n: 1, output_format: 'jpeg',
      size: { cuadrado: '1024x1024', vertical: '1024x1536', horizontal: '1536x1024' }[formato] };
  } else if (prov === 'gemini') {
    if (!$env.GEMINI_API_KEY) throw new Error('Falta GEMINI_API_KEY');
    url = ($env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com') + '/v1beta/models/' + ($env.MODELO_IMAGEN || 'imagen-4.0-generate-001') + ':predict';
    cab = { 'x-goog-api-key': $env.GEMINI_API_KEY };
    cuerpo = { instances: [{ prompt }], parameters: { sampleCount: 1, aspectRatio: { cuadrado: '1:1', vertical: '9:16', horizontal: '16:9' }[formato] } };
  } else if (prov === 'cloudflare') {
    // Cloudflare Workers AI (FLUX): incluye una cuota diaria gratuita. La imagen sale cuadrada.
    if (!$env.CLOUDFLARE_ACCOUNT_ID || !$env.CLOUDFLARE_API_TOKEN) throw new Error('Faltan CLOUDFLARE_ACCOUNT_ID o CLOUDFLARE_API_TOKEN');
    url = 'https://api.cloudflare.com/client/v4/accounts/' + encodeURIComponent($env.CLOUDFLARE_ACCOUNT_ID) + '/ai/run/' + ($env.MODELO_IMAGEN || '@cf/black-forest-labs/flux-1-schnell');
    cab = { Authorization: 'Bearer ' + $env.CLOUDFLARE_API_TOKEN };
    cuerpo = { prompt: prompt.slice(0, 2000), steps: 8 };
  } else throw new Error('PROVEEDOR_IMAGEN no válido: ' + prov + ' (usa cloudflare, openai o gemini)');
  return { json: { url, cab, cuerpo, prompt, pieza_id: j.pieza_id || '' } };
});
""", (220, 0)),
        http_json("Generar", (440, 0), retryOnFail=True, maxTries=2, waitBetweenTries=5000),
        code("Extraer imagen", r"""
return $input.all().map((it, i) => {
  const r = it.json, p = $('Preparar').all()[i].json;
  const b64 = r.data?.[0]?.b64_json || r.predictions?.[0]?.bytesBase64Encoded || r.result?.image;
  if (!b64) throw new Error('El proveedor no devolvió imagen: ' + JSON.stringify(r).slice(0, 300));
  const mime = b64.startsWith('/9j/') ? 'image/jpeg' : b64.startsWith('iVBOR') ? 'image/png' : 'image/webp';
  return { json: { params: [b64, mime, p.prompt.slice(0, 2000), p.pieza_id] } };
});
""", (660, 0)),
        pg("Guardar medio", """
WITH m AS (INSERT INTO medios (tipo, mime, datos, prompt, pieza_id)
           VALUES ('imagen', $2, decode($1, 'base64'), $3, nullif($4, '')::uuid) RETURNING id, pieza_id)
SELECT id, pieza_id FROM m
""", "={{ $json.params }}", (880, 0)),
        code("Dirección pública", BASE_PUBLICA + r"""
return $input.all().map((it) => ({ json: { medio_id: it.json.id, pieza_id: it.json.pieza_id || '', url: BASE + '/webhook/medio?id=' + it.json.id, media_tipo: 'imagen' } }));
""", (1100, 0)),
        pg("Asignar a la pieza", "UPDATE piezas SET media_url = $1, actualizado_en = now() WHERE id = nullif($2, '')::uuid RETURNING id",
           "={{ [$json.url, $json.pieza_id] }}", (1320, 0), alwaysOutputData=True),
        code("Resultado", "return $('Dirección pública').all().map((it) => ({ json: it.json }));", (1540, 0)),
    ]
    c = enlazar(("Generar imagen", "Preparar"), ("Preparar", "Generar"), ("Generar", "Extraer imagen"),
                ("Extraer imagen", "Guardar medio"), ("Guardar medio", "Dirección pública"),
                ("Dirección pública", "Asignar a la pieza"), ("Asignar a la pieza", "Resultado"))
    return flujo("GEN01", "GEN-01 Generar imagen", n, c)


# ── GEN-02 · Generar vídeo con Veo (Gemini API) ──────────────────────
def gen02():
    n = [
        nodo("Generar vídeo", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Preparar", r"""
const j = $input.first().json;
const prov = String($env.PROVEEDOR_VIDEO || '').toLowerCase();
const horizontal = j.formato === 'horizontal';
const comun = { prov, prompt: String(j.prompt || ''), pieza_id: j.pieza_id || '', avisar: !!j.avisar, titulo: j.titulo || '' };
if (prov === 'gemini') {
  if (!$env.GEMINI_API_KEY) throw new Error('Falta GEMINI_API_KEY');
  const base = ($env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com') + '/v1beta/';
  return [{ json: Object.assign(comun, { base, url: base + 'models/' + ($env.MODELO_VIDEO || 'veo-3.1-generate-preview') + ':predictLongRunning',
    cab: { 'x-goog-api-key': $env.GEMINI_API_KEY },
    cuerpo: { instances: [{ prompt: comun.prompt.slice(0, 4000) }], parameters: { aspectRatio: horizontal ? '16:9' : '9:16' } } }) }];
}
if (prov === 'openai') {
  // Sora (API de vídeos de OpenAI). OpenAI anunció su retirada; si ya no está disponible, usa PROVEEDOR_VIDEO=gemini.
  if (!$env.OPENAI_API_KEY) throw new Error('Falta OPENAI_API_KEY');
  const base = ($env.OPENAI_BASE_URL || 'https://api.openai.com') + '/v1/videos';
  return [{ json: Object.assign(comun, { base, url: base, cab: { Authorization: 'Bearer ' + $env.OPENAI_API_KEY },
    modelo: $env.MODELO_VIDEO || 'sora-2', tamano: horizontal ? '1280x720' : '720x1280', segundos: String($env.SEGUNDOS_VIDEO || '8') }) }];
}
if (prov === 'montaje') {
  // Montaje gratuito: imágenes de Cloudflare + textos en pantalla, montado con ffmpeg en el propio servidor.
  const escenas = Array.isArray(j.escenas) && j.escenas.length ? j.escenas : null;
  return [{ json: Object.assign(comun, { formato: horizontal ? 'horizontal' : 'vertical', escenas, faltan: !escenas }) }];
}
throw new Error('Configura PROVEEDOR_VIDEO: montaje (gratis), gemini (Veo) u openai (Sora) para generar vídeos');
""", (220, 0)),
        si_campo("¿Montaje?", "prov", "montaje", (330, 300)),
        si_campo("¿Faltan escenas?", "faltan", True, (550, 300), operador="true", tipo="boolean"),
        code("Encargo de escenas", r"""
const p = $('Preparar').first().json;
return [{ json: { agente_id: 5, max_tokens: 1500, origen: 'GEN-02', input:
  'Convierte esto en un vídeo corto montado con imágenes (reel, short o TikTok) de 4 a 6 escenas. ' +
  'Responde SOLO JSON: {"escenas":[{"texto":"frase en pantalla en español de España, como mucho 9 palabras",' +
  '"imagen":"descripción en inglés de una imagen SIN texto: sujeto, escena, luz y estilo (foto o ilustración moderna)"}]}. ' +
  'La primera escena es un gancho que engancha en 2 segundos; la última, una llamada a la acción. Nada de marcas registradas ni personas reales.\n\n' + 'Petición o guion:\n' + String(p.prompt || p.titulo || '').slice(0, 3000) } }];
""", (770, 250)),
        llamar_agente("Guionista de escenas", (990, 250)),
        code("Trabajo de montaje", JSON_DE_TEXTO + r"""
const p = $('Preparar').first().json;
let escenas = p.escenas;
if (!escenas) escenas = jsonDeTexto($input.first().json.respuesta).escenas;
if (!Array.isArray(escenas) || !escenas.length) throw new Error('No hay escenas para montar el vídeo');
const trabajo = { escenas, formato: p.formato, pieza_id: p.pieza_id, prompt: p.prompt || p.titulo,
  cierre: $env.CIERRE_VIDEO || 'Síguenos para más ideas' };
// En base64 para pasarlo a la línea de órdenes sin problemas de comillas
return [{ json: { trabajo: Buffer.from(JSON.stringify(trabajo), 'utf8').toString('base64') } }];
""", (1210, 300)),
        nodo("Montar vídeo", "n8n-nodes-base.executeCommand", 1,
             {"command": "={{ \"node /opt/omni/montar.mjs '\" + $json.trabajo + \"'\" }}"}, (1430, 300)),
        code("Vídeo montado", r"""
const r0 = $input.first().json;
let r;
try { r = JSON.parse(String(r0.stdout || '').trim().split('\n').pop()); }
catch (e) { throw new Error('El montaje no devolvió resultado: ' + String(r0.stderr || r0.stdout || '').slice(0, 300)); }
if (!r.id) throw new Error('El montaje no guardó el vídeo');
return [{ json: { id: r.id } }];
""", (1650, 300)),
        si_campo("¿Sora?", "prov", "openai", (440, 0)),
        http_json("Lanzar", (440, 100)),
        nodo("Lanzar Sora", "n8n-nodes-base.httpRequest", 4.2, {
            "method": "POST", "url": "={{ $json.url }}", "sendHeaders": True, "specifyHeaders": "json",
            "jsonHeaders": "={{ JSON.stringify($json.cab) }}", "sendBody": True, "contentType": "multipart-form-data",
            "bodyParameters": {"parameters": [
                {"parameterType": "formData", "name": "model", "value": "={{ $json.modelo }}"},
                {"parameterType": "formData", "name": "prompt", "value": "={{ $json.prompt.slice(0, 4000) }}"},
                {"parameterType": "formData", "name": "size", "value": "={{ $json.tamano }}"},
                {"parameterType": "formData", "name": "seconds", "value": "={{ $json.segundos }}"}]},
            "options": {"timeout": 120000}}, (440, -100)),
        code("Operación", r"""
const r = $input.first().json;
const p = $('Preparar').first().json;
if (p.prov === 'openai') {
  if (!r.id) throw new Error('Sora no aceptó el vídeo: ' + JSON.stringify(r.error || r).slice(0, 300));
  return [{ json: { url: p.base + '/' + r.id, cab: p.cab } }];
}
if (!r.name) throw new Error('Veo no devolvió operación: ' + JSON.stringify(r).slice(0, 300));
return [{ json: { url: p.base + r.name, cab: p.cab } }];
""", (660, 0)),
        nodo("Esperar 20 s", "n8n-nodes-base.wait", 1.1, {"amount": 20, "unit": "seconds"}, (880, 0),
             webhookId="6f1d1c1e-0a00-4c00-9a00-000000001100"),
        http_json("Consultar", (1100, 0), metodo="GET"),
        code("¿Listo?", r"""
const r = $input.first().json;
const p = $('Operación').first().json;
const prov = $('Preparar').first().json.prov;
if (prov === 'openai') {
  if (r.status === 'failed') throw new Error('Sora: ' + (r.error?.message || 'el vídeo falló'));
  if (r.status !== 'completed') {
    if ($runIndex > 45) throw new Error('Sora tarda demasiado (más de 15 minutos)');
    return [{ json: { listo: false, url: p.url, cab: p.cab } }];
  }
  return [{ json: { listo: true, url: p.url + '/content', cab: p.cab } }];
}
if (r.error) throw new Error('Veo: ' + (r.error.message || JSON.stringify(r.error)));
if (!r.done) {
  if ($runIndex > 45) throw new Error('Veo tarda demasiado (más de 15 minutos)');
  return [{ json: { listo: false, url: p.url, cab: p.cab } }];
}
const uri = r.response?.generateVideoResponse?.generatedSamples?.[0]?.video?.uri;
if (!uri) throw new Error('Veo terminó sin vídeo (puede haberlo bloqueado su filtro de seguridad): ' + JSON.stringify(r.response || r).slice(0, 300));
return [{ json: { listo: true, url: uri, cab: p.cab } }];
""", (1320, 0)),
        si_campo("¿Terminado?", "listo", True, (1540, 0), operador="true", tipo="boolean"),
        nodo("Descargar", "n8n-nodes-base.httpRequest", 4.2, {
            "method": "GET", "url": "={{ $json.url }}", "sendHeaders": True, "specifyHeaders": "json",
            "jsonHeaders": "={{ JSON.stringify($json.cab) }}",
            "options": {"timeout": 300000, "response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}}},
            (1760, -100)),
        code("A base64", r"""
const buf = await this.helpers.getBinaryDataBuffer(0, 'data');
const p = $('Preparar').first().json;
return [{ json: { params: [buf.toString('base64'), 'video/mp4', p.prompt.slice(0, 2000), p.pieza_id] } }];
""", (1980, -100)),
        pg("Guardar medio", """
INSERT INTO medios (tipo, mime, datos, prompt, pieza_id) VALUES ('video', $2, decode($1, 'base64'), $3, nullif($4, '')::uuid) RETURNING id
""", "={{ $json.params }}", (2200, -100)),
        code("Dirección pública", BASE_PUBLICA + r"""
const p = $('Preparar').first().json;
const id = $input.first().json.id;
return [{ json: { medio_id: id, pieza_id: p.pieza_id, url: BASE + '/webhook/medio?id=' + id, media_tipo: 'video', avisar: p.avisar, titulo: p.titulo } }];
""", (2420, -100)),
        pg("Asignar a la pieza", "UPDATE piezas SET media_url = $1, actualizado_en = now() WHERE id = nullif($2, '')::uuid RETURNING id",
           "={{ [$json.url, $json.pieza_id] }}", (2640, -100), alwaysOutputData=True),
        code("Avisar si toca", AVISO_TG + r"""
const d = $('Dirección pública').first().json;
if (!d.avisar) return [];
return avisoTelegram('🎬 Vídeo listo' + (d.titulo ? ': ' + d.titulo : '') + '\n' + d.url).map((x) => ({ json: Object.assign(x.json, { media_url: d.url, media_tipo: 'video' }) }));
""", (2860, -250)),
        code("Resultado", "return $('Dirección pública').all().map((it) => ({ json: it.json }));", (2860, -100)),
    ]
    c = enlazar(("Generar vídeo", "Preparar"), ("Preparar", "¿Montaje?"), ("¿Montaje?", "¿Faltan escenas?", 0), ("¿Montaje?", "¿Sora?", 1),
                ("¿Faltan escenas?", "Encargo de escenas", 0), ("¿Faltan escenas?", "Trabajo de montaje", 1),
                ("Encargo de escenas", "Guionista de escenas"), ("Guionista de escenas", "Trabajo de montaje"),
                ("Trabajo de montaje", "Montar vídeo"), ("Montar vídeo", "Vídeo montado"), ("Vídeo montado", "Dirección pública"),
                ("¿Sora?", "Lanzar Sora", 0), ("¿Sora?", "Lanzar", 1),
                ("Lanzar Sora", "Operación"), ("Lanzar", "Operación"), ("Operación", "Esperar 20 s"),
                ("Esperar 20 s", "Consultar"), ("Consultar", "¿Listo?"), ("¿Listo?", "¿Terminado?"),
                ("¿Terminado?", "Descargar", 0), ("¿Terminado?", "Esperar 20 s", 1),
                ("Descargar", "A base64"), ("A base64", "Guardar medio"), ("Guardar medio", "Dirección pública"),
                ("Dirección pública", "Asignar a la pieza"),
                ("Asignar a la pieza", "Avisar si toca"), ("Asignar a la pieza", "Resultado"))
    con_avisos(n, c, "Avisar si toca", 3080, -250)
    return flujo("GEN02", "GEN-02 Generar vídeo (montaje, Veo u OpenAI)", n, c)


# ── GEN-03 · Crear una web (landing con formulario de captación) ─────
def gen03():
    n = [
        nodo("Crear web", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Encargo", BASE_PUBLICA + r"""
const j = $input.first().json;
const encargo = String(j.encargo || j.texto || '').trim();
if (!encargo) throw new Error('Falta el encargo de la web');
const slug = (String(j.slug || encargo).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'web')
  + (j.slug ? '' : '-' + Math.random().toString(36).slice(2, 6));
const input = 'Crea una landing page para este encargo:\n' + encargo + '\n\n' +
  (j.imagen_url ? 'Usa esta imagen de cabecera (etiqueta img con alt descriptivo): ' + j.imagen_url + '\n' : '') +
  'El formulario de contacto debe tener method="post", action="' + BASE + '/webhook/lead", campos con name="nombre", name="email", name="telefono", name="mensaje", ' +
  'un campo oculto name="web" value="' + slug + '" y un campo trampa anti-spam name="empresa_web" oculto con la clase "hidden". ' +
  'Incluye un pie con aviso legal y política de privacidad básicos (RGPD) y una casilla obligatoria de aceptación de la privacidad.';
return [{ json: { agente_id: 15, input, max_tokens: 8000, origen: 'GEN-03', _slug: slug, _titulo: String(j.titulo || encargo).slice(0, 120),
  _proyecto: j.proyecto_id || '', _avisar: !!j.avisar } }];
""", (220, 0)),
        llamar_agente("Diseñador web", (440, 0)),
        code("Limpiar HTML", r"""
const e = $('Encargo').first().json;
let html = String($input.first().json.respuesta || '').replace(/^```(?:html)?\s*/i, '').replace(/```\s*$/, '').trim();
const i = html.search(/<!doctype html|<html/i);
if (i < 0) throw new Error('El diseñador web no devolvió HTML');
html = html.slice(i);
const titulo = (html.match(/<title>([^<]*)<\/title>/i) || [])[1] || e._titulo;
return [{ json: { params: [e._slug, titulo.slice(0, 200), html, e._proyecto] } }];
""", (660, 0)),
        pg("Guardar web", """
INSERT INTO webs (slug, titulo, html, proyecto_id) VALUES ($1, $2, $3, nullif($4, '')::uuid)
ON CONFLICT (slug) DO UPDATE SET html = excluded.html, titulo = excluded.titulo, actualizado_en = now() RETURNING slug, titulo
""", "={{ $json.params }}", (880, 0)),
        code("Dirección pública", BASE_PUBLICA + r"""
const e = $('Encargo').first().json;
const w = $input.first().json;
return [{ json: { slug: w.slug, titulo: w.titulo, url: BASE + '/webhook/web?s=' + w.slug, avisar: e._avisar } }];
""", (1100, 0)),
        code("Avisar si toca", AVISO_TG + r"""
const d = $('Dirección pública').first().json;
return d.avisar ? avisoTelegram('🌐 Web publicada: ' + d.titulo + '\n' + d.url + '\n\nLos contactos del formulario te llegarán como leads.') : [];
""", (1320, -150)),
        code("Resultado", "return $('Dirección pública').all().map((it) => ({ json: it.json }));", (1320, 0)),
    ]
    c = enlazar(("Crear web", "Encargo"), ("Encargo", "Diseñador web"), ("Diseñador web", "Limpiar HTML"),
                ("Limpiar HTML", "Guardar web"), ("Guardar web", "Dirección pública"),
                ("Dirección pública", "Avisar si toca"), ("Dirección pública", "Resultado"))
    con_avisos(n, c, "Avisar si toca", 1540, -150)
    return flujo("GEN03", "GEN-03 Crear web", n, c)


# ── WEB-01 · Sirve imágenes, vídeos y webs, y recoge los formularios ─
def web01():
    def responder(nombre, pos, **p):
        return nodo(nombre, "n8n-nodes-base.respondToWebhook", 1.1, p, pos)
    n = [
        nodo("Medio", "n8n-nodes-base.webhook", 2, {"httpMethod": "GET", "path": "medio", "responseMode": "responseNode", "options": {}},
             (0, 0), webhookId="6f1d1c1e-0a00-4c00-9a00-000000001200"),
        pg("Leer medio", "SELECT encode(datos, 'base64') AS b64, mime FROM medios WHERE id::text = $1 LIMIT 1",
           "={{ [String($json.query.id || '').replace(/[^0-9a-f-]/gi, '').slice(0, 36)] }}", (220, 0), alwaysOutputData=True),
        code("A binario", r"""
const r = $input.first().json;
if (!r.b64) return [{ json: { encontrado: false } }];
const ext = r.mime.split('/')[1].replace('jpeg', 'jpg');
const bin = await this.helpers.prepareBinaryData(Buffer.from(r.b64, 'base64'), 'omniagent.' + ext, r.mime);
return [{ json: { encontrado: true }, binary: { data: bin } }];
""", (440, 0)),
        si_campo("¿Existe?", "encontrado", True, (660, 0), operador="true", tipo="boolean"),
        responder("Enviar archivo", (880, -80), respondWith="binary",
                  options={"responseHeaders": {"entries": [{"name": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}}),
        responder("No existe", (880, 80), respondWith="text", responseBody="No encontrado", options={"responseCode": 404}),

        nodo("Web", "n8n-nodes-base.webhook", 2, {"httpMethod": "GET", "path": "web", "responseMode": "responseNode", "options": {}},
             (0, 300), webhookId="6f1d1c1e-0a00-4c00-9a00-000000001300"),
        pg("Leer web", "UPDATE webs SET visitas = visitas + 1 WHERE slug = $1 RETURNING html",
           "={{ [String($json.query.s || '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 60)] }}", (220, 300), alwaysOutputData=True),
        responder("Enviar web", (440, 300), respondWith="text",
                  responseBody="={{ $json.html || '<!doctype html><meta charset=utf-8><title>No encontrada</title><p>Esta página no existe.</p>' }}",
                  options={"responseCode": "={{ $json.html ? 200 : 404 }}",
                           "responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}}),

        nodo("Formulario", "n8n-nodes-base.webhook", 2, {"httpMethod": "POST", "path": "lead", "responseMode": "responseNode", "options": {}},
             (0, 600), webhookId="6f1d1c1e-0a00-4c00-9a00-000000001400"),
        code("Limpiar datos", r"""
const b = $input.first().json.body || {};
const t = (v, n) => String(v || '').replace(/[<>]/g, '').trim().slice(0, n);
const email = t(b.email, 160).toLowerCase();
const d = { nombre: t(b.nombre, 120), email: /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) ? email : '', telefono: t(b.telefono, 30).replace(/[^\d+]/g, ''),
  mensaje: t(b.mensaje, 2000), web: t(b.web, 60), spam: !!String(b.empresa_web || '').trim() };
d.valido = !d.spam && !!(d.email || d.telefono);
return [{ json: d }];
""", (220, 600)),
        pg("Guardar lead", """
INSERT INTO contactos (email, nombre, telefono, origen, notas, score)
SELECT nullif($1, ''), nullif($2, ''), nullif($3, ''), 'web:' || $4, nullif($5, ''), 40 WHERE $6 = 'si'
ON CONFLICT DO NOTHING RETURNING id
""", "={{ [$json.email, $json.nombre, $json.telefono, $json.web, $json.mensaje, $json.valido ? 'si' : 'no'] }}", (440, 600), alwaysOutputData=True),
        responder("Gracias", (660, 520), respondWith="text",
                  responseBody="<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Gracias</title><body style='font-family:system-ui;display:grid;place-items:center;min-height:90vh;text-align:center'><div><h1>¡Gracias!</h1><p>Hemos recibido tu mensaje y te responderemos muy pronto.</p><p><a href='javascript:history.back()'>Volver</a></p></div></body></html>",
                  options={"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}}),
        code("Avisar del lead", AVISO_TG + r"""
const d = $('Limpiar datos').first().json;
if (!d.valido) return [];
return avisoTelegram('🧲 Nuevo lead desde la web «' + d.web + '»\n' + [d.nombre, d.email, d.telefono].filter(Boolean).join(' · ') + (d.mensaje ? '\n\n«' + d.mensaje.slice(0, 800) + '»' : ''));
""", (660, 680)),
    ]
    c = enlazar(("Medio", "Leer medio"), ("Leer medio", "A binario"), ("A binario", "¿Existe?"),
                ("¿Existe?", "Enviar archivo", 0), ("¿Existe?", "No existe", 1),
                ("Web", "Leer web"), ("Leer web", "Enviar web"),
                ("Formulario", "Limpiar datos"), ("Limpiar datos", "Guardar lead"),
                ("Guardar lead", "Gracias"), ("Guardar lead", "Avisar del lead"))
    con_avisos(n, c, "Avisar del lead", 880, 680)
    return flujo("WEB01", "WEB-01 Medios, webs y formularios", n, c)


# ── VID-01 · Fábrica de vídeo: guiones pendientes → vídeo con Veo ────
def vid01():
    n = [
        nodo("Cada 10 min", "n8n-nodes-base.scheduleTrigger", 1.2,
             {"rule": {"interval": [{"field": "minutes", "minutesInterval": 10}]}}, (0, 0)),
        code("¿Activada?", r"""
if (!['montaje', 'gemini', 'openai'].includes(String($env.PROVEEDOR_VIDEO || '').toLowerCase())) return [];
return [{ json: { max: parseInt($env.VIDEOS_POR_DIA || '1', 10) } }];
""", (220, 0)),
        pg("Elegir guion", """
UPDATE piezas SET estado = 'generando_video', intentos = intentos + 1, actualizado_en = now()
WHERE id = (SELECT id FROM piezas WHERE estado = 'requiere_video' AND media_url IS NULL AND intentos < 3
              AND NOT EXISTS (SELECT 1 FROM ajustes WHERE clave = 'pausa' AND valor = 'si')
              AND (SELECT count(*) FROM medios WHERE tipo = 'video' AND creado_en::date = current_date) < $1::int
            ORDER BY programado_para LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id, canal, formato, tema, brief
""", "={{ [$json.max] }}", (440, 0)),
        code("Encargo de prompt", r"""
const p = $input.first().json;
// Sin guion pendiente, Postgres devuelve {success: true}: no se genera nada (Veo cuesta dinero).
if (!p.id) return [];
if (String($env.PROVEEDOR_VIDEO || '').toLowerCase() === 'montaje') return [{ json: { agente_id: 5, max_tokens: 1500, origen: 'VID-01', input:
  'Convierte esto en un vídeo corto montado con imágenes (reel, short o TikTok) de 4 a 6 escenas. ' +
  'Responde SOLO JSON: {"escenas":[{"texto":"frase en pantalla en español de España, como mucho 9 palabras",' +
  '"imagen":"descripción en inglés de una imagen SIN texto: sujeto, escena, luz y estilo (foto o ilustración moderna)"}]}. ' +
  'La primera escena es un gancho que engancha en 2 segundos; la última, una llamada a la acción. Nada de marcas registradas ni personas reales.\n\n' + 'Tema: ' + (p.tema || '') + '\nGuion:\n' + String(p.brief || '').slice(0, 3000) } }];
return [{ json: { agente_id: 5, max_tokens: 900, origen: 'VID-01', input:
  'Convierte este guion en UN prompt para un generador de vídeo con IA (Veo o Sora): un vídeo vertical de 8 segundos con audio. ' +
  'Escribe el prompt en inglés, describiendo el plano, el sujeto, el movimiento de cámara, la luz y el estilo (moderno, profesional, colores azul y blanco). ' +
  'Incluye la locución en español de España entre comillas como lo que dice el narrador (como mucho 20 palabras). Nada de marcas registradas ni personas reales. ' +
  'Responde SOLO con el prompt.\n\nTema: ' + (p.tema || '') + '\nGuion:\n' + String(p.brief || '').slice(0, 3000) } }];
""", (660, 0)),
        llamar_agente("Agente de vídeo", (880, 0)),
        code("Pedido de vídeo", JSON_DE_TEXTO + r"""
const p = $('Elegir guion').first().json;
const respuesta = String($input.first().json.respuesta || '').trim();
if (String($env.PROVEEDOR_VIDEO || '').toLowerCase() === 'montaje') {
  let escenas = null;
  try { escenas = jsonDeTexto(respuesta).escenas; } catch (e) { /* GEN-02 las pedirá de nuevo */ }
  return [{ json: { prompt: String(p.brief || p.tema || ''), escenas, formato: 'vertical', pieza_id: p.id, avisar: false, titulo: p.tema } }];
}
return [{ json: { prompt: respuesta, formato: 'vertical', pieza_id: p.id, avisar: false, titulo: p.tema } }];
""", (1100, 0)),
        sub("Generar vídeo", "GEN02", (1320, 0)),
        code("Siguiente estado", r"""
const p = $('Elegir guion').first().json;
const r = $input.first().json;
if (r.error || !r.url) return [{ json: { params: [p.id, 'requiere_video', 'Vídeo no generado: ' + String(r.error?.message || r.error || 'sin respuesta').slice(0, 400)], p, url: '' } }];
// YouTube, Instagram y Facebook se publican solos; TikTok exige subida manual (su API pide auditoría de la app).
const estado = p.canal === 'tiktok' ? 'listo_manual' : 'en_cola';
return [{ json: { params: [p.id, estado, ''], p, url: r.url } }];
""", (1540, 0)),
        pg("Actualizar pieza", """
UPDATE piezas SET estado = $2, error = nullif($3, ''), programado_para = CASE WHEN $2 = 'en_cola' THEN least(programado_para, now()) ELSE programado_para END, actualizado_en = now()
WHERE id = $1::uuid RETURNING id, estado
""", "={{ $json.params }}", (1760, 0)),
        code("Aviso", AVISO_TG + r"""
const s = $('Siguiente estado').first().json;
const p = s.p;
if (!s.url) return avisoTelegram('⚠ No se pudo generar el vídeo «' + (p.tema || p.canal) + '»: ' + s.params[2]);
const txt = p.canal === 'tiktok'
  ? '🎬 Vídeo para TikTok listo: «' + (p.tema || '') + '». Descárgalo y súbelo desde la app de TikTok:\n' + s.url + '\n\nTexto sugerido:\n' + String(p.brief || '').slice(0, 600)
  : '🎬 Vídeo listo para ' + p.canal + ' («' + (p.tema || '') + '»). Se publicará automáticamente.\n' + s.url;
return avisoTelegram(txt).map((x) => ({ json: Object.assign(x.json, { media_url: s.url, media_tipo: 'video' }) }));
""", (1980, 0)),
    ]
    c = enlazar(("Cada 10 min", "¿Activada?"), ("¿Activada?", "Elegir guion"), ("Elegir guion", "Encargo de prompt"),
                ("Encargo de prompt", "Agente de vídeo"), ("Agente de vídeo", "Pedido de vídeo"), ("Pedido de vídeo", "Generar vídeo"),
                ("Generar vídeo", "Siguiente estado"), ("Siguiente estado", "Actualizar pieza"), ("Actualizar pieza", "Aviso"))
    con_avisos(n, c, "Aviso", 2200, 0)
    con_ejecutar_ahora(n, c, "¿Activada?")
    return flujo("VID01", "VID-01 Fábrica de vídeo", n, c)


# ── NEG-01 · Crear un negocio o un canal automatizado completo ───────
def neg01():
    n = [
        nodo("Crear negocio o canal", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        code("Encargo", r"""
const j = $input.first().json;
const idea = String(j.texto || '').trim();
if (!idea) throw new Error('Describe el negocio o canal que quieres crear');
const tipo = j.tipo === 'canal' || /\bcanal\b/i.test(idea) ? 'canal' : 'negocio';
const canales = String($env.CANALES_ACTIVOS || 'facebook,instagram,linkedin,x,tiktok,youtube').split(',').map((s) => s.trim()).filter(Boolean);
const input = 'Diseña un ' + (tipo === 'canal' ? 'canal de contenido automatizado (faceless)' : 'negocio digital') + ' a partir de esta idea: «' + idea + '».\n' +
  'Canales disponibles: ' + canales.join(', ') + '.\n' +
  'Responde SOLO JSON con esta forma: {"nombre":"","slug":"nombre-corto-sin-espacios","nicho":"","publico":"","propuesta":"una frase","oferta":{"producto":"","precio":"","formato":""},' +
  '"pilares":["",""],"canales":[""],"encargo_web":"brief detallado de la landing: secciones, textos clave, oferta y llamada a la acción","portada":"descripción visual de la portada de marca",' +
  '"piezas":[{"canal":"","formato":"post|carrusel|hilo|reel|short","tema":"","texto":"texto final o guion","hashtags":"","texto_imagen":"máx 6 palabras","publicar_en_dias":0}]}\n' +
  'Incluye 7 piezas (una por día, de 0 a 6) repartidas entre los canales. Para tiktok, youtube y los reels, el texto es un guion de 30-45 s con [TEXTO EN PANTALLA] y [VOZ]. Para X, si es un hilo, separa los tuits con una línea ---.';
return [{ json: { agente_id: 16, input, max_tokens: 8000, origen: 'NEG-01', _tipo: tipo, _idea: idea, _canales: canales } }];
""", (220, 0)),
        llamar_agente("Creador de negocios", (440, 0)),
        code("Plan", JSON_DE_TEXTO + r"""
const e = $('Encargo').first().json;
const plan = jsonDeTexto($input.first().json.respuesta);
plan.slug = String(plan.slug || plan.nombre || 'proyecto').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 32) + '-' + Math.random().toString(36).slice(2, 6);
plan.piezas = (plan.piezas || []).filter((p) => e._canales.includes(String(p.canal || '').toLowerCase()) && String(p.texto || '').trim()).slice(0, 10);
return [{ json: { plan, params: [String(plan.nombre || e._idea).slice(0, 120), e._tipo, String(plan.nicho || '').slice(0, 200), JSON.stringify(plan), plan.slug] } }];
""", (660, 0)),
        pg("Guardar proyecto", """
INSERT INTO proyectos (nombre, tipo, nicho, plan, web_slug) VALUES ($1, $2, $3, $4::jsonb, $5) RETURNING id
""", "={{ $json.params }}", (880, 0)),
        code("Pedido de portada", r"""
const plan = $('Plan').first().json.plan;
return [{ json: { tipo: 'portada', formato: 'horizontal', tema: (plan.nombre || '') + '. ' + (plan.portada || plan.propuesta || ''), texto_imagen: String(plan.nombre || '').slice(0, 40) } }];
""", (1100, 0)),
        sub("Portada", "GEN01", (1320, 0)),
        code("Pedido de web", r"""
const plan = $('Plan').first().json.plan;
const proyecto = $('Guardar proyecto').first().json.id;
const portada = $input.first().json.url || '';
return [{ json: { encargo: 'Negocio: ' + plan.nombre + '\nPropuesta: ' + (plan.propuesta || '') + '\nPúblico: ' + (plan.publico || '') +
  '\nOferta: ' + JSON.stringify(plan.oferta || {}) + '\n\n' + (plan.encargo_web || ''), slug: plan.slug, titulo: plan.nombre, proyecto_id: proyecto, imagen_url: portada, avisar: false } }];
""", (1540, 0)),
        sub("Web", "GEN03", (1760, 0)),
        code("Piezas del calendario", r"""
const plan = $('Plan').first().json.plan;
const proyecto = $('Guardar proyecto').first().json.id;
const ahora = Date.now();
return plan.piezas.map((p) => {
  const canal = String(p.canal).toLowerCase();
  const video = canal === 'tiktok' || canal === 'youtube' || (canal === 'instagram' && /reel|short|video/i.test(p.formato || ''));
  const dias = Math.max(0, Math.min(30, Number(p.publicar_en_dias) || 0));
  return { json: { params: [canal, String(p.texto).trim(), String(p.hashtags || ''), video ? 'requiere_video' : 'pendiente_aprobacion',
    new Date(ahora + dias * 86400e3 + 3600e3).toISOString(), String(p.formato || 'post'), String(p.tema || '').slice(0, 200), String(p.texto_imagen || '').slice(0, 60), proyecto] } };
});
""", (1980, 0)),
        pg("Guardar piezas", """
INSERT INTO piezas (canal, brief, hashtags, estado, programado_para, formato, tema, texto_imagen, proyecto_id)
VALUES ($1, $2, $3, $4, $5::timestamptz, $6, $7, nullif($8, ''), $9::uuid) RETURNING id
""", "={{ $json.params }}", (2200, 0)),
        code("Informe", AVISO_TG + BASE_PUBLICA + r"""
const plan = $('Plan').first().json.plan;
const portada = $('Portada').first().json.url || '';
const web = $('Web').first().json.url || '';
const n = $input.all().length;
const texto = '🚀 ' + ($('Encargo').first().json._tipo === 'canal' ? 'Canal' : 'Negocio') + ' creado: *' + plan.nombre + '*\n' +
  (plan.propuesta ? '💡 ' + plan.propuesta + '\n' : '') + (plan.publico ? '👥 ' + plan.publico + '\n' : '') +
  (plan.oferta?.producto ? '🛒 ' + plan.oferta.producto + (plan.oferta.precio ? ' · ' + plan.oferta.precio : '') + '\n' : '') +
  (plan.pilares?.length ? '🧱 Pilares: ' + plan.pilares.join(' · ') + '\n' : '') +
  (web ? '🌐 Web: ' + web + '\n' : '⚠ La web no se pudo crear\n') + (portada ? '🖼 Portada: ' + portada + '\n' : '') +
  '📅 ' + n + ' piezas preparadas para la primera semana: las de texto esperan tu aprobación y los vídeos se generarán solos.';
return avisoTelegram(texto).map((x) => ({ json: Object.assign(x.json, portada ? { media_url: portada, media_tipo: 'imagen' } : {}) }));
""", (2420, 0)),
    ]
    c = enlazar(("Crear negocio o canal", "Encargo"), ("Encargo", "Creador de negocios"), ("Creador de negocios", "Plan"),
                ("Plan", "Guardar proyecto"), ("Guardar proyecto", "Pedido de portada"), ("Pedido de portada", "Portada"),
                ("Portada", "Pedido de web"), ("Pedido de web", "Web"), ("Web", "Piezas del calendario"),
                ("Piezas del calendario", "Guardar piezas"), ("Guardar piezas", "Informe"))
    con_avisos(n, c, "Informe", 2640, 0)
    return flujo("NEG01", "NEG-01 Crear negocio o canal", n, c)


# ── PUB-04 · Publicar vídeos en YouTube (Shorts) ─────────────────────
def pub04():
    n = [
        nodo("Desde el publicador", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, (0, 0)),
        nodo("Descargar vídeo", "n8n-nodes-base.httpRequest", 4.2, {
            "method": "GET", "url": "={{ $json.media_url }}",
            "options": {"timeout": 300000, "response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}}}, (240, 0)),
        nodo("YouTube", "n8n-nodes-base.youTube", 1, {
            "resource": "video", "operation": "upload",
            "title": "={{ ($('Desde el publicador').item.json.tema || $('Desde el publicador').item.json.texto.split('\\n')[0]).slice(0, 95) }}",
            "regionCode": "ES", "categoryId": "22", "binaryProperty": "data",
            "options": {"description": "={{ $('Desde el publicador').item.json.texto.slice(0, 4800) + '\\n\\n#Shorts' }}",
                        "privacyStatus": "public", "selfDeclaredMadeForKids": False, "defaultLanguage": "es"},
        }, (480, 0)),
    ]
    c = enlazar(("Desde el publicador", "Descargar vídeo"), ("Descargar vídeo", "YouTube"))
    return flujo("PUB04", "PUB-04 Publicar en YouTube", n, c)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    flujos = {
        "SYS-00-debugger-global.json": sys00(),
        "SYS-01-autorreparacion.json": sys01(),
        "SYS-20-api-control.json": sys20(),
        "AGT-00-ejecutar-agente.json": agt00(),
        "CNT-01-director-contenido.json": cnt01(),
        "PUB-01-publicador.json": pub01(),
        "TEL-01-telegram-dueno.json": tel01(),
        "MSG-01-emails-leads.json": msg01(),
        "RPT-01-resumen-diario.json": rpt01(),
        "PUB-02-linkedin.json": pub02(),
        "PUB-03-x.json": pub03(),
        "SYS-21-herramientas-ia.json": sys21(),
        "WA-01-whatsapp.json": wa01(),
        "WA-02-enviar-whatsapp.json": wa02(),
        "GEN-01-generar-imagen.json": gen01(),
        "GEN-02-generar-video.json": gen02(),
        "GEN-03-crear-web.json": gen03(),
        "WEB-01-medios-webs.json": web01(),
        "VID-01-fabrica-video.json": vid01(),
        "NEG-01-crear-negocio.json": neg01(),
        "PUB-04-youtube.json": pub04(),
        "MCP-01-servidor-mcp.json": mcp01(),
    }
    for nombre, wf in flujos.items():
        (SALIDA / nombre).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("✔", nombre, "·", len(wf["nodes"]), "nodos")


if __name__ == "__main__":
    main()
