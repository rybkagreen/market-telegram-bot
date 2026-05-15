import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route, useLocation } from 'react-router-dom'
import { renderWithProviders } from '@/test/utils'
import AdminChannelVerificationDetail from './AdminChannelVerificationDetail'
import * as api from '@/api/admin_channel_verifications'
import type { ChannelVerificationDetailResponse } from '@/api/admin_channel_verifications'

vi.mock('@/api/admin_channel_verifications', async () => {
  const actual = await vi.importActual<typeof api>('@/api/admin_channel_verifications')
  return {
    ...actual,
    getChannelVerificationDetail: vi.fn(),
    verifyChannelManually: vi.fn(),
    rejectChannelVerification: vi.fn(),
  }
})

const getDetailMock = vi.mocked(api.getChannelVerificationDetail)
const verifyMock = vi.mocked(api.verifyChannelManually)
const rejectMock = vi.mocked(api.rejectChannelVerification)

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="probe-pathname">{loc.pathname}</div>
}

function renderDetail(channelId = 42) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/admin/channel-verifications/:id"
        element={<AdminChannelVerificationDetail />}
      />
      <Route path="/admin/channel-verifications" element={<LocationProbe />} />
    </Routes>,
    { initialEntries: [`/admin/channel-verifications/${channelId}`] },
  )
}

const pendingDetail = (channelId = 42): ChannelVerificationDetailResponse => ({
  channel_id: channelId,
  channel_username: 'demo_channel',
  channel_title: 'Demo Channel',
  member_count: 15000,
  owner_id: 7,
  owner_username: 'owner_demo',
  is_blogger_registry_verified: false,
  blogger_registry_verified_at: null,
  blogger_registry_verification_method: null,
  blogger_registry_verified_by_admin_id: null,
  application_number: 'A-2026-04-77',
  member_count_at_verification: null,
  last_blogger_registry_check_at: null,
  history: [
    {
      action: 'blogger_registry_evidence_submitted',
      actor_user_id: 7,
      created_at: '2026-04-10T12:00:00Z',
      extra: null,
    },
  ],
})

beforeEach(() => {
  getDetailMock.mockReset()
  verifyMock.mockReset()
  rejectMock.mockReset()
})

describe('AdminChannelVerificationDetail', () => {
  it('renders channel info and pending registration status', async () => {
    getDetailMock.mockResolvedValue(pendingDetail(42))

    renderDetail(42)

    expect(await screen.findByText(/Заявка на верификацию #42/)).toBeInTheDocument()
    expect(screen.getByText('Demo Channel')).toBeInTheDocument()
    expect(screen.getByText('@demo_channel')).toBeInTheDocument()
    expect(screen.getByText('A-2026-04-77')).toBeInTheDocument()
    expect(screen.getByText('Подана заявка')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Подтвердить/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Отклонить/i })).toBeInTheDocument()
  })

  it('shows validation error and skips API call when reject reason is empty', async () => {
    getDetailMock.mockResolvedValue(pendingDetail(42))

    const user = userEvent.setup()
    renderDetail(42)

    await user.click(await screen.findByRole('button', { name: /Отклонить/i }))

    // Reject form is open — confirmed by inline heading; scope the submit
    // lookup to the form panel so the toggle button (if still present) is excluded.
    const rejectHeading = await screen.findByText('Отклонить заявку')
    const rejectPanel = rejectHeading.parentElement!
    const submitReject = within(rejectPanel).getByRole('button', { name: /^Отклонить$/i })
    await user.click(submitReject)

    expect(await screen.findByText('Укажите причину отказа')).toBeInTheDocument()
    expect(rejectMock).not.toHaveBeenCalled()
  })

  it('submits verify payload with notes and navigates back to list on success', async () => {
    getDetailMock.mockResolvedValue(pendingDetail(42))
    verifyMock.mockResolvedValue({
      channel_id: 42,
      is_blogger_registry_verified: true,
      blogger_registry_verified_at: '2026-04-12T09:00:00Z',
      blogger_registry_verification_method: 'manual_evidence',
      blogger_registry_verified_by_admin_id: 1,
    })

    const user = userEvent.setup()
    renderDetail(42)

    await user.click(await screen.findByRole('button', { name: /Подтвердить/i }))

    const verifyHeading = await screen.findByText('Подтвердить канал')
    const verifyPanel = verifyHeading.parentElement!
    const textarea = within(verifyPanel).getByPlaceholderText(/Внутренние заметки/i)
    await user.type(textarea, 'looks good')

    const submitVerify = within(verifyPanel).getByRole('button', { name: /^Подтвердить$/i })
    await user.click(submitVerify)

    await waitFor(() => {
      expect(verifyMock).toHaveBeenCalledWith(42, { notes: 'looks good' })
    })
    await waitFor(() => {
      expect(screen.getByTestId('probe-pathname')).toHaveTextContent(
        '/admin/channel-verifications',
      )
    })
  })
})
