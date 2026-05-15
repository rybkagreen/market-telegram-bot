import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route, useLocation } from 'react-router-dom'
import { renderWithProviders } from '@/test/utils'
import AdminChannelVerificationsList from './AdminChannelVerificationsList'
import * as api from '@/api/admin_channel_verifications'
import type { ChannelVerificationListResponse } from '@/api/admin_channel_verifications'

vi.mock('@/api/admin_channel_verifications', async () => {
  const actual = await vi.importActual<typeof api>('@/api/admin_channel_verifications')
  return {
    ...actual,
    listChannelVerifications: vi.fn(),
  }
})

const listMock = vi.mocked(api.listChannelVerifications)

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="probe-pathname">{loc.pathname}</div>
}

function renderList() {
  return renderWithProviders(
    <Routes>
      <Route path="/admin/channel-verifications" element={<AdminChannelVerificationsList />} />
      <Route
        path="/admin/channel-verifications/:id"
        element={<LocationProbe />}
      />
    </Routes>,
    { initialEntries: ['/admin/channel-verifications'] },
  )
}

const buildList = (
  items: ChannelVerificationListResponse['items'],
  total = items.length,
): ChannelVerificationListResponse => ({
  items,
  total,
  limit: 20,
  offset: 0,
})

beforeEach(() => {
  listMock.mockReset()
})

describe('AdminChannelVerificationsList', () => {
  it('renders pending entries with total count and channel titles', async () => {
    listMock.mockResolvedValue(
      buildList([
        {
          channel_id: 101,
          channel_username: 'rus_marketing',
          channel_title: 'Russian Marketing Daily',
          member_count: 12345,
          owner_id: 7,
          owner_username: 'alice',
          application_number: 'A-2026-04-1',
          submitted_at: '2026-04-01T10:00:00Z',
          status: 'pending_review',
        },
        {
          channel_id: 102,
          channel_username: null,
          channel_title: 'Crypto Insights',
          member_count: 50000,
          owner_id: 8,
          owner_username: null,
          application_number: 'A-2026-04-2',
          submitted_at: '2026-04-02T11:00:00Z',
          status: 'pending_review',
        },
      ]),
    )

    renderList()

    expect(await screen.findByText('Russian Marketing Daily')).toBeInTheDocument()
    expect(screen.getByText('Crypto Insights')).toBeInTheDocument()
    expect(screen.getByText(/всего: 2/i)).toBeInTheDocument()
    expect(listMock).toHaveBeenCalledWith({
      status: 'pending_review',
      limit: 20,
      offset: 0,
    })
  })

  it('renders empty state when there are no entries', async () => {
    listMock.mockResolvedValue(buildList([], 0))

    renderList()

    expect(await screen.findByText('Заявки не найдены')).toBeInTheDocument()
    expect(screen.getByText(/Нет ожидающих проверки заявок/)).toBeInTheDocument()
  })

  it('navigates to detail page when row is clicked', async () => {
    listMock.mockResolvedValue(
      buildList([
        {
          channel_id: 555,
          channel_username: 'demo',
          channel_title: 'Demo Channel',
          member_count: 11000,
          owner_id: 1,
          owner_username: 'bob',
          application_number: 'A-555',
          submitted_at: '2026-04-05T09:00:00Z',
          status: 'pending_review',
        },
      ]),
    )

    const user = userEvent.setup()
    renderList()

    const row = await screen.findByRole('button', { name: /Demo Channel/i })
    await user.click(row)

    await waitFor(() => {
      expect(screen.getByTestId('probe-pathname')).toHaveTextContent(
        '/admin/channel-verifications/555',
      )
    })
  })
})
