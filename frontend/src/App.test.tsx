import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
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
})
