import { StatusPill } from './StatusPill'

/* ============================================================
   MobileCard — 3-zone layout for mobile list screens
   Header / Body (stats) / Footer (actions)
   TailwindCSS v4 — web_portal design system
   ============================================================ */

// ─── Stat item ──────────────────────────────────────────────
interface StatItem {
  value: string
  label: string
}

// ─── OwnChannels variant ───────────────────────────────────
interface ChannelMobileCardProps {
  variant: 'channel'
  id: number
  title: string
  username: string
  memberCount: string
  rating: string
  category?: string
  statusPill: { status: Parameters<typeof StatusPill>[0]['status']; label: string }
  headerExtra?: React.ReactNode
  statsExtra?: React.ReactNode
  actions: React.ReactNode
}

// ─── Campaign / Placement variant ──────────────────────────
interface CampaignMobileCardProps {
  variant: 'campaign' | 'request'
  id: number
  channelUsername: string
  adText?: string
  price: string
  date: string
  statusPill: { status: Parameters<typeof StatusPill>[0]['status']; label: string }
  headerExtra?: React.ReactNode
  statsExtra?: React.ReactNode
  actions: React.ReactNode
}

type MobileCardProps = ChannelMobileCardProps | CampaignMobileCardProps

export function MobileCard(props: MobileCardProps) {
  const isChannel = props.variant === 'channel'

  return (
    <div className="flex flex-col gap-3 p-4 bg-harbor-card border border-border rounded-lg shadow-md">
      {/* ─── HEADER: ID + Username/Title + StatusPill ─── */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 min-w-[40px] rounded-full bg-accent-muted flex items-center justify-center text-lg font-semibold text-accent font-display">
          {isChannel
            ? (props.title.charAt(0).toUpperCase())
            : (props.channelUsername.charAt(0).toUpperCase())}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-base font-semibold text-text-primary truncate font-display">
              {isChannel ? props.title : `#${props.id}`}
            </span>
            {props.headerExtra}
          </div>
          <span className="text-xs text-text-secondary truncate block">
            {isChannel ? `@${props.username}` : `@${props.channelUsername}`}
          </span>
          {!isChannel && 'adText' in props && props.adText && (
            <span className="text-xs text-text-tertiary truncate block mt-0.5">{props.adText}</span>
          )}
        </div>

        <StatusPill status={props.statusPill.status} size="sm">
          {props.statusPill.label}
        </StatusPill>
      </div>

      {/* ─── BODY: Stats ─── */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-border">
        {isChannel ? (
          <>
            <Stat value={props.memberCount} label="подписчиков" />
            <Stat value={props.rating} label="рейтинг" />
            <Stat value={props.category ?? '—'} label="категория" />
            {props.statsExtra}
          </>
        ) : (
          <>
            <Stat value={props.price} label="цена" />
            <Stat value={props.date} label="дата" />
            {props.statsExtra ?? <Stat value="—" label="—" />}
          </>
        )}
      </div>

      {/* ─── FOOTER: Actions ─── */}
      <div className="flex gap-2 pt-1">
        {props.actions}
      </div>
    </div>
  )
}

// ─── Internal helpers ──────────────────────────────────────

function Stat({ value, label }: StatItem) {
  return (
    <div className="flex flex-col items-center gap-0.5 min-w-0 text-center">
      <span className="text-sm font-semibold text-text-primary truncate font-display">{value}</span>
      <span className="text-[10px] text-text-tertiary leading-none lowercase">{label}</span>
    </div>
  )
}
