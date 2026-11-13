-- Vídeos guardados fuera de la base de datos (p. ej. en GitHub Releases): solo se guarda su URL pública.
-- Evita mover vídeos de varios MB por la memoria de n8n.
ALTER TABLE medios ADD COLUMN IF NOT EXISTS url text;
ALTER TABLE medios ALTER COLUMN datos DROP NOT NULL;
