-- Phase 6: settlement. The host gives one payment handle and says which app it belongs to. Each
-- guest records the amount they paid.

alter table sessions add column host_payment_platform text
    check (host_payment_platform in ('revolut', 'wise'));

-- The amount a guest marked as paid, taken from their share at that moment. The payment only
-- counts while it matches the share, so a changed share shows as "changed" instead of paid.
alter table members add column paid_amount_minor bigint;
alter table members add column paid_at timestamptz;

-- Changing the platform should reach live viewers too, so the notify trigger watches it.
drop trigger sessions_notify on sessions;
create trigger sessions_notify
    after insert or delete or update of
        status, currency, subtotal_minor, tax_minor, tip_minor, total_minor,
        host_payment_handle, host_payment_platform, bill_version
    on sessions
    for each row execute function notify_session_change();
