-- Phase 5: tell live viewers when a split changes.
-- Every committed change to a split sends its id on the "session_changes" channel. Postgres
-- sends it only after the commit, and merges duplicates within one transaction. Touching the
-- idle timer (last_active_at) does not notify, so reading a split does not wake every viewer.

create or replace function notify_session_change() returns trigger
language plpgsql as $$
declare
    sid text;
begin
    if tg_table_name = 'sessions' then
        sid := case when tg_op = 'DELETE' then old.id else new.id end;
    elsif tg_table_name = 'claims' then
        -- Claims only know their member, so look up the split through it.
        select m.session_id into sid from members m
        where m.id = case when tg_op = 'DELETE' then old.member_id else new.member_id end;
    else
        sid := case when tg_op = 'DELETE' then old.session_id else new.session_id end;
    end if;

    if sid is not null then
        perform pg_notify('session_changes', sid);
    end if;
    return null;
end;
$$;

create trigger sessions_notify
    after insert or delete or update of
        status, currency, subtotal_minor, tax_minor, tip_minor, total_minor,
        host_payment_handle, bill_version
    on sessions
    for each row execute function notify_session_change();

create trigger session_items_notify
    after insert or update or delete on session_items
    for each row execute function notify_session_change();

create trigger members_notify
    after insert or update or delete on members
    for each row execute function notify_session_change();

create trigger claims_notify
    after insert or update or delete on claims
    for each row execute function notify_session_change();
