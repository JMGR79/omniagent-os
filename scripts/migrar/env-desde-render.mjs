// Genera el .env del servidor de Oracle a partir de las variables del servicio de Render.
// Uso (en GitHub Actions): RENDER_API_KEY=… node env-desde-render.mjs <serviceId> <dominio> <salida>
// Nunca imprime valores: los marca como secretos para que GitHub los oculte en los registros.
import fs from 'node:fs';
import crypto from 'node:crypto';

const [servicio, dominio, salida] = process.argv.slice(2);
const clave = process.env.RENDER_API_KEY;
if (!servicio || !dominio || !salida || !clave) {
  console.error('Uso: RENDER_API_KEY=… node env-desde-render.mjs <serviceId> <dominio> <salida>');
  process.exit(2);
}

const vars = new Map();
let cursor = '';
for (;;) {
  const url = new URL(`https://api.render.com/v1/services/${servicio}/env-vars`);
  url.searchParams.set('limit', '100');
  if (cursor) url.searchParams.set('cursor', cursor);
  const r = await fetch(url, { headers: { Authorization: `Bearer ${clave}`, Accept: 'application/json' } });
  if (!r.ok) { console.error(`Render respondió ${r.status} al leer las variables`); process.exit(1); }
  const lote = await r.json();
  for (const { envVar, cursor: c } of lote) { vars.set(envVar.key, String(envVar.value ?? '')); cursor = c; }
  if (lote.length < 100) break;
}

// Lo que depende de Render se sustituye por lo del servidor nuevo
const fuera = /^(DB_POSTGRESDB_|DATABASE_URL$|RENDER|NODE_OPTIONS$|WEBHOOK_URL$|N8N_EDITOR_BASE_URL$|N8N_HOST$|N8N_PROTOCOL$|N8N_PROXY_HOPS$|DOMINIO$|OMNI_MODO_PRUEBA$)/;
for (const k of [...vars.keys()]) if (fuera.test(k)) vars.delete(k);

const base = `https://${dominio}/`;
const propias = {
  DOMINIO: dominio,
  DB_TYPE: 'postgresdb',
  DB_POSTGRESDB_HOST: 'postgres',
  DB_POSTGRESDB_PORT: '5432',
  DB_POSTGRESDB_DATABASE: 'omniagent',
  DB_POSTGRESDB_USER: 'omniagent',
  DB_POSTGRESDB_PASSWORD: crypto.randomBytes(24).toString('hex'),
  DB_POSTGRESDB_SCHEMA: 'n8n',
  WEBHOOK_URL: base,
  N8N_EDITOR_BASE_URL: base,
  N8N_HOST: dominio,
  N8N_PROTOCOL: 'https',
  N8N_PROXY_HOPS: '1',
  // 24 GB de RAM: n8n ya no va justo de memoria
  NODE_OPTIONS: '--max-old-space-size=4096',
  // Mientras Render siga encendido: sin publicaciones automáticas ni bots entrantes (ver iniciar.sh)
  OMNI_MODO_PRUEBA: 'true',
};
for (const [k, v] of Object.entries(propias)) vars.set(k, v);

const lineas = ['# Generado desde Render por «Migrar desde Render». Contiene claves: no lo subas a ningún sitio.'];
for (const [k, v] of [...vars.entries()].sort(([a], [b]) => a.localeCompare(b))) {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(k)) continue;
  if (/[\r\n']/.test(v)) { console.error(`Variable omitida por llevar saltos de línea o comillas simples: ${k} (ponla a mano en /opt/omniagent/.env)`); continue; }
  if (v.length >= 6 && process.env.GITHUB_ACTIONS) console.log(`::add-mask::${v}`);
  // Comillas simples: Docker Compose las toma literalmente (sin sustituir $)
  lineas.push(`${k}='${v}'`);
}
fs.writeFileSync(salida, lineas.join('\n') + '\n', { mode: 0o600 });
console.log(`Variables preparadas: ${vars.size} (valores ocultos)`);
