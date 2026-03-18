import { useState } from 'react'

const swatch = (bg: string, label: string) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: 8,
        background: bg,
        border: '1px solid rgba(255,255,255,0.08)',
        flexShrink: 0,
      }}
    />
    <span style={{ fontSize: 10, color: 'var(--rh-text-secondary)', textAlign: 'center', maxWidth: 72 }}>
      {label}
    </span>
  </div>
)

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div style={{ marginBottom: 32 }}>
    <h2
      style={{
        fontFamily: 'var(--rh-font-display)',
        fontSize: 'var(--rh-text-lg)',
        fontWeight: 'var(--rh-weight-semibold)',
        color: 'var(--rh-text-primary)',
        marginBottom: 16,
        borderBottom: '1px solid var(--rh-border)',
        paddingBottom: 8,
      }}
    >
      {title}
    </h2>
    {children}
  </div>
)

export default function DesignSystemTest() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    setTheme(next)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--rh-bg-primary)',
        color: 'var(--rh-text-primary)',
        padding: '24px 16px 80px',
        overflowY: 'auto',
        height: '100%',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <h1
            style={{
              fontFamily: 'var(--rh-font-display)',
              fontSize: 'var(--rh-text-2xl)',
              fontWeight: 'var(--rh-weight-bold)',
            }}
          >
            Dark Harbor
          </h1>
          <p style={{ color: 'var(--rh-text-secondary)', fontSize: 'var(--rh-text-sm)', marginTop: 4 }}>
            Design System — Phase 2
          </p>
        </div>
        <button
          onClick={toggleTheme}
          style={{
            padding: '8px 16px',
            borderRadius: 'var(--rh-radius-md)',
            border: '1px solid var(--rh-border-active)',
            background: 'var(--rh-bg-card)',
            color: 'var(--rh-text-primary)',
            fontSize: 'var(--rh-text-sm)',
            fontFamily: 'var(--rh-font-body)',
            cursor: 'pointer',
          }}
        >
          {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>

      {/* Colors */}
      <Section title="Цвета">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          {swatch('var(--rh-bg-primary)', 'bg-primary')}
          {swatch('var(--rh-bg-secondary)', 'bg-secondary')}
          {swatch('var(--rh-bg-card)', 'bg-card')}
          {swatch('var(--rh-bg-elevated)', 'bg-elevated')}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          {swatch('var(--rh-accent)', 'accent')}
          {swatch('var(--rh-accent-muted)', 'accent-muted')}
          {swatch('var(--rh-accent-2)', 'accent-2')}
          {swatch('var(--rh-success)', 'success')}
          {swatch('var(--rh-success-muted)', 'success-muted')}
          {swatch('var(--rh-warning)', 'warning')}
          {swatch('var(--rh-warning-muted)', 'warning-muted')}
          {swatch('var(--rh-danger)', 'danger')}
          {swatch('var(--rh-danger-muted)', 'danger-muted')}
        </div>
      </Section>

      {/* Typography */}
      <Section title="Типографика">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontFamily: 'var(--rh-font-display)', fontSize: 'var(--rh-text-3xl)', fontWeight: 800 }}>
            Заголовок экрана
          </div>
          <div style={{ fontFamily: 'var(--rh-font-display)', fontSize: 'var(--rh-text-2xl)', fontWeight: 600 }}>
            Название секции
          </div>
          <div style={{ fontFamily: 'var(--rh-font-display)', fontSize: 'var(--rh-text-xl)', fontWeight: 500 }}>
            Подзаголовок
          </div>
          <div style={{ fontFamily: 'var(--rh-font-body)', fontSize: 'var(--rh-text-base)' }}>
            Основной текст тела — DM Sans Regular 15px
          </div>
          <div style={{ fontFamily: 'var(--rh-font-body)', fontSize: 'var(--rh-text-sm)', color: 'var(--rh-text-secondary)' }}>
            Вторичный текст — DM Sans 13px muted
          </div>
          <div style={{ fontFamily: 'var(--rh-font-body)', fontSize: 'var(--rh-text-xs)', color: 'var(--rh-text-tertiary)' }}>
            Подпись — 11px tertiary
          </div>
          <div style={{ fontFamily: 'var(--rh-font-mono)', fontSize: 'var(--rh-text-xl)', fontVariantNumeric: 'tabular-nums' }}>
            12 800 ₽ — JetBrains Mono
          </div>
        </div>
      </Section>

      {/* Shadows & Glass */}
      <Section title="Тени и Glass">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {(['sm', 'md', 'lg'] as const).map((size) => (
            <div
              key={size}
              style={{
                padding: 16,
                borderRadius: 'var(--rh-radius-md)',
                background: 'var(--rh-bg-card)',
                boxShadow: `var(--rh-shadow-${size})`,
                border: '1px solid var(--rh-border)',
                fontSize: 'var(--rh-text-sm)',
                color: 'var(--rh-text-secondary)',
              }}
            >
              shadow-{size}
            </div>
          ))}
          <div
            style={{
              padding: 16,
              borderRadius: 'var(--rh-radius-md)',
              background: 'var(--rh-glass-bg)',
              border: '1px solid var(--rh-glass-border)',
              backdropFilter: `blur(var(--rh-glass-blur))`,
              WebkitBackdropFilter: `blur(var(--rh-glass-blur))`,
              fontSize: 'var(--rh-text-sm)',
              color: 'var(--rh-text-secondary)',
            }}
          >
            Glass morphism card ✨
          </div>
        </div>
      </Section>

      {/* Animations */}
      <Section title="Анимации">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className={`animate-fade-in-up stagger-${i}`}
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--rh-radius-sm)',
                background: 'var(--rh-bg-card)',
                border: '1px solid var(--rh-border)',
                fontSize: 'var(--rh-text-sm)',
                color: 'var(--rh-text-secondary)',
              }}
            >
              Элемент {i} — fadeInUp stagger-{i}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
          <div className="skeleton" style={{ height: 16, width: '100%' }} />
          <div className="skeleton" style={{ height: 16, width: '72%' }} />
          <div className="skeleton" style={{ height: 16, width: '88%' }} />
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div
            className="animate-pulse"
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: 'var(--rh-accent)',
            }}
          />
          <span style={{ fontSize: 'var(--rh-text-sm)', color: 'var(--rh-text-secondary)' }}>
            Pulse indicator
          </span>
          <div
            className="animate-spin"
            style={{
              width: 18,
              height: 18,
              border: '2px solid var(--rh-border-active)',
              borderTopColor: 'var(--rh-accent)',
              borderRadius: '50%',
            }}
          />
          <span style={{ fontSize: 'var(--rh-text-sm)', color: 'var(--rh-text-secondary)' }}>
            Spinner
          </span>
        </div>
      </Section>

      {/* Spacing */}
      <Section title="Spacing (4px grid)">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            ['space-1', '4px'],
            ['space-2', '8px'],
            ['space-3', '12px'],
            ['space-4', '16px'],
            ['space-5', '20px'],
            ['space-6', '24px'],
            ['space-8', '32px'],
            ['space-10', '40px'],
          ].map(([name, size]) => (
            <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  height: 20,
                  width: size,
                  background: 'var(--rh-accent-muted)',
                  border: '1px solid var(--rh-accent)',
                  borderRadius: 2,
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 'var(--rh-text-xs)', color: 'var(--rh-text-secondary)', fontFamily: 'var(--rh-font-mono)' }}>
                --rh-{name} = {size}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* Border radius */}
      <Section title="Border Radius">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          {[
            ['xs', '4px'],
            ['sm', '8px'],
            ['md', '12px'],
            ['lg', '16px'],
            ['xl', '20px'],
            ['2xl', '24px'],
            ['full', '9999px'],
          ].map(([name, val]) => (
            <div key={name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  background: 'var(--rh-accent-muted)',
                  border: '1px solid var(--rh-accent)',
                  borderRadius: val,
                }}
              />
              <span style={{ fontSize: 10, color: 'var(--rh-text-secondary)', fontFamily: 'var(--rh-font-mono)' }}>
                {name}
              </span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
