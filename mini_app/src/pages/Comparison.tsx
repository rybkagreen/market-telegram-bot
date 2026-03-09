import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { channelsApi, type ComparisonChannelItem } from '../api/channels'

const METRIC_LABELS: Record<string, string> = {
  member_count: '👥 Подписчики',
  avg_views: '👁 Просмотры',
  er: '📈 ER %',
  post_frequency: '📝 Постов/день',
  price_per_post: '💰 Цена/пост',
  price_per_1k_subscribers: '💰 Цена/1К',
}

export default function Comparison() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const channelIds = params.get('ids')?.split(',').map(Number) ?? []

  const { data, isLoading, error } = useQuery({
    queryKey: ['comparison', channelIds],
    queryFn: () => channelsApi.compare(channelIds),
    enabled: channelIds.length >= 2,
  })

  if (channelIds.length < 2) {
    return (
      <div className="comparison-page">
        <h1>📊 Сравнение каналов</h1>
        <p>Выберите минимум 2 канала для сравнения</p>
        <button onClick={() => navigate('/channels')} className="primary-btn">
          ← К каталогу каналов
        </button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="comparison-page">
        <h1>📊 Сравнение каналов</h1>
        <p>Загрузка данных...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="comparison-page">
        <h1>📊 Сравнение каналов</h1>
        <p className="error">Ошибка загрузки данных</p>
        <button onClick={() => navigate(-1)} className="secondary-btn">
          ← Назад
        </button>
      </div>
    )
  }

  return (
    <div className="comparison-page">
      <h1>📊 Сравнение каналов</h1>

      <div className="comparison-table-wrapper">
        <table className="comparison-table">
          <thead>
            <tr>
              <th className="metric-col">Метрика</th>
              {data.channels.map(ch => (
                <th key={ch.id} className="channel-col">
                  {ch.title || `@${ch.username || ch.id}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(METRIC_LABELS).map(([key, label]) => (
              <tr key={key}>
                <td className="metric-label">{label}</td>
                {data.channels.map(ch => {
                  const val = ch[key as keyof ComparisonChannelItem] as number
                  const isBest = ch.is_best[key]
                  return (
                    <td key={ch.id} className={isBest ? 'best-value' : ''}>
                      {isBest && <span className="best-indicator">🟢 </span>}
                      <span className="metric-value">
                        {typeof val === 'number' ? val.toLocaleString('ru-RU') : val}
                      </span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.recommendation && (
        <div className="recommendation">
          <h3>🏆 Рекомендация</h3>
          <p className="recommendation-channel">
            <strong>{data.recommendation.channel_name}</strong>
          </p>
          <p className="recommendation-reason">{data.recommendation.reason}</p>
        </div>
      )}

      <div className="comparison-actions">
        <button
          className="primary-btn"
          onClick={() => navigate('/campaigns/create')}
        >
          ➕ Добавить в кампанию
        </button>
      </div>

      <div className="comparison-nav">
        <button onClick={() => navigate(-1)} className="secondary-btn">
          ← Назад
        </button>
        <button onClick={() => navigate('/channels')} className="text-btn">
          К каталогу каналов
        </button>
      </div>
    </div>
  )
}
