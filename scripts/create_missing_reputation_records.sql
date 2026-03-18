-- Create missing reputation records for all users
-- This script is idempotent (safe to run multiple times)

INSERT INTO reputation_scores (
    user_id,
    advertiser_score,
    owner_score,
    is_advertiser_blocked,
    is_owner_blocked,
    advertiser_violations_count,
    owner_violations_count
)
SELECT 
    u.id,
    5.0,  -- default advertiser_score
    5.0,  -- default owner_score
    false,
    false,
    0,
    0
FROM users u
LEFT JOIN reputation_scores rs ON rs.user_id = u.id
WHERE rs.user_id IS NULL
ON CONFLICT (user_id) DO NOTHING;

-- Verify the results
SELECT 
    u.id AS user_id,
    u.username,
    rs.advertiser_score,
    rs.owner_score,
    CASE WHEN rs.user_id IS NOT NULL THEN '✓' ELSE '✗' END AS has_reputation
FROM users u
LEFT JOIN reputation_scores rs ON rs.user_id = u.id;
