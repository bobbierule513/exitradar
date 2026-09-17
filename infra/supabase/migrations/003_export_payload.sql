-- Export payloads for CSV/JSON downloads (used by PostgresStore.create_export)

ALTER TABLE exports
  ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '[]';
