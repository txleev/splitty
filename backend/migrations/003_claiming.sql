-- Phase 3: claiming. Claims point at the item id, so editing an item keeps its claims.

-- Bumped on every change to what people owe. A confirmation made on an older version is stale.
alter table sessions add column bill_version integer not null default 0;

-- The bill version a guest last confirmed on. Null means not confirmed.
alter table members add column confirmed_bill_version integer;

create index members_token_hash_idx on members (token_hash);

create table claims (
    member_id   bigint not null references members(id) on delete cascade,
    item_id     bigint not null references session_items(id) on delete cascade,
    quantity    integer not null check (quantity > 0),
    primary key (member_id, item_id)
);

create index claims_item_id_idx on claims (item_id);
