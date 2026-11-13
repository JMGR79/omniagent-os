// OmniAgent OS · preparación en cada arranque del contenedor (antes de `n8n start`).
// 1) Aplica las migraciones SQL (idempotentes).
// 2) Crea o actualiza las credenciales de n8n a partir de variables de entorno.
// 3) Importa los flujos que faltan y actualiza los que cambiaron en el repositorio
//    (OMNI_ACTUALIZAR_FLUJOS=false para no tocar nunca los existentes).
// 4) Activa una sola vez cada flujo cuyos requisitos estén configurados.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const require = createRequire(import.meta.url);
const BASE = process.env.OMNI_DIR || '/opt/omni';
const pg = require(require.resolve('pg', { paths: [BASE, path.join(BASE, 'node_modules'), process.cwd()] }));
const N8N = process.env.OMNI_N8N_BIN || 'n8n';
const env = process.env;
const log = (...a) => console.log('[omniagent]', ...a);

const db = {
  host: env.DB_POSTGRESDB_HOST, port: Number(env.DB_POSTGRESDB_PORT || 5432),
  database: env.DB_POSTGRESDB_DATABASE, user: env.DB_POSTGRESDB_USER, password: env.DB_POSTGRESDB_PASSWORD,
  ssl: env.DB_POSTGRESDB_SSL_ENABLED === 'true' ? { rejectUnauthorized: false } : false,
};
const esquemaN8n = env.DB_POSTGRESDB_SCHEMA || 'public';

async function conectar() {
  for (let i = 1; i <= 30; i++) {
    const c = new pg.Client(db);
    try { await c.connect(); return c; } catch (e) {
      log(`Base de datos no disponible (intento ${i}/30): ${e.message}`);
      if (/password authentication failed/i.test(e.message)) log('→ La contraseña de la base de datos no es correcta: copia en Render el campo «Password» (o la «Internal Database URL» completa) en DB_POSTGRESDB_PASSWORD.');
      await c.end().catch(() => {});
      await new Promise((r) => setTimeout(r, 4000));
    }
  }
  throw new Error('No se pudo conectar a Postgres');
}

function n8n(...args) {
  execFileSync(N8N, args, { stdio: 'inherit', env });
}

async function main() {
  const c = await conectar();

  // 1) Migraciones
  const dirMig = path.join(BASE, 'db', 'migrations');
  for (const f of fs.readdirSync(dirMig).filter((x) => x.endsWith('.sql')).sort()) {
    await c.query(fs.readFileSync(path.join(dirMig, f), 'utf8'));
    log('migración aplicada:', f);
  }
  await c.query(`CREATE TABLE IF NOT EXISTS omni_meta (clave text PRIMARY KEY, valor text, creado_en timestamptz DEFAULT now())`);
  if (esquemaN8n !== 'public') await c.query(`CREATE SCHEMA IF NOT EXISTS "${esquemaN8n}"`);

  // 1b) Limpieza de ejecuciones de n8n atascadas: tras una caída, n8n intenta recuperarlas todas al
  //     arrancar y, si son miles, se queda sin memoria y entra en bucle. Nunca bloquea el arranque.
  const limpiezas = [
    ['a medias', `DELETE FROM "${esquemaN8n}".execution_entity WHERE status IN ('new','running','unknown','crashed')
        AND coalesce("startedAt", "createdAt") < now() - interval '30 minutes'`],
    ['en espera caducadas', `DELETE FROM "${esquemaN8n}".execution_entity WHERE status = 'waiting'
        AND (coalesce("waitTill", "createdAt") < now() - interval '1 hour')`],
    ['antiguas', `DELETE FROM "${esquemaN8n}".execution_entity WHERE "createdAt" < now() - interval '${parseInt(env.OMNI_DIAS_EJECUCIONES || '3', 10)} days'`],
  ];
  for (const [nombre, sql] of limpiezas) {
    try { const r = await c.query(sql); if (r.rowCount) log(`ejecuciones ${nombre} borradas:`, r.rowCount); }
    catch (e) { log(`no se pudieron limpiar las ejecuciones ${nombre}:`, e.message); }
  }

  // 2) Credenciales desde variables de entorno (se reimportan en cada arranque)
  const creds = [{
    id: 'omniPostgres0001', name: 'Postgres OmniAgent', type: 'postgres',
    data: { host: db.host, port: db.port, database: db.database, user: db.user, password: db.password,
      ssl: db.ssl ? 'allow' : 'disable', allowUnauthorizedCerts: !!db.ssl, maxConnections: 10, sshTunnel: false },
  }];
  const gmail = env.GMAIL_USUARIO || env.EMAIL_DUENO;
  if (gmail && env.GMAIL_APP_PASSWORD) {
    const pass = env.GMAIL_APP_PASSWORD.replace(/\s+/g, '');
    creds.push({ id: 'omniGmailSmtp001', name: 'Gmail SMTP', type: 'smtp',
      data: { user: gmail, password: pass, host: 'smtp.gmail.com', port: 465, secure: true, disableStartTls: false, hostName: '' } });
    creds.push({ id: 'omniGmailImap001', name: 'Gmail IMAP', type: 'imap',
      data: { user: gmail, password: pass, host: 'imap.gmail.com', port: 993, secure: true, allowUnauthorizedCerts: false } });
  }
  if (env.TELEGRAM_BOT_TOKEN) {
    creds.push({ id: 'omniTelegram0001', name: 'Telegram OmniAgent', type: 'telegramApi',
      data: { accessToken: env.TELEGRAM_BOT_TOKEN, baseUrl: 'https://api.telegram.org' } });
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-'));
  try {
    const dirCred = path.join(tmp, 'cred');
    fs.mkdirSync(dirCred);
    creds.forEach((x) => fs.writeFileSync(path.join(dirCred, x.id + '.json'), JSON.stringify(x), { mode: 0o600 }));
    n8n('import:credentials', '--separate', '--input=' + dirCred);
    log('credenciales sincronizadas:', creds.map((x) => x.name).join(', '));

    // 3) Flujos que faltan o que cambiaron en el repositorio
    const dirWf = path.join(BASE, 'n8n', 'workflows');
    const archivos = fs.readdirSync(dirWf).filter((x) => x.endsWith('.json'));
    const existentes = new Set((await c.query(`SELECT id FROM "${esquemaN8n}".workflow_entity`)).rows.map((r) => r.id));
    const huellas = new Map((await c.query(`SELECT clave, valor FROM omni_meta WHERE clave LIKE 'huella:%'`)).rows.map((r) => [r.clave, r.valor]));
    const actualizar = env.OMNI_ACTUALIZAR_FLUJOS !== 'false';
    const dirNuevos = path.join(tmp, 'wf');
    fs.mkdirSync(dirNuevos);
    const importar = [];
    for (const f of archivos) {
      const texto = fs.readFileSync(path.join(dirWf, f), 'utf8');
      const wf = JSON.parse(texto);
      const huella = crypto.createHash('sha256').update(texto).digest('hex');
      const existe = existentes.has(wf.id);
      if (existe && (!actualizar || huellas.get('huella:' + wf.id) === huella)) continue;
      fs.copyFileSync(path.join(dirWf, f), path.join(dirNuevos, f));
      importar.push({ id: wf.id, huella, existe });
    }
    if (importar.length) {
      n8n('import:workflow', '--separate', '--input=' + dirNuevos);
      for (const w of importar) {
        await c.query(`INSERT INTO omni_meta (clave, valor) VALUES ($1, $2) ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor`, ['huella:' + w.id, w.huella]);
        // Un flujo actualizado que ya estaba activo se vuelve a publicar con la versión nueva
        if (w.existe && (await c.query('SELECT 1 FROM omni_meta WHERE clave = $1', ['activado:' + w.id])).rowCount) {
          try { n8n('publish:workflow', '--id=' + w.id); } catch (e) { log('no se pudo volver a publicar', w.id, '-', e.message); }
        }
      }
      log('flujos importados o actualizados:', importar.map((w) => w.id).join(', '));
    } else log('todos los flujos están al día; no se toca nada');

    // Los reintentos pendientes por falta de cuota o límite de uso del proveedor de IA no se arreglan reintentando
    const limpiados = await c.query(`UPDATE incidentes SET proximo_reintento = NULL
      WHERE resuelto_en IS NULL AND proximo_reintento IS NOT NULL
        AND error ~* '(429|quota|rate.?limit|too many requests|exceeded)'`);
    if (limpiados.rowCount) log('reintentos cancelados por cuota agotada:', limpiados.rowCount);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  // 4) Activación automática (una sola vez por flujo; si luego lo pausas, se respeta)
  const prov = (env.PROVEEDOR_IA || 'anthropic').toLowerCase();
  const tieneIA = !!({ anthropic: env.ANTHROPIC_API_KEY, openai: env.OPENAI_API_KEY, gemini: env.GEMINI_API_KEY }[prov]);
  const tieneEmail = !!(gmail && env.GMAIL_APP_PASSWORD);
  const tieneTg = !!env.TELEGRAM_BOT_TOKEN; // con el bot activo, escribe /id para conocer tu chat_id
  const requisitos = {
    omniSYS00errores: true, omniSYS01reintnt: true, omniSYS20control: !!env.OMNIAGENT_CONTROL_TOKEN,
    omniAGT00agentes: tieneIA, omniCNT01directr: tieneIA, omniPUB01publica: true,
    omniTEL01telegrm: tieneTg, omniMSG01emailld: tieneIA && tieneEmail, omniRPT01resumen: true,
    omniSYS21herrams: !!env.OMNIAGENT_CONTROL_TOKEN, omniMCP01servidr: !!env.OMNIAGENT_CONTROL_TOKEN,
    omniWA02enviarms: true,
    omniGEN01imagen0: true, omniGEN02video00: true, omniWEB01servir0: true,
    omniGEN03webs000: tieneIA, omniNEG01negocio: tieneIA,
    omniVID01fabrica: tieneIA && ['montaje', 'gemini', 'openai'].includes((env.PROVEEDOR_VIDEO || '').toLowerCase()),
    omniWA01entrante: tieneIA && !!(env.WHATSAPP_TOKEN && env.WHATSAPP_PHONE_ID && env.WHATSAPP_APP_SECRET && env.WHATSAPP_VERIFY_TOKEN),
  };
  if (env.OMNI_AUTOACTIVAR !== 'false') {
    for (const [id, ok] of Object.entries(requisitos)) {
      const clave = 'activado:' + id;
      if (!ok) { log('pendiente de configurar, no se activa todavía:', id); continue; }
      if ((await c.query('SELECT 1 FROM omni_meta WHERE clave = $1', [clave])).rowCount) continue;
      try { n8n('publish:workflow', '--id=' + id); await c.query('INSERT INTO omni_meta (clave, valor) VALUES ($1, $2)', [clave, new Date().toISOString()]); log('activado:', id); }
      catch (e) { log('no se pudo activar', id, '-', e.message); }
    }
  }
  // 5) Modo prueba: los flujos que reciben mensajes (Telegram, WhatsApp) se despublican para no
  //    quitarle el webhook al servidor que sigue en producción; al salir del modo prueba se reactivan.
  const entrantes = ['omniTEL01telegrm', 'omniWA01entrante'];
  const prueba = env.OMNI_MODO_PRUEBA === 'true';
  for (const id of entrantes) {
    const marca = 'pausado_prueba:' + id;
    const pausado = (await c.query('SELECT 1 FROM omni_meta WHERE clave = $1', [marca])).rowCount > 0;
    const activo = (await c.query(`SELECT 1 FROM "${esquemaN8n}".workflow_entity WHERE id = $1 AND active`, [id])).rowCount > 0;
    try {
      if (prueba && activo) {
        n8n('unpublish:workflow', '--id=' + id);
        await c.query('INSERT INTO omni_meta (clave, valor) VALUES ($1, $2) ON CONFLICT (clave) DO NOTHING', [marca, new Date().toISOString()]);
        log('modo prueba, en pausa:', id);
      } else if (!prueba && pausado) {
        n8n('publish:workflow', '--id=' + id);
        await c.query('DELETE FROM omni_meta WHERE clave = $1', [marca]);
        log('fin del modo prueba, reactivado:', id);
      }
    } catch (e) { log('no se pudo cambiar el estado de', id, '-', e.message); }
  }
  await c.end();
}

main().catch((e) => { console.error('[omniagent] fallo en la preparación:', e); process.exit(1); });
