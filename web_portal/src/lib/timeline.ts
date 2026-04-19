// ============================================================
// RekHarbor Web Portal — Timeline Event Derivation Helpers
// S31-07 | ORD / Act / Contract timeline event generators
// ============================================================

import type { TimelineEvent, TimelineEventStatus } from './timeline.types';
import type { OrdRegistration } from '@/lib/types/misc';
import type { Act } from '@/api/acts';
import type { Contract } from '@/lib/types';

// ─── ORD timeline events ────────────────────────────────────

/**
 * Derive timeline events from ORD registration data.
 * Security: NEVER console.log(ord.erid) or ord.ord_token anywhere.
 */
export function deriveOrdTimelineEvents(
  ord: OrdRegistration | null | undefined,
): TimelineEvent[] {
  if (!ord) return [];

  const statusMap: Record<
    string,
    { label: string; status: TimelineEventStatus; ts: string }
  > = {
    pending: {
      label: '⏳ ОРД-регистрация',
      status: 'warning',
      ts: ord.created_at,
    },
    registered: {
      label: '🔄 Регистрация принята ОРД',
      status: 'info',
      ts: ord.created_at,
    },
    token_received: {
      label: `✅ ERID получен: ${ord.erid ?? ''}`,
      status: 'success',
      ts: ord.created_at,
    },
    reported: {
      label: '📨 Отчёт отправлен в ОРД',
      status: 'success',
      ts: ord.created_at,
    },
    failed: {
      label: `❌ Ошибка ОРД${ord.error_message ? ': ' + ord.error_message : ''}`,
      status: 'danger',
      ts: ord.created_at,
    },
  };

  const entry = statusMap[ord.status];
  if (!entry) return [];

  return [
    {
      id: `ord-${ord.status}`,
      type: 'ord',
      label: entry.label,
      status: entry.status,
      timestamp: entry.ts,
    },
  ];
}

// ─── Act timeline events ────────────────────────────────────

export function deriveActTimelineEvents(acts: Act[]): TimelineEvent[] {
  const statusMap: Record<
    string,
    {
      label: (id: number) => string;
      status: TimelineEventStatus;
      ts: (act: Act) => string;
    }
  > = {
    draft: {
      label: (id) => `📄 Акт #${id} сформирован`,
      status: 'default',
      ts: (act) => act.created_at,
    },
    pending: {
      label: (id) => `⏳ Акт #${id} ожидает подписания`,
      status: 'warning',
      ts: (act) => act.created_at,
    },
    signed: {
      label: (id) => `✅ Акт #${id} подписан`,
      status: 'success',
      ts: (act) => act.signed_at ?? act.created_at,
    },
    auto_signed: {
      label: (id) => `✅ Акт #${id} авто-подписан`,
      status: 'success',
      ts: (act) => act.signed_at ?? act.created_at,
    },
  };

  const events: TimelineEvent[] = []
  for (const act of acts) {
    const entry = statusMap[act.sign_status]
    if (!entry) continue
    events.push({
      id: `act-${act.id}`,
      type: 'act',
      label: entry.label(act.id),
      status: entry.status,
      timestamp: entry.ts(act),
    })
  }
  return events
}

// ─── Contract timeline events ───────────────────────────────

const contractTypeLabels: Record<string, string> = {
  owner_service: '📋 Договор оказания услуг подписан',
  advertiser_campaign: '📝 Договор кампании подписан',
  platform_rules: '✅ Правила платформы приняты',
  privacy_policy: '🔒 Политика конфиденциальности принята',
  tax_agreement: '🧾 Налоговое соглашение подписано',
};

export function deriveContractTimelineEvents(
  contracts: Contract[],
): TimelineEvent[] {
  return contracts
    .filter(
      (c) =>
        c.contract_status === 'signed' &&
        c.signed_at !== null,
    )
    .map((contract) => ({
      id: `contract-${contract.id}`,
      type: 'contract' as const,
      label:
        contractTypeLabels[contract.contract_type] ??
        `📄 Документ #${contract.id} подписан`,
      status: 'success' as TimelineEventStatus,
      timestamp: contract.signed_at!,
    }));
}

// ─── Merge and sort ─────────────────────────────────────────

/** Merge multiple timeline event groups and sort ascending by timestamp. */
export function mergeAndSortTimelineEvents(
  ...groups: TimelineEvent[][]
): TimelineEvent[] {
  return groups
    .flat()
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
}
