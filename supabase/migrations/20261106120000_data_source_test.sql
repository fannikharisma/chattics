-- Test-before-save support for the Data Source card.
-- test_fingerprint is the hash of the fields that passed; last_structure caches
-- the tables and columns so GET can show summaries without another BigQuery call.

alter table data_sources
    add column if not exists test_fingerprint text,
    add column if not exists last_structure jsonb not null
        default '{"tables": []}'::jsonb;