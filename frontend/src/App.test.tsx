import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

let originalScrollIntoView: HTMLElement['scrollIntoView'] | undefined

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    ),
  }
}

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.useRealTimers()
    if (originalScrollIntoView) {
      window.HTMLElement.prototype.scrollIntoView = originalScrollIntoView
    } else {
      delete (window.HTMLElement.prototype as { scrollIntoView?: HTMLElement['scrollIntoView'] }).scrollIntoView
    }
  })

  beforeEach(() => {
    originalScrollIntoView = window.HTMLElement.prototype.scrollIntoView
    localStorage.clear()
    window.history.pushState({}, '', '/')
  })

  async function openNavigation(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: /open navigation/i }))
    return within(await screen.findByRole('navigation', { name: /main/i }))
  }

  async function navigateTo(user: ReturnType<typeof userEvent.setup>, label: RegExp) {
    const nav = await openNavigation(user)
    await user.click(nav.getByRole('button', { name: label }))
  }

  it('renders the demo dashboard with backend scenario navigation', async () => {
    const { user } = renderApp()

    expect(await screen.findByRole('heading', { name: /delivery dashboard/i })).toBeInTheDocument()
    expect(screen.getByText(/demo data mode is active/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open navigation/i })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /main/i })).not.toBeInTheDocument()

    const nav = await openNavigation(user)
    expect(nav.getByRole('button', { name: /^projects$/i })).toBeInTheDocument()
    expect(nav.getByRole('button', { name: /my tasks/i })).toBeInTheDocument()
    expect(nav.getByRole('button', { name: /due soon/i })).toBeInTheDocument()
    expect(nav.getByRole('button', { name: /^notifications$/i })).toBeInTheDocument()
    expect(nav.getByRole('button', { name: /profile/i })).toBeInTheDocument()

    await user.click(nav.getByRole('button', { name: /^projects$/i }))
    expect(await screen.findByRole('heading', { name: /^projects$/i })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /main/i })).not.toBeInTheDocument()
  })

  it('keeps the header notification badge inside a dedicated button', async () => {
    renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    const notificationButton = await screen.findByRole('button', { name: /notifications, 1 unread/i })

    expect(notificationButton).toHaveClass('notification-button')
    expect(within(notificationButton).getByText('1')).toHaveClass('notification-badge')
  })

  it('opens workspace search from a compact mobile topbar trigger', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    expect(screen.getByPlaceholderText(/search projects, tasks, people/i)).toHaveClass('desktop-search-input')

    await user.click(screen.getByRole('button', { name: /open search/i }))

    const dialog = await screen.findByRole('dialog', { name: /search workspace/i })
    const searchInput = within(dialog).getByPlaceholderText(/search projects, tasks, people/i)
    expect(searchInput).toHaveClass('input')
    expect(searchInput).toHaveClass('mobile-search-input')
  })

  it('opens the navigation drawer from the compact topbar menu trigger', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await user.click(screen.getByRole('button', { name: /open menu/i }))

    const nav = within(await screen.findByRole('navigation', { name: /main/i }))
    expect(nav.getByRole('button', { name: /^projects$/i })).toBeInTheDocument()
  })

  it('shows all workspaces in the collapsed rail and marks the selected one', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    const rail = within(screen.getByRole('complementary', { name: /primary navigation/i }))
    const dashboardButton = rail.getByRole('button', { name: /^dashboard$/i })
    const projectsButton = rail.getByRole('button', { name: /^projects$/i })

    expect(dashboardButton).toHaveAttribute('aria-current', 'page')
    expect(projectsButton).not.toHaveAttribute('aria-current')
    expect(rail.getByRole('button', { name: /my tasks/i })).toBeInTheDocument()
    expect(rail.getByRole('button', { name: /due soon/i })).toBeInTheDocument()
    expect(rail.getByRole('button', { name: /^notifications$/i })).toBeInTheDocument()
    expect(rail.getByRole('button', { name: /profile/i })).toBeInTheDocument()

    await user.click(projectsButton)
    expect(await screen.findByRole('heading', { name: /^projects$/i })).toBeInTheDocument()
    expect(projectsButton).toHaveAttribute('aria-current', 'page')
  })

  it('keeps project filters collapsed until requested', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)

    expect(await screen.findByRole('heading', { name: /^projects$/i })).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/^search projects$/i)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /filters/i }))
    expect(screen.getByPlaceholderText(/^search projects$/i)).toBeInTheDocument()
  })

  it('opens projects from a list page into a focused project workspace', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)

    expect(await screen.findByRole('heading', { name: /project list/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /members/i })).not.toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: /open launch control/i }))
    expect(await screen.findByRole('button', { name: /back to projects/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /members/i })).toBeInTheDocument()
  })

  it('adds mobile labels to project list cells for card-style rendering', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)

    const launchRow = await screen.findByTestId('project-row-10')
    expect(launchRow.querySelector('td[data-label="Name"]')).toHaveTextContent(/launch control/i)
    expect(launchRow.querySelector('td[data-label="State"]')).toHaveTextContent(/active/i)
    expect(launchRow.querySelector('td[data-label="Role"]')).toHaveTextContent(/owner/i)
    expect(launchRow.querySelector('td[data-label="Visibility"]')).toHaveTextContent(/private/i)
  })

  it('opens a project task from a shareable URL', async () => {
    window.history.pushState({}, '', '/ui/projects/10/tasks/30')

    renderApp()

    expect(await screen.findByRole('heading', { name: /project workspace/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /finalize deployment checklist/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back to projects/i })).toBeInTheDocument()
  })

  it('updates the URL when opening a task from the dashboard', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await user.click(await screen.findByRole('button', { name: /finalize deployment checklist/i }))

    expect(await screen.findByRole('heading', { name: /finalize deployment checklist/i })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/ui/projects/10/tasks/30')
  })

  it('links dashboard cards, projects, due-soon tasks, and header avatar to their views', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })

    await user.click(screen.getByRole('button', { name: /active projects/i }))
    expect(await screen.findByRole('heading', { name: /^projects$/i })).toBeInTheDocument()

    await navigateTo(user, /^dashboard$/i)
    await user.click(screen.getByRole('button', { name: /my open tasks/i }))
    expect(await screen.findByRole('heading', { name: /my tasks/i, level: 1 })).toBeInTheDocument()

    await navigateTo(user, /^dashboard$/i)
    await user.click(screen.getByRole('button', { name: /unread notifications/i }))
    expect(await screen.findByRole('heading', { name: /^notifications$/i })).toBeInTheDocument()

    await navigateTo(user, /^dashboard$/i)
    await user.click(screen.getByRole('button', { name: /^launch control/i }))
    expect(await screen.findByRole('button', { name: /back to projects/i })).toBeInTheDocument()

    await navigateTo(user, /^dashboard$/i)
    await user.click(screen.getByRole('button', { name: /finalize deployment checklist/i }))
    expect(await screen.findByRole('heading', { name: /finalize deployment checklist/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /open profile/i }))
    expect(await screen.findByRole('heading', { name: /^profile$/i })).toBeInTheDocument()
  })

  it('surfaces project capabilities, lifecycle, audit, and attachment limits', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)
    expect(await screen.findByRole('heading', { name: /^projects$/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /open launch control/i }))

    expect(await screen.findByRole('button', { name: /^task$/i })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: /lifecycle/i }))
    expect(await screen.findByRole('button', { name: /close project/i })).toBeEnabled()
    expect(screen.getByLabelText(/publish at/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /audit/i }))
    expect(await screen.findByText(/project\.created/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /attachments/i }))
    expect(await screen.findByText(/allowed uploads/i)).toBeInTheDocument()
    expect(screen.getByText(/max file mb/i)).toBeInTheDocument()
  })

  it('allows a permitted task transition and comment from the task detail view', async () => {
    const scrollIntoView = vi.fn()
    window.HTMLElement.prototype.scrollIntoView = scrollIntoView
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)
    await user.click(await screen.findByRole('button', { name: /open launch control/i }))
    expect(await screen.findByRole('heading', { name: /task overview/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /kanban board/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/transition note/i)).not.toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: /finalize deployment checklist/i }))
    expect(await screen.findByRole('heading', { name: /finalize deployment checklist/i })).toBeInTheDocument()
    expect(screen.getByText(/selected task detail/i)).toBeInTheDocument()
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled())

    await user.type(screen.getByLabelText(/transition note/i), 'Verified in UI test')
    await user.click(screen.getByRole('button', { name: /move to on hold/i }))
    await waitFor(() => expect(screen.getByRole('button', { name: /move to in progress/i })).toBeInTheDocument())

    await user.type(screen.getByLabelText(/new comment/i), 'Frontend workflow test comment')
    await user.click(screen.getByRole('button', { name: /add comment/i }))
    expect(await screen.findByText(/frontend workflow test comment/i)).toBeInTheDocument()
  })

  it('requires confirmation before deleting a project and keeps focus inside the confirm dialog', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)
    await user.click(await screen.findByRole('button', { name: /open launch control/i }))

    const deleteButton = await screen.findByRole('button', { name: /^delete$/i })
    await user.click(deleteButton)

    const dialog = await screen.findByRole('dialog', { name: /delete project/i })
    expect(within(dialog).getByText(/delete launch control/i)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: /cancel/i })).toHaveFocus()

    await user.keyboard('{Tab}{Tab}{Tab}')
    expect(dialog).toContainElement(document.activeElement as HTMLElement | SVGElement | null)

    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /delete project/i })).not.toBeInTheDocument())
    expect(deleteButton).toHaveFocus()
    expect(screen.getByRole('heading', { name: /launch control/i })).toBeInTheDocument()
  })

  it('closes navigation drawer and create-project dialog with Escape while restoring focus', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await user.click(menuButton)
    expect(await screen.findByRole('navigation', { name: /main/i })).toBeInTheDocument()

    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('navigation', { name: /main/i })).not.toBeInTheDocument())
    expect(menuButton).toHaveFocus()

    await navigateTo(user, /^projects$/i)
    const projectButton = screen.getByRole('button', { name: /^project$/i })
    await user.click(projectButton)
    expect(await screen.findByRole('dialog', { name: /create project/i })).toBeInTheDocument()

    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /create project/i })).not.toBeInTheDocument())
    expect(projectButton).toHaveFocus()
  })

  it('computes task overview due-soon counts from the current render time', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-05-25T10:00:00.000Z'))
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^projects$/i)
    await user.click(await screen.findByRole('button', { name: /open launch control/i }))

    const overview = await screen.findByRole('heading', { name: /task overview/i })
    const overviewPanel = overview.closest('section')
    expect(overviewPanel).toBeTruthy()
    expect(within(overviewPanel as HTMLElement).getByText(/^due soon$/i).nextElementSibling).toHaveTextContent('0')
  })

  it('uses a selectable timezone preference instead of free text', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await user.click(screen.getByRole('button', { name: /open profile/i }))

    const timezone = await screen.findByLabelText(/timezone/i)
    expect(timezone.tagName).toBe('SELECT')
    await user.selectOptions(timezone, 'UTC')
    expect(timezone).toHaveValue('UTC')
    expect(screen.getByRole('option', { name: /europe\/prague/i })).toBeInTheDocument()
  })

  it('opens dashboards from top-level navigation and renders demo widgets', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)

    expect(await screen.findByRole('heading', { name: /^dashboards$/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /open dashboard menu/i }))
    expect(await screen.findByText(/favorites/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/search dashboards/i)).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /select operations dashboard/i })).toHaveAttribute('aria-current', 'page')
    await user.type(screen.getByLabelText(/search dashboards/i), 'support')
    expect(await screen.findByRole('button', { name: /select support triage/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /select my team/i })).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /open tickets/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /technician workload/i })).toBeInTheDocument()
    expect(screen.getByText(/project members/i)).toBeInTheDocument()
  })

  it('blocks overlapping dashboard layout edits', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await screen.findByRole('heading', { name: /open tickets/i })
    await user.click(await screen.findByRole('button', { name: /edit layout/i }))

    const openTickets = await screen.findByTestId('dashboard-widget-open-tickets')
    expect(openTickets).toHaveStyle({ gridColumn: '1 / span 3' })
    await user.click(await screen.findByRole('button', { name: /move open tickets right/i }))

    expect(openTickets).toHaveStyle({ gridColumn: '1 / span 3' })
    expect(await screen.findByText(/widgets cannot overlap/i)).toBeInTheDocument()
  })

  it('blocks overlapping pointer drag and resize edits', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await screen.findByRole('heading', { name: /open tickets/i })
    await user.click(await screen.findByRole('button', { name: /edit layout/i }))

    const openTickets = await screen.findByTestId('dashboard-widget-open-tickets')
    const grid = openTickets.closest('.dashboard-grid')
    expect(grid).toBeTruthy()
    Object.defineProperty(grid, 'clientWidth', { configurable: true, value: 1200 })

    const widgetHeader = within(openTickets).getByRole('heading', { name: /open tickets/i }).closest('.dashboard-widget-header')
    expect(widgetHeader).toBeTruthy()
    fireEvent.pointerDown(widgetHeader as HTMLElement, { clientX: 0, clientY: 0 })
    fireEvent.pointerMove(window, { clientX: 100, clientY: 0 })
    fireEvent.pointerUp(window)

    expect(openTickets).toHaveStyle({ gridColumn: '1 / span 3' })
    expect(await screen.findByText(/widgets cannot overlap/i)).toBeInTheDocument()

    fireEvent.pointerDown(await screen.findByRole('button', { name: /drag resize open tickets/i }), { clientX: 0, clientY: 0 })
    fireEvent.pointerMove(window, { clientX: 100, clientY: 0 })
    fireEvent.pointerUp(window)

    expect(openTickets).toHaveStyle({ gridColumn: '1 / span 3' })
  })

  it('saves a valid dashboard layout and restores it after switching dashboards', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await user.click(await screen.findByRole('button', { name: /new dashboard/i }))

    const dialog = await screen.findByRole('dialog', { name: /create dashboard/i })
    const nameInput = within(dialog).getByLabelText(/name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Layout Persistence')
    await user.click(within(dialog).getByRole('button', { name: /create dashboard/i }))

    expect(await screen.findByRole('heading', { name: /layout persistence/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /add widget/i }))
    await user.click(within(await screen.findByRole('dialog', { name: /add widget/i })).getByRole('button', { name: /add widget/i }))

    const widget = await screen.findByTestId('dashboard-widget-new-metric')
    expect(widget).toHaveStyle({ gridColumn: '1 / span 4' })
    await user.click(await screen.findByRole('button', { name: /edit layout/i }))
    await user.click(await screen.findByRole('button', { name: /move new metric right/i }))
    expect(widget).toHaveStyle({ gridColumn: '2 / span 4' })
    await user.click(await screen.findByRole('button', { name: /save layout/i }))
    expect(await screen.findByText(/layout saved/i)).toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: /open dashboard menu/i }))
    await user.click(await screen.findByRole('button', { name: /select operations dashboard/i }))
    await user.click(await screen.findByRole('button', { name: /open dashboard menu/i }))
    await user.type(screen.getByLabelText(/search dashboards/i), 'layout persistence')
    await user.click(await screen.findByRole('button', { name: /select layout persistence/i }))

    expect(await screen.findByTestId('dashboard-widget-new-metric')).toHaveStyle({ gridColumn: '2 / span 4' })
  })

  it('shows owner-only sharing controls', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)

    expect(await screen.findByRole('button', { name: /^share$/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /open dashboard menu/i }))
    await user.click(await screen.findByRole('button', { name: /select my team/i }))

    expect(await screen.findByText(/viewer access/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^share$/i })).not.toBeInTheDocument()
  })

  it('navigates from widget drilldown to a filtered task list', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await user.click(await screen.findByRole('button', { name: /open matching tasks for open tickets/i }))

    expect(await screen.findByRole('heading', { name: /dashboard task results/i, level: 1 })).toBeInTheDocument()
    expect(screen.getByText(/filtered by dashboard widget/i)).toBeInTheDocument()
    expect(window.location.pathname).toBe('/ui/dashboard-tasks')
  })

  it('creates a dashboard from the dashboards workspace', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await user.click(await screen.findByRole('button', { name: /new dashboard/i }))

    const dialog = await screen.findByRole('dialog', { name: /create dashboard/i })
    const nameInput = within(dialog).getByLabelText(/name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Release Metrics')
    await user.click(within(dialog).getByRole('button', { name: /create dashboard/i }))

    expect(await screen.findByRole('heading', { name: /release metrics/i })).toBeInTheDocument()
  })

  it('removes dashboard share rows before saving sharing changes', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await user.click(await screen.findByRole('button', { name: /^share$/i }))

    const dialog = await screen.findByRole('dialog', { name: /share dashboard/i })
    expect(within(dialog).getAllByText(/project members/i).length).toBeGreaterThan(1)
    await user.click(within(dialog).getByRole('button', { name: /remove share 1/i }))
    await user.click(within(dialog).getByRole('button', { name: /save sharing/i }))

    await waitFor(() => expect(screen.queryByRole('dialog', { name: /share dashboard/i })).not.toBeInTheDocument())
    expect(screen.queryByText(/project members/i)).not.toBeInTheDocument()
  })

  it('adds dashboard shares by selecting named projects and users', async () => {
    const { user } = renderApp()

    await screen.findByRole('heading', { name: /delivery dashboard/i })
    await navigateTo(user, /^dashboards$/i)
    await user.click(await screen.findByRole('button', { name: /^share$/i }))

    const dialog = await screen.findByRole('dialog', { name: /share dashboard/i })
    expect(within(dialog).queryByLabelText(/project id/i)).not.toBeInTheDocument()
    expect(within(dialog).queryByLabelText(/user id/i)).not.toBeInTheDocument()

    await within(dialog).findByRole('option', { name: /public feedback/i })
    await user.selectOptions(within(dialog).getByLabelText(/project/i), '11')
    expect(within(dialog).getByRole('button', { name: /add share/i })).toBeEnabled()
    await user.selectOptions(within(dialog).getByLabelText(/access/i), 'editor')
    await user.click(within(dialog).getByRole('button', { name: /add share/i }))

    const publicShareRow = within(dialog).getByText(/editor access/i).closest('.detail-row')
    expect(publicShareRow).toHaveTextContent(/public feedback/i)
    expect(within(dialog).getByRole('button', { name: /add share/i })).toBeDisabled()

    await user.selectOptions(within(dialog).getByLabelText(/target/i), 'user')
    await user.type(within(dialog).getByLabelText(/search users/i), 'nina')
    await user.click(await within(dialog).findByRole('button', { name: /select nina member/i }))
    await user.click(within(dialog).getByRole('button', { name: /add share/i }))

    expect(within(dialog).getByText(/nina member/i)).toBeInTheDocument()
    expect(within(dialog).getByText(/nina.member@example.com/i)).toBeInTheDocument()
  })
})
