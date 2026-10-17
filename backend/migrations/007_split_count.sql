-- Phase 7b: an equal split can fix how many people share the item. Everyone pays total / count,
-- whether or not all of them have joined yet. Null means whoever joins splits it.
alter table session_items add column split_count integer
    check (split_count between 2 and 100);
alter table session_items add constraint split_count_needs_equal_split
    check (split_count is null or split_equally);
