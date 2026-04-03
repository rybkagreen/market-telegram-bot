-- ══════════════════════════════════════════════════════════════
-- Production DB Cleanup Script — v2 (no pager-safe)
-- ══════════════════════════════════════════════════════════════

-- Reset platform_account FIRST (no FK issues)
UPDATE platform_account SET
    escrow_reserved      = 0,
    payout_reserved      = 0,
    profit_accumulated   = 0,
    total_topups         = 0,
    total_payouts        = 0,
    legal_name           = NULL,
    inn                  = NULL,
    kpp                  = NULL,
    ogrn                 = NULL,
    address              = NULL,
    bank_name            = NULL,
    bank_account         = NULL,
    bank_bik             = NULL,
    bank_corr_account    = NULL,
    updated_at           = NOW()
WHERE id = 1;

-- Truncate all user data in dependency order
TRUNCATE TABLE
    audit_logs,
    contract_signatures,
    publication_logs,
    mailing_logs,
    click_tracking,
    yookassa_payments,
    user_badges,
    badge_achievements,
    reputation_history,
    placement_disputes,
    user_feedback,
    ord_registrations,
    reviews
RESTART IDENTITY CASCADE;

TRUNCATE TABLE
    contracts,
    legal_profiles,
    payout_requests,
    transactions,
    placement_requests,
    channel_mediakits,
    channel_settings,
    reputation_scores,
    telegram_chats,
    badges
RESTART IDENTITY CASCADE;

TRUNCATE TABLE users RESTART IDENTITY CASCADE;
