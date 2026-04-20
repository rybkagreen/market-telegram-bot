import { useNavigate } from 'react-router-dom'
import { Icon } from '@shared/ui'
import { useRecommendedChannels } from '@/hooks/useChannelQueries'
import type { ChannelResponse } from '@/lib/types'

function avatarColorFor(ch: ChannelResponse): string {
  // Deterministic OKLCH hue by id so the avatar stays stable per channel.
  const hue = (ch.id * 47) % 360
  return `oklch(0.68 0.16 ${hue})`
}

function formatSubs(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace('.0', '')}K`
  return String(n)
}

function ChannelCard({ ch }: { ch: ChannelResponse }) {
  const navigate = useNavigate()
  const initial = (ch.title || ch.username || '?').slice(0, 1).toUpperCase()
  const tier =
    ch.member_count > 100_000
      ? { label: 'Premium', clr: 'bg-accent-2-muted text-accent-2' }
      : ch.last_er > 5
        ? { label: 'Verified', clr: 'bg-success-muted text-success' }
        : null

  return (
    <button
      type="button"
      onClick={() => navigate(`/adv/campaigns/new/category?prefill_channel=${ch.id}`)}
      className="group text-left rounded-md p-3.5 transition-colors hover:bg-harbor-secondary cursor-pointer flex flex-col gap-2.5"
    >
      <div className="flex items-center gap-2.5">
        <div
          className="w-9 h-9 rounded-lg grid place-items-center text-white font-display font-bold text-sm flex-shrink-0"
          style={{ background: avatarColorFor(ch) }}
        >
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[12.5px] font-semibold text-text-primary truncate">
            {ch.username ? `@${ch.username}` : ch.title}
          </div>
          <div className="text-[10.5px] text-text-tertiary mt-0.5 truncate">{ch.category ?? 'Без категории'}</div>
        </div>
      </div>
      {tier && (
        <div
          className={`self-start text-[9.5px] font-semibold tracking-[0.05em] uppercase px-1.5 py-0.5 rounded-sm ${tier.clr}`}
        >
          {tier.label}
        </div>
      )}
      <div className="flex gap-3 pt-2 border-t border-dashed border-border">
        <div>
          <div className="text-[9.5px] text-text-tertiary uppercase tracking-[0.05em]">Подписч.</div>
          <div className="text-xs font-semibold text-text-primary font-mono mt-0.5">{formatSubs(ch.member_count)}</div>
        </div>
        <div>
          <div className="text-[9.5px] text-text-tertiary uppercase tracking-[0.05em]">ER</div>
          <div className="text-xs font-semibold text-success font-mono mt-0.5">{ch.last_er.toFixed(1)}%</div>
        </div>
      </div>
    </button>
  )
}

export function RecommendedChannels() {
  const navigate = useNavigate()
  const { data, isLoading } = useRecommendedChannels(5)
  const items = data?.items ?? []

  return (
    <section className="rounded-xl bg-harbor-card border border-border overflow-hidden">
      <header className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div>
          <h3 className="font-display text-[15px] font-semibold text-text-primary">
            Рекомендовано для размещения
          </h3>
          <p className="text-[11px] text-text-tertiary mt-0.5">
            Подобрано по вашим прошлым кампаниям
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/adv/campaigns/new/channels')}
          className="flex items-center gap-1 text-[12px] text-accent hover:text-accent-hover cursor-pointer"
        >
          В каталог <Icon name="chevron-right" size={12} />
        </button>
      </header>
      {isLoading ? (
        <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Загружаем…</div>
      ) : items.length === 0 ? (
        <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Каналы пока не подобраны.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-0 divide-x divide-border p-3">
          {items.map((ch) => (
            <ChannelCard key={ch.id} ch={ch} />
          ))}
        </div>
      )}
    </section>
  )
}
