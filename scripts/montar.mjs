// OmniAgent OS · montaje gratuito de vídeo (reels, shorts, TikTok) sin IA de vídeo de pago.
// Uso: node montar.mjs <trabajo en base64>
//   trabajo = { escenas: [{ texto, imagen }], formato: 'vertical'|'horizontal', pieza_id, prompt, cierre }
// Cada escena: imagen generada con Cloudflare Workers AI (FLUX) + texto grande en pantalla.
// Al final, una tarjeta de cierre con la marca. Guarda el MP4 en la tabla «medios» y escribe {"id": ...}.
// Si una imagen no se puede generar, la escena usa un fondo de color de marca (el vídeo sale igualmente).
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const env = process.env;
const BASE = env.OMNI_DIR || '/opt/omni';
const FFMPEG = env.OMNI_FFMPEG || 'ffmpeg';
const FUENTE = env.OMNI_FUENTE || path.join(BASE, 'fuentes', 'DejaVuSans-Bold.ttf');
const AZUL = '0x0B3D91';

const trabajo = JSON.parse(Buffer.from(process.argv[2] || '', 'base64').toString('utf8') || '{}');
const vertical = trabajo.formato !== 'horizontal';
const [W, H] = vertical ? [720, 1280] : [1280, 720];
const SEG = Math.min(Math.max(parseFloat(env.SEGUNDOS_ESCENA || '4'), 2), 8);
const FPS = 30;
const escenas = (Array.isArray(trabajo.escenas) ? trabajo.escenas : [])
  .map((e) => ({ texto: String(e?.texto || '').trim().slice(0, 90), imagen: String(e?.imagen || '').trim().slice(0, 1500) }))
  .filter((e) => e.texto || e.imagen)
  .slice(0, 8);
if (!escenas.length) { console.error('El trabajo de montaje no trae escenas'); process.exit(1); }

const negocio = env.NOMBRE_NEGOCIO || 'EstrategIA Digital 3.0';
const cierre = String(trabajo.cierre || 'Síguenos para más ideas').slice(0, 60);

// Parte el texto en líneas para que quepa en pantalla.
function partir(texto, max) {
  const lineas = [];
  let actual = '';
  for (const palabra of texto.split(/\s+/).filter(Boolean)) {
    if ((actual + ' ' + palabra).trim().length > max && actual) { lineas.push(actual); actual = palabra; }
    else actual = (actual + ' ' + palabra).trim();
  }
  if (actual) lineas.push(actual);
  return lineas.slice(0, 4).join('\n');
}

async function imagenCloudflare(prompt, destino) {
  if (!env.CLOUDFLARE_ACCOUNT_ID || !env.CLOUDFLARE_API_TOKEN || !prompt) return false;
  const modelo = env.MODELO_IMAGEN_MONTAJE || '@cf/black-forest-labs/flux-1-schnell';
  const estilo = env.ESTILO_MARCA || 'modern, professional, deep blue #0B3D91 and white with yellow accents, clean composition, high contrast';
  try {
    const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(env.CLOUDFLARE_ACCOUNT_ID)}/ai/run/${modelo}`, {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + env.CLOUDFLARE_API_TOKEN, 'content-type': 'application/json' },
      body: JSON.stringify({ prompt: (prompt + '. ' + estilo + '. No text, no letters, no logos.').slice(0, 2000), steps: 8 }),
      signal: AbortSignal.timeout(120000),
    });
    const d = await r.json().catch(() => ({}));
    const b64 = d?.result?.image;
    if (!r.ok || !b64) { console.error('Cloudflare no devolvió imagen:', r.status, JSON.stringify(d?.errors || d).slice(0, 300)); return false; }
    fs.writeFileSync(destino, Buffer.from(b64, 'base64'));
    return true;
  } catch (e) {
    console.error('Fallo al pedir la imagen a Cloudflare:', e.message);
    return false;
  }
}

// Un solo hilo: el servidor tiene poca memoria y n8n ya ocupa la mayor parte.
function ff(args) {
  execFileSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', '-threads', '1', '-filter_threads', '1', '-filter_complex_threads', '1', ...args],
    { stdio: ['ignore', 'ignore', 'inherit'] });
}

// Memoria libre del contenedor (cgroup v2). Si no hay margen, mejor fallar el vídeo que tumbar n8n.
function memoriaLibreMB() {
  try {
    const max = fs.readFileSync('/sys/fs/cgroup/memory.max', 'utf8').trim();
    const usada = parseInt(fs.readFileSync('/sys/fs/cgroup/memory.current', 'utf8'), 10);
    if (max === 'max' || !usada) return null;
    let cache = 0;
    try { cache = parseInt((fs.readFileSync('/sys/fs/cgroup/memory.stat', 'utf8').match(/^inactive_file (\d+)/m) || [])[1] || '0', 10); } catch (e) { /* sin estadística */ }
    return Math.round((parseInt(max, 10) - usada + cache) / 1048576);
  } catch (e) { return null; }
}

const fuente = FUENTE.replace(/\\/g, '/').replace(/:/g, '\\:');
const tamTexto = vertical ? 54 : 50;
const anchoLinea = vertical ? 20 : 32;
const fundidos = `fade=t=in:st=0:d=0.35,fade=t=out:st=${(SEG - 0.35).toFixed(2)}:d=0.35`;
const comunX264 = ['-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage', '-crf', '25', '-threads', '1', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-an'];

function texto(archivoTexto, y) {
  const t = archivoTexto.replace(/\\/g, '/').replace(/:/g, '\\:');
  return `drawtext=fontfile='${fuente}':textfile='${t}':fontcolor=white:fontsize=${tamTexto}:line_spacing=10:text_align=C:` +
    `box=1:boxcolor=${AZUL}@0.88:boxborderw=22:x=(w-text_w)/2:y=${y}`;
}

async function main() {
  const libre = memoriaLibreMB();
  const minimo = parseInt(env.MONTAJE_MEMORIA_MIN_MB || '110', 10);
  if (libre !== null && libre < minimo) {
    throw new Error(`Memoria insuficiente en el servidor para montar el vídeo (${libre} MB libres, hacen falta ${minimo}). ` +
      'Reintenta más tarde o sube el plan de Render a uno con más memoria.');
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'montaje-'));
  try {
    const clips = [];
    for (let i = 0; i < escenas.length; i++) {
      const e = escenas[i];
      const img = path.join(tmp, `e${i}.jpg`);
      const txt = path.join(tmp, `e${i}.txt`);
      const clip = path.join(tmp, `e${i}.mp4`);
      fs.writeFileSync(txt, partir(e.texto, anchoLinea));
      const frames = Math.round(SEG * FPS);
      if (await imagenCloudflare(e.imagen, img)) {
        // Fondo desenfocado a pantalla completa + imagen con zoom lento + texto en el tercio inferior.
        // Se lee la imagen una sola vez (sin -loop): el fondo se repite con «loop» y zoompan genera los fotogramas.
        // Así el pico de memoria baja de ~700 MB a ~85 MB.
        const lado = vertical ? W : H;
        const filtro =
          `[0:v]scale=${lado}:${lado},split[a][b];` +
          `[a]scale=${W / 2}:${H / 2}:force_original_aspect_ratio=increase,crop=${W / 2}:${H / 2},boxblur=10:1,scale=${W}:${H},eq=brightness=-0.15,` +
          `loop=loop=${frames - 1}:size=1:start=0,setpts=N/${FPS}/TB[fondo];` +
          `[b]zoompan=z='min(zoom+0.0007,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=${frames}:s=${lado}x${lado}:fps=${FPS}[frente];` +
          `[fondo][frente]overlay=(W-w)/2:${vertical ? '(H-h)/2-140' : '0'}:shortest=1,` +
          `${texto(txt, vertical ? 'h*0.70' : 'h*0.72')},${fundidos},format=yuv420p[v]`;
        ff(['-i', img, '-filter_complex', filtro, '-map', '[v]', '-frames:v', String(frames), ...comunX264, clip]);
      } else {
        const filtro = `${texto(txt, '(h-text_h)/2')},${fundidos},format=yuv420p`;
        ff(['-f', 'lavfi', '-i', `color=c=${AZUL}:s=${W}x${H}:d=${SEG}:r=${FPS}`, '-vf', filtro, '-t', String(SEG), ...comunX264, clip]);
      }
      clips.push(clip);
    }
    // Tarjeta de cierre con la marca
    const marca = path.join(tmp, 'marca.txt');
    const llamada = path.join(tmp, 'llamada.txt');
    fs.writeFileSync(marca, partir(negocio, anchoLinea));
    fs.writeFileSync(llamada, partir(cierre, anchoLinea + 6));
    const final = path.join(tmp, 'cierre.mp4');
    const t = (f) => f.replace(/\\/g, '/').replace(/:/g, '\\:');
    ff(['-f', 'lavfi', '-i', `color=c=${AZUL}:s=${W}x${H}:d=3:r=${FPS}`, '-vf',
      `drawtext=fontfile='${fuente}':textfile='${t(marca)}':fontcolor=white:fontsize=${tamTexto + 4}:text_align=C:line_spacing=8:x=(w-text_w)/2:y=(h-text_h)/2-60,` +
      `drawtext=fontfile='${fuente}':textfile='${t(llamada)}':fontcolor=0xFFD23F:fontsize=${tamTexto - 12}:text_align=C:line_spacing=8:x=(w-text_w)/2:y=(h/2)+50,` +
      `fade=t=in:st=0:d=0.35,format=yuv420p`, '-t', '3', ...comunX264, final]);
    clips.push(final);

    // Unir las escenas y añadir una pista de audio silenciosa (algunas redes la exigen)
    const lista = path.join(tmp, 'lista.txt');
    fs.writeFileSync(lista, clips.map((c) => `file '${c}'`).join('\n'));
    const salida = path.join(tmp, 'video.mp4');
    ff(['-f', 'concat', '-safe', '0', '-i', lista, '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
      '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart', salida]);
    const datos = fs.readFileSync(salida);

    if (env.OMNI_MONTAJE_SALIDA) { fs.copyFileSync(salida, env.OMNI_MONTAJE_SALIDA); console.log(JSON.stringify({ archivo: env.OMNI_MONTAJE_SALIDA, bytes: datos.length })); return; }

    const require = createRequire(import.meta.url);
    const pg = require(require.resolve('pg', { paths: [BASE, path.join(BASE, 'node_modules'), process.cwd()] }));
    const c = new pg.Client({
      host: env.DB_POSTGRESDB_HOST, port: Number(env.DB_POSTGRESDB_PORT || 5432), database: env.DB_POSTGRESDB_DATABASE,
      user: env.DB_POSTGRESDB_USER, password: env.DB_POSTGRESDB_PASSWORD,
      ssl: env.DB_POSTGRESDB_SSL_ENABLED === 'true' ? { rejectUnauthorized: false } : false,
    });
    await c.connect();
    try {
      const pieza = /^[0-9a-f-]{36}$/i.test(String(trabajo.pieza_id || '')) ? trabajo.pieza_id : null;
      const r = await c.query(`INSERT INTO medios (tipo, mime, datos, prompt, pieza_id) VALUES ('video', 'video/mp4', $1, $2, $3) RETURNING id`,
        [datos, String(trabajo.prompt || escenas.map((e) => e.texto).join(' · ')).slice(0, 2000), pieza]);
      console.log(JSON.stringify({ id: r.rows[0].id, bytes: datos.length, escenas: escenas.length }));
    } finally { await c.end(); }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

main().catch((e) => { console.error('Fallo en el montaje:', e.message); process.exit(1); });
