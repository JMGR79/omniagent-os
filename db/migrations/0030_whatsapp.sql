-- WhatsApp: los contactos pueden identificarse por teléfono (además de por email).
ALTER TABLE contactos ADD COLUMN IF NOT EXISTS telefono text;
CREATE UNIQUE INDEX IF NOT EXISTS contactos_telefono_uq ON contactos (telefono);

-- Interruptores del sistema (por ejemplo, la pausa del piloto automático).
CREATE TABLE IF NOT EXISTS ajustes (
  clave text PRIMARY KEY,
  valor text NOT NULL,
  actualizado_en timestamptz NOT NULL DEFAULT now()
);
