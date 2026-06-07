import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { api, getStoredSession, isDemoMode, storeSession } from './lib/api'
import type { ID } from './lib/types'
import { AuthScreen } from './features/auth'
import { Dashboard } from './features/dashboard'
import { NotificationsView, ProfileView } from './features/account'
import { ProjectsView } from './features/projects'
import { TaskListPage } from './features/task-lists'
import { SideRail, Sidebar, Topbar } from './features/navigation'
import type { ViewKey } from './features/navigation-model'

function App() {
  const [session, setSession] = useState(getStoredSession())
  const [view, setView] = useState<ViewKey>('dashboard')
  const [activeProjectId, setActiveProjectId] = useState<ID | null>(null)
  const [activeTaskId, setActiveTaskId] = useState<ID | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const queryClient = useQueryClient()

  const meQuery = useQuery({
    queryKey: ['me', session?.access],
    queryFn: api.me,
    enabled: !!session || isDemoMode,
  })

  const handleSession = (nextSession: { access: string; refresh: string } | null) => {
    storeSession(nextSession)
    setSession(nextSession)
    queryClient.clear()
  }

  const navigateToView = (nextView: ViewKey) => {
    setView(nextView)
    setActiveProjectId(null)
    setActiveTaskId(null)
  }

  const navigateFromDrawer = (nextView: ViewKey) => {
    navigateToView(nextView)
    setSidebarOpen(false)
  }

  const openProjectWorkspace = (projectId: ID, taskId: ID | null = null) => {
    setActiveProjectId(projectId)
    setActiveTaskId(taskId)
    setView('projects')
  }

  if (!session && !isDemoMode) return <AuthScreen onAuthenticated={handleSession} />

  return (
    <>
      <Toaster richColors position="top-right" />
      <div className="app-shell">
        <SideRail view={view} onOpen={() => setSidebarOpen(true)} onView={navigateToView} />
        {sidebarOpen && (
          <>
            <button className="drawer-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />
            <Sidebar
              user={meQuery.data}
              view={view}
              onView={navigateFromDrawer}
              onClose={() => setSidebarOpen(false)}
              onLogout={() => {
                setSidebarOpen(false)
                handleSession(null)
              }}
            />
          </>
        )}
        <main className="main-shell">
          <Topbar user={meQuery.data} view={view} onView={navigateToView} onOpenNavigation={() => setSidebarOpen(true)} />
          <div className="content">
            {isDemoMode && (
              <div className="alert">
                Demo data mode is active because the frontend is not connected to a live backend.
                Set <strong>VITE_DEMO_MODE=live</strong> and <strong>VITE_API_BASE_URL</strong> to use the Django API.
              </div>
            )}
            {view === 'dashboard' && <Dashboard onView={navigateToView} onOpenProject={openProjectWorkspace} />}
            {view === 'projects' && (
              <ProjectsView
                activeProjectId={activeProjectId}
                activeTaskId={activeTaskId}
                onOpenProject={openProjectWorkspace}
                onBackToProjects={() => navigateToView('projects')}
              />
            )}
            {view === 'my-tasks' && <TaskListPage title="My Tasks" queryKey={['my-tasks']} queryFn={api.myTasks} onOpenTask={openProjectWorkspace} />}
            {view === 'due-soon' && <TaskListPage title="Due Soon" queryKey={['due-soon']} queryFn={api.dueSoon} onOpenTask={openProjectWorkspace} />}
            {view === 'notifications' && <NotificationsView />}
            {view === 'profile' && <ProfileView user={meQuery.data} onLoggedOut={() => handleSession(null)} />}
          </div>
        </main>
      </div>
    </>
  )
}

export default App
