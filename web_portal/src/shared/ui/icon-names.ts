/**
 * RekHarbor icon sprite — 132 canonical names, grouped.
 * Keep in sync with public/icons/rh-sprite.svg.
 * Source of truth: reports/design/test-avatars-handoff-2026-04-20/project/icons/Icons.jsx
 */

export const ICON_NAMES = [
  // Navigation
  'dashboard', 'cabinet', 'tariff', 'topup', 'payouts', 'campaign',
  'analytics', 'placement', 'channels', 'docs', 'referral', 'feedback', 'settings',
  // Admin
  'admin', 'users', 'disputes', 'requests', 'accounting', 'taxes', 'moderation', 'audit',
  // Status
  'success', 'warning', 'error', 'info', 'blocked', 'pending', 'hourglass', 'draft', 'archive',
  // Verification
  'verify-email', 'verify-tg', 'verify-entity', 'verify-bank', 'passport', 'kyc', 'verified',
  // Communication
  'telegram', 'email', 'push', 'sms', 'chat', 'phone', 'call', 'bell', 'bell-off', 'megaphone',
  // Finance
  'card', 'wallet', 'bank', 'ruble', 'dollar', 'coin', 'coin-stack', 'receipt',
  'invoice', 'contract', 'refund', 'transaction', 'deposit', 'withdraw', 'percent', 'tax-doc',
  // Metrics / Ad
  'reach', 'impressions', 'clicks', 'ctr', 'er', 'audience', 'growth', 'decline',
  'category', 'target', 'budget', 'heart', 'play', 'pause',
  // Actions
  'search', 'filter', 'sort', 'sort-asc', 'sort-desc', 'export', 'import',
  'download', 'upload', 'copy', 'share', 'link', 'unlink', 'delete', 'edit',
  'pin', 'expand', 'collapse', 'refresh', 'more-h', 'more-v', 'plus', 'minus',
  'check', 'close', 'logout', 'login', 'lock', 'unlock', 'key', 'eye', 'eye-off',
  'bookmark', 'flag', 'star', 'zap', 'calendar', 'clock',
  // Brand / nautical
  'anchor', 'compass', 'wave', 'wave-double', 'lighthouse', 'ship',
  'helm', 'sail', 'harbor', 'seagull', 'rope',
  // Arrows
  'arrow-up', 'arrow-down', 'arrow-left', 'arrow-right',
  'arrow-up-right', 'arrow-down-right',
  'chevron-up', 'chevron-down', 'chevron-left', 'chevron-right',
  'chevrons-left', 'chevrons-right', 'external',
] as const

export type IconName = typeof ICON_NAMES[number]

export const FILLED_AVAILABLE: ReadonlySet<IconName> = new Set<IconName>([
  'dashboard', 'cabinet', 'tariff', 'topup', 'payouts', 'campaign',
  'analytics', 'placement', 'channels', 'docs', 'referral', 'feedback', 'settings',
  'success', 'warning', 'error', 'info',
  'telegram', 'email', 'push',
  'star', 'zap', 'anchor', 'compass',
])
