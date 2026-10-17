-- Phase 7: equal split. The host can mark an item as shared. Guests then opt in with a claim of
-- 1, and everyone who opted in pays the same share of the line total.
alter table session_items add column split_equally boolean not null default false;
