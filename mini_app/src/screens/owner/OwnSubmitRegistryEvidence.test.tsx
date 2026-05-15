import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route, useLocation } from 'react-router-dom'
import { renderWithProviders } from '@/test/utils'
import OwnSubmitRegistryEvidence from './OwnSubmitRegistryEvidence'
import * as channelsApi from '@/api/channels'

vi.mock('@/hooks/useHaptic', () => ({
  useHaptic: () => ({
    tap: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    select: vi.fn(),
  }),
}))

vi.mock('@/api/channels', async () => {
  const actual = await vi.importActual<typeof channelsApi>('@/api/channels')
  return {
    ...actual,
    submitRegistryEvidence: vi.fn(),
  }
})

const submitMock = vi.mocked(channelsApi.submitRegistryEvidence)

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="probe-pathname">{loc.pathname}</div>
}

function renderForm(channelId = 99) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/own/channels/:id/registry"
        element={<OwnSubmitRegistryEvidence />}
      />
      <Route path="/own/channels/:id" element={<LocationProbe />} />
    </Routes>,
    { initialEntries: [`/own/channels/${channelId}/registry`] },
  )
}

beforeEach(() => {
  submitMock.mockReset()
})

describe('OwnSubmitRegistryEvidence', () => {
  it('renders application_number, registry_url, notes fields and submit button', () => {
    renderForm(99)

    expect(screen.getByPlaceholderText('A-2026-04-12345')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('https://rkn.gov.ru/...')).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText('Дополнительные сведения для администратора'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Отправить заявку/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Отмена/i })).toBeInTheDocument()
  })

  it('submits payload with trimmed inputs and navigates to /own/channels/:id on success', async () => {
    submitMock.mockResolvedValue({
      status: 'pending_review',
      channel_id: 99,
      application_number: 'A-2026-04-7777',
      submitted_at: '2026-04-15T10:00:00Z',
    })

    const user = userEvent.setup()
    renderForm(99)

    await user.type(screen.getByPlaceholderText('A-2026-04-12345'), '  A-2026-04-7777  ')
    await user.type(screen.getByPlaceholderText('https://rkn.gov.ru/...'), 'https://rkn.gov.ru/case/7777')
    await user.type(
      screen.getByPlaceholderText('Дополнительные сведения для администратора'),
      ' Сертификат прилагается ',
    )

    await user.click(screen.getByRole('button', { name: /Отправить заявку/i }))

    await waitFor(() => {
      expect(submitMock).toHaveBeenCalledWith(99, {
        application_number: 'A-2026-04-7777',
        registry_url: 'https://rkn.gov.ru/case/7777',
        notes: 'Сертификат прилагается',
      })
    })
    await waitFor(() => {
      expect(screen.getByTestId('probe-pathname')).toHaveTextContent('/own/channels/99')
    })
  })

  it('shows validation error and skips API call when application_number is empty', async () => {
    const user = userEvent.setup()
    renderForm(99)

    await user.click(screen.getByRole('button', { name: /Отправить заявку/i }))

    expect(await screen.findByText('Укажите номер заявления')).toBeInTheDocument()
    expect(submitMock).not.toHaveBeenCalled()
  })
})
