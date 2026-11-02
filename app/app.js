/* OmniAgent Control — centro de mando de OmniAgent OS.
 * Modo DEMO: datos de ejemplo en memoria, para ver la app sin servidor.
 * Modo conectado: todas las acciones van a UN webhook de n8n (flujo SYS-20 API de control),
 * con POST {accion, datos} y cabecera Authorization: Bearer <token>. Ver n8n/SYS-20-api-control.json.
 */
(function () {
  'use strict';

  // ─── Ajustes (solo en este navegador) ────────────────────────────────
  const KEY = 'omniagent-control-ajustes';
  function leerAjustes() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
  function guardarAjustes(a) { try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) { /* almacenamiento bloqueado */ } }
  let ajustes = Object.assign({ url: '', token: '', tema: 'auto', negocio: 'EstrategIA Digital 3.0' }, leerAjustes());
  const conectado = () => !!(ajustes.url && ajustes.token);
  // Enlace de conexión rápida: …/#conectar?u=<url>&t=<token> (el fragmento # nunca llega a ningún servidor).
  if (location.hash.startsWith('#conectar?')) {
    const q = new URLSearchParams(location.hash.slice('#conectar?'.length));
    if (q.get('u') && q.get('t')) { ajustes.url = q.get('u'); ajustes.token = q.get('t'); guardarAjustes(ajustes); }
    history.replaceState(null, '', location.pathname + '#panel');
  }
  const urlMcp = () => (ajustes.url || '').replace(/\/webhook\/omniagent-control\/?$/, '/mcp/omniagent');

  // ─── Datos de ejemplo (modo DEMO) ────────────────────────────────────
  const AGENTES = ['Director de prompts', 'Estrategia de negocio', 'Copywriting', 'Conversación humanizada', 'Visual', 'Vídeo y voz',
    'Productos formativos', 'Humanizador', 'Evaluador', 'Anuncios', 'SEO y blog', 'Marca faceless', 'Traducción', 'Analista de comunidad', 'Archivista'];
  const demo = {
    kpis: { leads_hoy: 14, leads_semana: 83, piezas_hoy: 9, publicadas_semana: 58, coste_ia_hoy: 3.42, presupuesto_ia: 5, ingresos_mes: 1870, ingresos_var: 12, cpl: 4.1, aprobaciones: 3, incidentes: 1 },
    actividad: [
      ['09:42', 'Publicado carrusel en Instagram · «5 automatizaciones con IA»', 'ok'],
      ['09:30', 'Lead cualificado (score 78) · origen: blog', 'info'],
      ['09:12', 'Reintento automático resuelto · token de LinkedIn renovado', 'warn'],
      ['08:55', 'Ciclo de contenido 06:00 completado · 3 piezas en cola', 'ok'],
      ['08:30', 'Resumen diario enviado a Telegram', 'info'],
    ],
    aprobaciones: [
      { id: 'p-101', canal: 'Instagram', formato: 'Carrusel', sensible: false, creado: 'hace 12 min', texto: 'Gancho: «Respondes los mismos WhatsApp 20 veces al día»\n1. Escribe tu base de respuestas\n2. Conecta un asistente que se presenta como IA\n3. Lo delicado pasa a una persona\nCTA: descarga la guía gratuita.' },
      { id: 'p-102', canal: 'LinkedIn', formato: 'Post', sensible: true, creado: 'hace 40 min', texto: 'El Reglamento europeo de IA ya exige transparencia en chatbots desde agosto de 2026. Qué significa para tu pyme en 3 puntos…' },
      { id: 'p-103', canal: 'Blog', formato: 'Artículo', sensible: false, creado: 'hace 1 h', texto: 'Título: Cómo calcular cuánto te ahorra la IA (con plantilla gratis)\nMeta: Fórmula, ejemplo y calculadora para medir el retorno real de la IA en tu negocio.' },
    ],
    agentes: AGENTES.map((n, i) => ({ id: i, nombre: n, version: 'v' + (1 + (i * 7) % 4) + '.' + (i % 3), puntuacion: (7.2 + ((i * 13) % 25) / 10).toFixed(1), ejecuciones_7d: 20 + (i * 37) % 140, coste_7d: (0.4 + ((i * 17) % 50) / 10).toFixed(2), estado: i === 5 ? 'candidata en prueba' : 'activo' })),
    flujos: [
      ['SYS-00 Debugger global', true, 'hace 2 h', 'ok'], ['SYS-01 Cola de reintentos', true, 'hace 1 min', 'ok'], ['SYS-03 Router de Telegram', true, 'hace 5 min', 'ok'],
      ['CNT-01 Orquestador de ciclo', true, '06:00', 'ok'], ['CNT-02 Tendencias', true, '06:01', 'ok'], ['CNT-05 QA y regeneración', true, '06:14', 'ok'],
      ['DST-01 Ventanas de publicación', true, '09:42', 'ok'], ['DST-02 Métricas', true, '09:00', 'ok'], ['CRM-02 Typebot', true, '09:30', 'ok'],
      ['CRM-04 Nurturing y reactivación', true, '08:00', 'ok'], ['RGL-00 Webhook de regalos', true, 'ayer', 'ok'], ['MET-01 Ingesta diaria', true, '06:00', 'error'],
      ['ARC-02 Procesar archivo', true, 'hace 20 min', 'ok'], ['CNT-07 Pico de tendencia', false, '—', 'pausado'],
    ].map((f, i) => ({ id: 'wf-' + i, nombre: f[0], activo: f[1], ultima: f[2], estado: f[3] })),
    archivos: [
      { nombre: '2026-10-30_contenido_interno_carrusel_automatizaciones_v01.png', ruta: '/02_Contenido/publicado/2026-10', tipo: 'imagen', fecha: '30/10/2026' },
      { nombre: '2026-10-29_regalos_interno_ebook_tu-negocio-con-ia_v03.pdf', ruta: '/04_Regalos', tipo: 'pdf', fecha: '29/10/2026' },
      { nombre: '2026-10-28_sistema_interno_prompts_evaluador_v07.md', ruta: '/11_Sistema', tipo: 'texto', fecha: '28/10/2026' },
      { nombre: '2026-10-27_marca_interno_paleta-colores_v02.svg', ruta: '/01_Marca', tipo: 'imagen', fecha: '27/10/2026' },
      { nombre: '2026-10-25_informes_interno_semanal-kpi_v01.pdf', ruta: '/10_Informes', tipo: 'pdf', fecha: '25/10/2026' },
    ],
    incidentes: [
      { id: 'i-7', workflow: 'MET-01 Ingesta diaria', nodo: 'Meta Ads API', error: '429 límite de peticiones', autorreparado: false, intentos: 3, cuando: 'hoy 06:04' },
      { id: 'i-6', workflow: 'DST-1x Publicar en LinkedIn', nodo: 'LinkedIn', error: 'Token caducado', autorreparado: true, intentos: 1, cuando: 'hoy 09:12' },
    ],
    leads: [
      { id: 'l-1', nombre: 'Lead #1042', score: 78, estado: 'cualificado', origen: 'blog', fecha: 'hoy' },
      { id: 'l-2', nombre: 'Lead #1041', score: 52, estado: 'nurturing día 3', origen: 'Instagram', fecha: 'hoy' },
      { id: 'l-3', nombre: 'Lead #1040', score: 91, estado: 'checkout iniciado', origen: 'Telegram', fecha: 'ayer' },
      { id: 'l-4', nombre: 'Lead #1037', score: 34, estado: 'frío (30 días)', origen: 'LinkedIn', fecha: 'hace 31 días' },
    ],
    chat: [{ yo: false, t: 'Hola. Soy el Director de OmniAgent. Puedes pedirme cosas como «prepara 3 posts sobre automatizaciones para mañana» o «pausa el disparo por tendencias».' }],
  };

  // ─── Capa de datos ───────────────────────────────────────────────────
  async function api(accion, datos) {
    if (!conectado()) return demoApi(accion, datos || {});
    const ctl = new AbortController(); const tm = setTimeout(() => ctl.abort(), 20000);
    let r;
    try { r = await fetch(ajustes.url, {
      method: 'POST', signal: ctl.signal,
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + ajustes.token },
      body: JSON.stringify({ accion, datos: datos || {} }),
    }); } catch (e) { throw new Error(e.name === 'AbortError' ? 'El servidor tarda demasiado en responder.' : 'Sin conexión con el servidor (revisa la URL, CORS o tu red).'); } finally { clearTimeout(tm); }
    if (!r.ok) throw new Error('El servidor respondió ' + r.status + '. Revisa la URL y el token en Ajustes.');
    return r.json();
  }

  function demoApi(accion, d) {
    const ok = (x) => Promise.resolve(JSON.parse(JSON.stringify(x)));
    switch (accion) {
      case 'resumen': return ok({ kpis: demo.kpis, actividad: demo.actividad });
      case 'aprobaciones': return ok(demo.aprobaciones);
      case 'decidir':
        demo.aprobaciones = demo.aprobaciones.filter((p) => p.id !== d.id);
        demo.kpis.aprobaciones = demo.aprobaciones.length;
        return ok({ ok: true });
      case 'agentes': return ok(demo.agentes);
      case 'agente_ejecutar': return ok({ respuesta: '(DEMO) El agente «' + AGENTES[d.agente_id] + '» habría recibido: ' + d.input });
      case 'flujos': return ok(demo.flujos);
      case 'flujo_activar': demo.flujos.forEach((f) => { if (f.id === d.id) { f.activo = d.activo; f.estado = d.activo ? 'ok' : 'pausado'; } }); return ok({ ok: true });
      case 'archivos': return ok(demo.archivos.filter((a) => !d.q || (a.nombre + a.ruta).toLowerCase().includes(d.q.toLowerCase())));
      case 'incidentes': return ok(demo.incidentes);
      case 'incidente_reintentar': demo.incidentes.forEach((i) => { if (i.id === d.id) { i.autorreparado = true; } }); demo.kpis.incidentes = demo.incidentes.filter((i) => !i.autorreparado).length; return ok({ ok: true });
      case 'leads': return ok(demo.leads);
      case 'crear': return ok({ respuesta: '(DEMO) Con el sistema conectado, aquí se crearía: ' + d.tipo + ' · «' + d.texto + '». Las imágenes salen al momento; los vídeos, webs y negocios te llegan por WhatsApp al terminar.' });
      case 'medios': return ok([]);
      case 'orden': return ok({ respuesta: '(DEMO) Recibido: «' + d.texto + '». Con el sistema conectado, el Director lo convertiría en tareas y te pediría aprobación en Aprobar.' });
      default: return Promise.reject(new Error('Acción desconocida: ' + accion));
    }
  }

  // ─── Utilidades de interfaz ──────────────────────────────────────────
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const eur = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
  let toastT;
  function toast(t) { const el = $('#toast'); el.textContent = t; el.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove('on'), 2400); }
  const vista = $('#vista');
  function pintar(html) { vista.innerHTML = html; }
  function error(e) { pintar('<div class="empty">⚠ ' + esc(e.message || e) + '</div>'); }
  function estadoPill(s) {
    const m = { ok: 'ok', error: 'bad', pausado: 'warn', activo: 'ok' };
    return '<span class="pill ' + (m[s] || 'info') + '">' + esc(s) + '</span>';
  }

  // ─── Vistas ──────────────────────────────────────────────────────────
  const V = {};

  V.panel = async () => {
    const { kpis: k, actividad } = await api('resumen');
    const pct = Math.min(100, Math.round((k.coste_ia_hoy / k.presupuesto_ia) * 100));
    pintar(`<h1>Panel</h1><p class="sub">${esc(ajustes.negocio)} · estado general del sistema</p>
    <div class="grid">
      <div class="card kpi"><div class="l">Leads hoy</div><div class="v">${k.leads_hoy}</div><div class="d">${k.leads_semana} esta semana</div></div>
      <div class="card kpi"><div class="l">Piezas generadas hoy</div><div class="v">${k.piezas_hoy}</div><div class="d">${k.publicadas_semana} publicadas esta semana</div></div>
      <div class="card kpi"><div class="l">Ingresos del mes</div><div class="v">${eur.format(k.ingresos_mes)}</div><div class="d ${k.ingresos_var >= 0 ? 'up' : 'down'}">${k.ingresos_var >= 0 ? '▲' : '▼'} ${Math.abs(k.ingresos_var)} % vs mes anterior</div></div>
      <div class="card kpi"><div class="l">Coste de IA hoy</div><div class="v">${eur.format(k.coste_ia_hoy)}</div><div class="d">${pct} % de ${eur.format(k.presupuesto_ia)}</div><div class="bar"><i style="width:${pct}%"></i></div></div>
      <div class="card kpi"><div class="l">CPL medio</div><div class="v">${eur.format(k.cpl)}</div><div class="d">coste por lead</div></div>
      <div class="card kpi"><div class="l">Pendiente de ti</div><div class="v">${k.aprobaciones + k.incidentes}</div><div class="d"><a href="#aprobaciones">${k.aprobaciones} aprobaciones</a> · <a href="#incidentes">${k.incidentes} incidentes</a></div></div>
    </div>
    <h2>Actividad reciente</h2><div class="list">${actividad.map((a) => `<div class="row"><span class="mono">${esc(a[0])}</span><div class="main"><div>${esc(a[1])}</div></div>${estadoPill(a[2] === 'warn' ? 'autorreparado' : a[2] === 'info' ? 'info' : 'ok')}</div>`).join('')}</div>`);
    badges(k);
  };

  V.aprobaciones = async () => {
    const lista = await api('aprobaciones');
    pintar(`<h1>Aprobaciones</h1><p class="sub">Piezas que esperan tu decisión antes de publicarse.</p>
    ${lista.length ? '<div class="list">' + lista.map((p) => `<div class="row" data-id="${esc(p.id)}"><div class="main">
      <div class="t">${esc(p.canal)} · ${esc(p.formato)} ${p.sensible ? '<span class="pill warn">sensible</span>' : ''}</div>
      <div class="m">${esc(p.creado)}</div><div class="preview">${esc(p.texto)}</div></div>
      <div class="acts"><button class="btn ok" data-d="aprobar">Aprobar</button><button class="btn" data-d="cambiar">Pedir cambios</button><button class="btn bad" data-d="descartar">Descartar</button></div></div>`).join('') + '</div>'
      : '<div class="empty">No hay nada pendiente. El sistema te avisará por Telegram cuando llegue algo.</div>'}`);
    vista.querySelectorAll('[data-d]').forEach((b) => b.addEventListener('click', async () => {
      const row = b.closest('.row');
      const id = row.dataset.id;
      let comentario = '';
      if (b.dataset.d === 'cambiar') {
        if (!row.querySelector('textarea')) {
          row.querySelector('.main').insertAdjacentHTML('beforeend', '<label class="f" for="c-' + id + '">¿Qué cambio quieres?</label><textarea id="c-' + id + '" rows="2"></textarea>');
          b.textContent = 'Enviar cambios';
          row.querySelector('textarea').focus();
          return;
        }
        comentario = row.querySelector('textarea').value.trim();
        if (!comentario) { toast('Escribe qué cambio quieres'); return; }
      }
      b.disabled = true;
      try { await api('decidir', { id, decision: b.dataset.d, comentario }); } catch (e) { b.disabled = false; toast('No se pudo: ' + e.message); return; }
      toast(b.dataset.d === 'aprobar' ? 'Aprobada: pasa a la cola' : b.dataset.d === 'cambiar' ? 'Cambios enviados al Evaluador' : 'Descartada');
      V.aprobaciones();
    }));
  };

  V.agentes = async () => {
    const lista = await api('agentes');
    pintar(`<h1>Agentes</h1><p class="sub">Los 15 agentes, su versión de prompt, puntuación del Evaluador y coste de los últimos 7 días.</p>
    <div class="tablewrap"><table><thead><tr><th>#</th><th>Agente</th><th>Prompt</th><th>Puntuación</th><th>Ejecuciones 7 d</th><th>Coste 7 d</th><th>Estado</th><th></th></tr></thead><tbody>
    ${lista.map((a) => `<tr><td class="mono">${a.id}</td><td><b>${esc(a.nombre)}</b></td><td class="mono">${esc(a.version)}</td><td>${esc(a.puntuacion)}</td><td>${a.ejecuciones_7d}</td><td>${eur.format(a.coste_7d)}</td><td>${estadoPill(a.estado)}</td><td><button class="btn" data-a="${a.id}">Probar</button></td></tr>`).join('')}
    </tbody></table></div><div id="prueba"></div>`);
    vista.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => {
      const id = +b.dataset.a;
      $('#prueba').innerHTML = `<h2>Probar: ${esc(lista.find((a) => a.id === id).nombre)}</h2><div class="card"><label class="f" for="pi">Entrada</label><textarea id="pi" rows="3" placeholder="Ej.: tema «automatizaciones para clínicas»"></textarea>
        <p><button class="btn pri" id="pe">Ejecutar</button></p><div id="pr" class="preview" hidden></div></div>`;
      $('#pi').focus();
      $('#pe').addEventListener('click', async () => {
        const pe = $('#pe'); pe.disabled = true; pe.textContent = 'Ejecutando…';
        let r; try { r = await api('agente_ejecutar', { agente_id: id, input: $('#pi').value }); } catch (e) { toast('No se pudo: ' + e.message); return; } finally { pe.disabled = false; pe.textContent = 'Ejecutar'; }
        const out = $('#pr'); out.hidden = false; out.textContent = typeof r.respuesta === 'string' ? r.respuesta : JSON.stringify(r.respuesta, null, 2);
      });
    }));
  };

  V.flujos = async () => {
    const lista = await api('flujos');
    pintar(`<h1>Flujos</h1><p class="sub">Workflows de n8n: actívalos o páusalos desde aquí.</p><div class="list">
    ${lista.map((f) => `<div class="row"><div class="main"><div class="t">${esc(f.nombre)}</div><div class="m">Última ejecución: ${esc(f.ultima)}</div></div>
      ${estadoPill(f.estado)}<label class="switch" title="${f.activo ? 'Pausar' : 'Activar'}"><input type="checkbox" data-f="${esc(f.id)}" ${f.activo ? 'checked' : ''} aria-label="Activar ${esc(f.nombre)}"><span></span></label></div>`).join('')}</div>`);
    vista.querySelectorAll('[data-f]').forEach((c) => c.addEventListener('change', async () => {
      try { await api('flujo_activar', { id: c.dataset.f, activo: c.checked }); } catch (e) { c.checked = !c.checked; toast('No se pudo: ' + e.message); return; }
      toast(c.checked ? 'Flujo activado' : 'Flujo pausado');
      V.flujos();
    }));
  };

  V.archivos = async (q) => {
    const lista = await api('archivos', { q: q || '' });
    pintar(`<h1>Archivos</h1><p class="sub">Busca en el archivo del sistema (MinIO, Drive y Dropbox indexados).</p>
    <input type="search" id="q" placeholder="Buscar por nombre, carpeta o contenido…" value="${esc(q || '')}" aria-label="Buscar archivos">
    <div class="list" style="margin-top:12px">${lista.length ? lista.map((a) => `<div class="row"><span class="pill info">${esc(a.tipo)}</span><div class="main"><div class="t mono">${esc(a.nombre)}</div><div class="m">${esc(a.ruta)} · ${esc(a.fecha)}</div></div>${a.url ? `<a class="btn" href="${esc(a.url)}" target="_blank" rel="noopener">Abrir</a>` : ''}</div>`).join('') : '<div class="empty">Sin resultados.</div>'}</div>`);
    const input = $('#q'); let t;
    input.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => V.archivos(input.value).then(() => { const n = $('#q'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }), 300); });
  };

  V.incidentes = async () => {
    const lista = await api('incidentes');
    pintar(`<h1>Incidentes</h1><p class="sub">Errores capturados por el debugger global. Los autorreparados quedan como registro.</p><div class="list">
    ${lista.length ? lista.map((i) => `<div class="row"><div class="main"><div class="t">${esc(i.workflow)} · <span class="mono">${esc(i.nodo)}</span></div><div class="m">${esc(i.error)} · ${esc(i.cuando)} · ${i.intentos} intentos</div></div>
      ${i.autorreparado ? estadoPill('autorreparado') : '<span class="pill bad">sin resolver</span><button class="btn pri" data-i="' + esc(i.id) + '">Reintentar</button>'}</div>`).join('') : '<div class="empty">Sin incidentes. Todo en orden.</div>'}</div>`);
    vista.querySelectorAll('[data-i]').forEach((b) => b.addEventListener('click', async () => { b.disabled = true; try { await api('incidente_reintentar', { id: b.dataset.i }); } catch (e) { b.disabled = false; toast('No se pudo: ' + e.message); return; } toast('Reintento lanzado'); V.incidentes(); }));
  };

  // ─── Crear: imágenes, vídeos, webs, negocios y canales ───────────────
  const TIPOS = [
    ['imagen', 'Imagen para post', 'Ej.: emprendedora usando IA en su tienda, texto «Ahorra 10 h a la semana»'],
    ['portada', 'Portada', 'Ej.: portada para un reel sobre automatizar WhatsApp'],
    ['miniatura', 'Miniatura de YouTube', 'Ej.: cara de sorpresa junto a un móvil, texto «IA GRATIS»'],
    ['video', 'Vídeo (short / reel)', 'Ej.: plano cenital de un café junto a un portátil; el narrador dice «la IA trabaja mientras tú descansas»'],
    ['web', 'Web (landing con formulario)', 'Ej.: landing para un taller online de IA para peluquerías, 49 €, plazas limitadas'],
    ['negocio', 'Negocio completo', 'Ej.: plantillas de Notion para autónomos'],
    ['canal', 'Canal automatizado', 'Ej.: canal faceless de recetas saludables en 15 minutos'],
  ];
  V.crear = async () => {
    pintar(`<h1>Crear</h1><p class="sub">Imágenes, portadas, miniaturas, vídeos, webs y negocios o canales completos con IA.</p>
    <form id="fc" class="card"><label class="f" for="ct">Qué quieres crear</label>
      <select id="ct">${TIPOS.map((t) => `<option value="${t[0]}">${esc(t[1])}</option>`).join('')}</select>
      <label class="f" for="cx">Descríbelo</label><textarea id="cx" rows="3"></textarea>
      <p><button class="btn pri" id="cb">Crear</button></p><div id="cr"></div></form>
    <div class="note">Las imágenes salen en unos segundos. Los vídeos (1-6 min), las webs (1-2 min) y los negocios o canales (2-4 min) te llegan por WhatsApp y Telegram al terminar, y aparecen abajo.</div>
    <h2>Tus creaciones</h2><div id="cg"><div class="empty">Cargando…</div></div>`);
    const ph = () => { $('#cx').placeholder = TIPOS.find((t) => t[0] === $('#ct').value)[2]; };
    $('#ct').addEventListener('change', ph); ph();
    $('#fc').addEventListener('submit', async (e) => {
      e.preventDefault();
      const texto = $('#cx').value.trim(); if (!texto) { toast('Describe lo que quieres crear'); return; }
      const b = $('#cb'); b.disabled = true; b.textContent = 'Creando…';
      let r; try { r = await api('crear', { tipo: $('#ct').value, texto }); } catch (err) { toast('No se pudo: ' + err.message); return; } finally { b.disabled = false; b.textContent = 'Crear'; }
      $('#cr').innerHTML = `<div class="preview">${esc(r.respuesta || '')}</div>` + (r.url && r.media_tipo === 'imagen' ? `<p><a href="${esc(r.url)}" target="_blank" rel="noopener"><img src="${esc(r.url)}" alt="Imagen generada" style="max-width:100%;border-radius:12px;margin-top:8px"></a></p>` : '');
      galeria();
    });
    galeria();
  };
  async function galeria() {
    let l; try { l = await api('medios'); } catch (e) { $('#cg').innerHTML = '<div class="empty">No se pudo cargar: ' + esc(e.message) + '</div>'; return; }
    if (!l.length) { $('#cg').innerHTML = '<div class="empty">Aún no hay creaciones.</div>'; return; }
    const icono = { imagen: '🖼', video: '🎬', web: '🌐', proyecto: '🚀' };
    $('#cg').innerHTML = '<div class="grid">' + l.map((m) => `<div class="card">
      ${m.tipo === 'imagen' ? `<a href="${esc(m.url)}" target="_blank" rel="noopener"><img src="${esc(m.url)}" alt="${esc(m.descripcion)}" loading="lazy" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px"></a>` : ''}
      ${m.tipo === 'video' ? `<video src="${esc(m.url)}" controls preload="none" playsinline style="width:100%;border-radius:10px;background:#000"></video>` : ''}
      <div class="m" style="margin-top:6px">${icono[m.tipo] || '•'} ${esc(m.tipo)} · ${esc(m.fecha)}</div>
      <div style="font-size:14px;overflow-wrap:anywhere">${esc(m.descripcion)}</div>
      ${m.url ? `<p style="margin:8px 0 0"><a class="btn" href="${esc(m.url)}" target="_blank" rel="noopener">Abrir</a></p>` : ''}</div>`).join('') + '</div>';
  }

  V.leads = async () => {
    const lista = await api('leads');
    pintar(`<h1>Leads</h1><p class="sub">Últimos contactos de la web, WhatsApp y el email, seudonimizados, con su puntuación.</p>
    <div class="tablewrap"><table><thead><tr><th>Lead</th><th>Score</th><th>Estado</th><th>Origen</th><th>Fecha</th></tr></thead><tbody>
    ${lista.map((l) => `<tr><td><b>${esc(l.nombre)}</b></td><td><span class="pill ${l.score >= 70 ? 'ok' : l.score >= 40 ? 'warn' : 'bad'}">${l.score}</span></td><td>${esc(l.estado)}</td><td>${esc(l.origen)}</td><td>${esc(l.fecha)}</td></tr>`).join('')}
    </tbody></table></div>`);
  };

  V.ordenes = async () => {
    pintar(`<h1>Órdenes</h1><p class="sub">Habla con el Director: lo que pidas se convierte en tareas y, si sale fuera, pasa por Aprobar.</p>
    <div class="chat" id="chat">${demo.chat.map((m) => `<div class="msg ${m.yo ? 'yo' : ''}">${esc(m.t)}</div>`).join('')}</div>
    <form id="fo" class="card"><label class="f" for="ot">Tu orden</label><textarea id="ot" rows="2" placeholder="Ej.: prepara 3 posts sobre el Reglamento de IA para la semana que viene"></textarea><p><button class="btn pri">Enviar</button></p></form>`);
    $('#fo').addEventListener('submit', async (e) => {
      e.preventDefault();
      const texto = $('#ot').value.trim(); if (!texto) return;
      demo.chat.push({ yo: true, t: texto }); $('#ot').value = '';
      let r; try { r = await api('orden', { texto }); } catch (e) { r = { respuesta: '⚠ No se pudo enviar: ' + e.message }; }
      demo.chat.push({ yo: false, t: typeof r.respuesta === 'string' ? r.respuesta : JSON.stringify(r.respuesta) });
      V.ordenes();
    });
  };

  V.ajustes = async () => {
    pintar(`<h1>Ajustes</h1><p class="sub">Conecta la app a tu servidor. Sin conexión funciona en modo DEMO con datos de ejemplo.</p>
    <form id="fa" class="card">
      <label class="f" for="an">Nombre del negocio</label><input type="text" id="an" value="${esc(ajustes.negocio)}">
      <label class="f" for="au">URL del webhook de control (n8n · SYS-20)</label><input type="url" id="au" placeholder="https://tu-servidor/webhook/omniagent-control" value="${esc(ajustes.url)}">
      <label class="f" for="at">Token de acceso</label><input type="password" id="at" autocomplete="off" value="${esc(ajustes.token)}">
      <label class="f" for="ae">Tema</label><select id="ae"><option value="auto">Automático</option><option value="dark">Oscuro</option><option value="light">Claro</option></select>
      <p style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn pri">Guardar</button><button class="btn" type="button" id="ap">Probar conexión</button><button class="btn bad" type="button" id="ad">Volver a DEMO</button></p>
    </form>
    <div class="note">El token se guarda solo en este dispositivo. Usa un token largo y aleatorio, distinto en cada dispositivo si puedes, y revócalo en n8n si pierdes el móvil. El servidor nunca debe aceptar peticiones sin token.</div>
    ${conectado() ? `<h2>Conectar otro dispositivo</h2><p class="sub">Abre este enlace en el móvil o la tablet y quedará conectado. Trátalo como una contraseña.</p>
    <p><button class="btn" type="button" id="ac">Copiar enlace de conexión</button></p>
    <h2>Dirigir el negocio desde Claude, ChatGPT o Gemini</h2>
    <p class="sub">Añade este servidor MCP como conector. Te pedirá entrar con tu usuario de n8n.</p>
    <div class="card"><code style="word-break:break-all">${esc(urlMcp())}</code></div>
    <p class="sub">Claude: Ajustes → Conectores → Añadir conector personalizado. ChatGPT: Ajustes → Aplicaciones y conectores → Crear (modo desarrollador). Gemini CLI: añádelo en <code>mcpServers</code> de settings.json.</p>` : ''}
    <h2>Instalar como app</h2><p class="sub">En Android o Chrome: menú ⋮ → «Instalar aplicación». En iPhone: Compartir → «Añadir a pantalla de inicio».</p>`);
    $('#ae').value = ajustes.tema;
    $('#fa').addEventListener('submit', (e) => {
      e.preventDefault();
      ajustes = Object.assign(ajustes, { negocio: $('#an').value.trim() || 'Mi negocio', url: $('#au').value.trim(), token: $('#at').value.trim(), tema: $('#ae').value });
      guardarAjustes(ajustes); aplicarTema(); modo(); toast('Ajustes guardados');
    });
    $('#ap').addEventListener('click', async () => {
      const prev = Object.assign({}, ajustes);
      ajustes.url = $('#au').value.trim(); ajustes.token = $('#at').value.trim();
      try { if (!conectado()) toast('Falta la URL o el token'); else { await api('resumen'); toast('Conexión correcta'); } } catch (e) { toast('No conecta: ' + e.message); }
      ajustes = prev;
    });
    const ac = $('#ac');
    if (ac) ac.addEventListener('click', async () => {
      const enlace = location.origin + location.pathname + '#conectar?u=' + encodeURIComponent(ajustes.url) + '&t=' + encodeURIComponent(ajustes.token);
      try { await navigator.clipboard.writeText(enlace); toast('Enlace copiado'); } catch (e) { prompt('Copia este enlace:', enlace); }
    });
    $('#ad').addEventListener('click', () => { ajustes.url = ''; ajustes.token = ''; guardarAjustes(ajustes); modo(); V.ajustes(); toast('Modo DEMO'); });
  };

  // ─── Navegación ──────────────────────────────────────────────────────
  function badges(k) { $('#badge-apr').textContent = k.aprobaciones || ''; $('#badge-inc').textContent = k.incidentes || ''; }
  function modo() { const m = $('#modo'); m.textContent = conectado() ? 'CONECTADO' : 'DEMO'; m.classList.toggle('real', conectado()); }
  function aplicarTema() { if (ajustes.tema === 'auto') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', ajustes.tema); }
  async function ir() {
    const v = (location.hash || '#panel').slice(1);
    const nombre = V[v] ? v : 'panel';
    document.querySelectorAll('#nav a').forEach((a) => a.classList.toggle('on', a.dataset.v === nombre));
    pintar('<div class="empty">Cargando…</div>');
    try { await V[nombre](); } catch (e) { error(e); }
    vista.focus({ preventScroll: true });
  }
  addEventListener('hashchange', ir);
  $('#refrescar').addEventListener('click', () => { ir(); toast('Actualizado'); });
  aplicarTema(); modo();
  api('resumen').then((r) => badges(r.kpis)).catch(() => {});
  ir();
  if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(() => {});
})();
