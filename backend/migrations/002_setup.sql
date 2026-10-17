-- Phase 2: host review and guests joining.

alter table sessions add column host_payment_handle text;

-- Items get a stable id so the host can edit them. "position" keeps the display order.
alter table session_items drop constraint session_items_pkey;
alter table session_items add column id bigint generated always as identity primary key;
alter table session_items add constraint session_items_session_position_key unique (session_id, position);

-- One row per name on the bill. token_hash stays null until a guest takes the slot.
create table members (
    id          bigint generated always as identity primary key,
    session_id  text not null references sessions(id) on delete cascade,
    name        text not null,
    token_hash  text,
    joined_at   timestamptz,
    created_at  timestamptz not null default now()
);

create unique index members_session_name_key on members (session_id, lower(name));
