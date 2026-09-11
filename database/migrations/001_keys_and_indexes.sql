-- Foreign keys and indexes the ER diagram documents but the dump does not contain.
--
-- Run as the `postgres` superuser; `abcd_app` is read-only by design:
--   docker compose exec -T db psql -U postgres -d abcd < database/migrations/001_keys_and_indexes.sql
--
-- Nothing in the API depends on this. At the current size (largest table 4,880
-- rows) every plan is a sequential scan and finishes instantly. It is here for the
-- real dataset, where filtering a cross table by allele or cell type -- neither of
-- which is a prefix of any primary key -- would otherwise scan the whole table.
--
-- Verified before writing: zero orphan rows on every join below.

BEGIN;

-- Hierarchy.
ALTER TABLE subject ADD CONSTRAINT subject_study_fk
  FOREIGN KEY (study_id) REFERENCES study (study_id);
ALTER TABLE sample ADD CONSTRAINT sample_subject_fk
  FOREIGN KEY (subject_id) REFERENCES subject (subject_id);

CREATE INDEX IF NOT EXISTS subject_study_idx ON subject (study_id);
CREATE INDEX IF NOT EXISTS sample_subject_idx ON sample (subject_id);

-- Dimension references. The summary and cross tables all key back to the two
-- dimension tables, and every one of them gets filtered by those ids.
DO $$
DECLARE
  level text;
  tbl text;
BEGIN
  FOREACH level IN ARRAY ARRAY['study', 'subject', 'sample'] LOOP
    FOREACH tbl IN ARRAY ARRAY[
      '_summary', '_chain_summary', '_annotated_celltype',
      '_chain_annotated_celltype_summary', '_vj_allele',
      '_vj_allele_annotated_celltype'
    ] LOOP
      EXECUTE format(
        'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I (%I)',
        level || tbl, level || tbl || '_parent_fk', level || '_id', level, level || '_id'
      );
    END LOOP;

    -- Cell type lookups.
    FOREACH tbl IN ARRAY ARRAY[
      '_annotated_celltype', '_chain_annotated_celltype_summary',
      '_vj_allele_annotated_celltype'
    ] LOOP
      EXECUTE format(
        'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (annotated_celltype_id)
           REFERENCES annotated_celltype (annotated_celltype_id)',
        level || tbl, level || tbl || '_celltype_fk'
      );
      EXECUTE format(
        'CREATE INDEX IF NOT EXISTS %I ON %I (annotated_celltype_id)',
        level || tbl || '_celltype_idx', level || tbl
      );
    END LOOP;

    -- Allele lookups.
    FOREACH tbl IN ARRAY ARRAY['_vj_allele', '_vj_allele_annotated_celltype'] LOOP
      EXECUTE format(
        'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (vj_allele_id)
           REFERENCES vj_allele (vj_allele_id)',
        level || tbl, level || tbl || '_allele_fk'
      );
      EXECUTE format(
        'CREATE INDEX IF NOT EXISTS %I ON %I (vj_allele_id)',
        level || tbl || '_allele_idx', level || tbl
      );
    END LOOP;

    -- `chain` is the most-used facet and is not a leading primary key column on
    -- the cross tables.
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS %I ON %I (chain)',
      level || '_chain_ct_chain_idx', level || '_chain_annotated_celltype_summary'
    );
  END LOOP;
END $$;

COMMIT;

ANALYZE;
