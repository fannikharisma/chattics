-- Chattics initial schema.
-- Every table except tenants carries tenant_id; query_log is permanent and
-- must survive conversation deletion (ON DELETE SET NULL, never CASCADE).

create table tenants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    status text not null default 'active'
        check (status in ('active', 'disabled')),
    created_at timestamptz not null default now()
);

create table users (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid references tenants(id),
    selected_tenant_id uuid references tenants(id) on delete set null,
    full_name text not null,
    email text not null,
    role text not null
        check (role in ('platform_admin', 'tenant_admin', 'user')),
    status text not null default 'active'
        check (status in ('active', 'deactivated')),
    created_at timestamptz not null default now()
);

-- One email per Tenant, case-insensitive. Platform Admins have a null
-- tenant_id, so this index deliberately does not constrain them.
create unique index users_tenant_email_key on users (tenant_id, lower(email));
create index users_tenant_id_idx on users (tenant_id);
create index users_selected_tenant_id_idx on users (selected_tenant_id);

create table data_sources (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null unique references tenants(id),
    engine text not null,
    method text not null,
    fields jsonb not null default '{}'::jsonb,
    status text not null default 'not_connected'
        check (status in ('not_connected', 'connected')),
    tested_at timestamptz,
    created_at timestamptz not null default now()
);

create table model_settings (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null unique references tenants(id),
    provider text,
    model_name text,
    address text,
    api_key_encrypted text,  -- Fernet ciphertext only; never plaintext
    status text not null default 'not_set'
        check (status in ('not_set', 'working')),
    tested_at timestamptz,
    created_at timestamptz not null default now()
);

create table tenant_settings (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null unique references tenants(id),
    maximum_period_days integer not null default 730
        check (maximum_period_days > 0),
    created_at timestamptz not null default now()
);

create table sl_tables (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    table_name text not null,
    meaning text,
    grain text,
    status text not null default 'needs_work'
        check (status in ('needs_work', 'described')),
    created_at timestamptz not null default now(),
    unique (tenant_id, table_name)
);

create table sl_columns (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    sl_table_id uuid not null references sl_tables(id) on delete cascade,
    column_name text not null,
    meaning text,
    created_at timestamptz not null default now(),
    unique (sl_table_id, column_name)
);

create index sl_columns_tenant_id_idx on sl_columns (tenant_id);

create table sl_relationships (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    from_table text not null,
    from_columns text[] not null,
    to_table text not null,
    to_columns text[] not null,
    created_at timestamptz not null default now()
);

create index sl_relationships_tenant_id_idx on sl_relationships (tenant_id);
create index sl_relationships_from_idx on sl_relationships (tenant_id, from_table);
create index sl_relationships_to_idx on sl_relationships (tenant_id, to_table);

create table kpis (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    name text not null,
    also_called text,
    description text,
    grain text not null,
    time_column text not null,
    formula text not null,
    default_period_days integer check (default_period_days > 0),
    unit text,
    created_at timestamptz not null default now()
);

create unique index kpis_tenant_name_key on kpis (tenant_id, lower(name));

create table kpi_inputs (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    kpi_id uuid not null references kpis(id) on delete cascade,
    source_type text not null check (source_type in ('column', 'kpi')),
    -- Polymorphic: sl_columns.id when source_type = 'column',
    -- kpis.id when source_type = 'kpi'. No FK because the target table varies.
    source_ref uuid not null,
    label text not null,
    created_at timestamptz not null default now()
);

create index kpi_inputs_tenant_id_idx on kpi_inputs (tenant_id);
create index kpi_inputs_kpi_id_idx on kpi_inputs (kpi_id);
create index kpi_inputs_source_idx on kpi_inputs (tenant_id, source_type, source_ref);

create table kpi_rules (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    kpi_id uuid not null references kpis(id) on delete cascade,
    rule text not null,
    created_at timestamptz not null default now()
);

create index kpi_rules_tenant_id_idx on kpi_rules (tenant_id);
create index kpi_rules_kpi_id_idx on kpi_rules (kpi_id);

create table conversations (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    user_id uuid not null references users(id),
    title text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index conversations_tenant_id_idx on conversations (tenant_id);
create index conversations_user_updated_idx on conversations (user_id, updated_at desc);

create table messages (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    kind text not null
        check (kind in ('question', 'clarification', 'assumption', 'kpi_note', 'result')),
    content jsonb not null,
    created_at timestamptz not null default now()
);

create index messages_tenant_id_idx on messages (tenant_id);
create index messages_conversation_created_idx on messages (conversation_id, created_at);

create table query_log (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    user_id uuid not null references users(id),
    -- The log outlives its Conversation and its KPI: never cascade here.
    conversation_id uuid references conversations(id) on delete set null,
    question text not null,
    query_text text not null,
    kpi_id uuid references kpis(id) on delete set null,
    assumption_text text,
    verdict text not null
        check (verdict in ('confirmed', 'rejected', 'no_answer', 'kpi_matched')),
    result text not null
        check (result in ('succeeded', 'succeeded_after_retry', 'failed')),
    row_count integer check (row_count >= 0),
    duration_ms integer check (duration_ms >= 0),
    trimmed boolean not null default false,
    retry_note text,
    checks jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index query_log_tenant_created_idx on query_log (tenant_id, created_at desc);
create index query_log_user_id_idx on query_log (user_id);
create index query_log_conversation_id_idx on query_log (conversation_id);
create index query_log_kpi_id_idx on query_log (kpi_id);

create table datasets (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    user_id uuid not null references users(id),
    name text not null,
    query_text text not null,
    relative_period jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create unique index datasets_user_name_key on datasets (user_id, lower(name));
create index datasets_tenant_id_idx on datasets (tenant_id);

create table charts (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    user_id uuid not null references users(id),
    dataset_id uuid not null references datasets(id) on delete restrict,
    name text not null,
    chart_config jsonb not null,
    created_at timestamptz not null default now()
);

create unique index charts_user_name_key on charts (user_id, lower(name));
create index charts_tenant_id_idx on charts (tenant_id);
create index charts_dataset_id_idx on charts (dataset_id);

create table dashboards (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    user_id uuid not null references users(id),
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index dashboards_user_name_key on dashboards (user_id, lower(name));
create index dashboards_tenant_id_idx on dashboards (tenant_id);

create table dashboard_items (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    dashboard_id uuid not null references dashboards(id) on delete cascade,
    chart_id uuid not null references charts(id) on delete cascade,
    position integer not null default 0 check (position >= 0),
    width text not null
        check (width in ('quarter', 'third', 'half', 'full')),
    created_at timestamptz not null default now(),
    unique (dashboard_id, chart_id)
);

create index dashboard_items_tenant_id_idx on dashboard_items (tenant_id);
create index dashboard_items_chart_id_idx on dashboard_items (chart_id);
