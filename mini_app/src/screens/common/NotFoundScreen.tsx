import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { EmptyState } from '@/components/ui'
import { useHaptic } from '@/hooks/useHaptic'

export default function NotFoundScreen() {
  const navigate = useNavigate()
  const haptic = useHaptic()

  return (
    <ScreenShell>
      <EmptyState
        icon="🧭"
        title="Страница не найдена"
        description="Этот маршрут не существует или был удалён"
        action={{
          label: 'На главную',
          onClick: () => {
            haptic.tap()
            navigate('/', { replace: true })
          },
        }}
      />
    </ScreenShell>
  )
}
