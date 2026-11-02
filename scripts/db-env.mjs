// Normaliza la conexión a Postgres antes de arrancar.
// Acepta: DATABASE_URL, o una URL postgresql://… pegada por error en DB_POSTGRESDB_PASSWORD,
// y elimina espacios sobrantes de la contraseña. Imprime líneas `export …` para el shell.
const e = process.env;
const q = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'";
const pass = String(e.DB_POSTGRESDB_PASSWORD || '').trim();
const url = String(e.DATABASE_URL || '').trim() || (/^postgres(ql)?:\/\//i.test(pass) ? pass : '');
const out = {};
if (url) {
  const u = new URL(url);
  out.DB_POSTGRESDB_HOST = u.hostname;
  out.DB_POSTGRESDB_PORT = u.port || '5432';
  out.DB_POSTGRESDB_DATABASE = decodeURIComponent(u.pathname.replace(/^\//, ''));
  out.DB_POSTGRESDB_USER = decodeURIComponent(u.username);
  out.DB_POSTGRESDB_PASSWORD = decodeURIComponent(u.password);
  // Las URL externas de Render (…render.com) exigen SSL; la interna no.
  if (/\.render\.com$/i.test(u.hostname)) out.DB_POSTGRESDB_SSL_ENABLED = 'true';
  console.error('[omniagent] conexión a Postgres tomada de una URL (' + u.hostname + ')');
} else if (pass) {
  out.DB_POSTGRESDB_PASSWORD = pass;
}
for (const [k, v] of Object.entries(out)) console.log('export ' + k + '=' + q(v));
