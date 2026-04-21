// Deterministic test user identities — must match scripts/e2e/seed_e2e.py
export const TEST_USERS = {
  advertiser: { telegramId: 9001, storageFile: 'tests/.auth/advertiser.json' },
  owner: { telegramId: 9002, storageFile: 'tests/.auth/owner.json' },
  admin: { telegramId: 9003, storageFile: 'tests/.auth/admin.json' },
} as const

export type Role = keyof typeof TEST_USERS
