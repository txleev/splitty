-- Money is stored as integers in minor units (e.g. 14.50 -> 1450).

create table sessions (
    id              text primary key,                 -- 11-char URL-safe random id (see ids.py)
    status          text not null default 'draft'
                    check (status in ('draft', 'ready')),
    host_token_hash text not null,                    -- sha256 of the host token; the token itself is never stored
    currency        text,
    subtotal_minor  bigint,
    tax_minor       bigint,
    tip_minor       bigint,
    total_minor     bigint,
    warnings        text[] not null default '{}',
    created_at      timestamptz not null default now(),
    last_active_at  timestamptz not null default now()
);

create table session_items (
    session_id         text not null references sessions(id) on delete cascade,
    position           integer not null,
    name               text not null,
    quantity           numeric(10, 3) not null default 1,
    unit_price_minor   bigint,
    total_minor        bigint not null,
    missing            text[] not null default '{}',
    preassigned_names  text[] not null default '{}',  -- names from the host's note, used in Phase 2
    primary key (session_id, position)
);
