import { useEffect, useState } from 'react'
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
import { pathForRoute, routeForView, routeFromPath, type AppRoute, type ProjectTab } from './lib/routes'

function App() {
  const [session, setSession] = useState(getStoredSession())
  const [route, setRoute] = useState<AppRoute>(() => routeFromPath(window.location.pathname))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const queryClient = useQueryClient()
  const view = route.view

  const meQuery = useQuery({
    queryKey: ['me', session?.access],
    queryFn: api.me,
    enabled: !!session || isDemoMode,
  })

  useEffect(() => {
    const syncRoute = () => setRoute(routeFromPath(window.location.pathname))
    window.addEventListener('popstate', syncRoute)
    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  const navigateToRoute = (nextRoute: AppRoute) => {
    const nextPath = pathForRoute(nextRoute)
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }
    setRoute(nextRoute)
  }

  const handleSession = (nextSession: { access: string; refresh: string } | null) => {
    storeSession(nextSession)
    setSession(nextSession)
    queryClient.clear()
  }

  const navigateToView = (nextView: ViewKey) => {
    navigateToRoute(routeForView(nextView))
  }

  const navigateFromDrawer = (nextView: ViewKey) => {
    navigateToView(nextView)
    setSidebarOpen(false)
  }

  const openProjectWorkspace = (projectId: ID, taskId: ID | null = null) => {
    navigateToRoute({ view: 'projects', projectId, taskId, projectTab: 'tasks' })
  }

  const openProjectTab = (projectId: ID, projectTab: ProjectTab) => {
    navigateToRoute({ view: 'projects', projectId, taskId: null, projectTab })
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
              <div className="alert mobile-hidden">
                Demo data mode is active because the frontend is not connected to a live backend.
                Set <strong>VITE_DEMO_MODE=live</strong> and <strong>VITE_API_BASE_URL</strong> to use the Django API.
              </div>
            )}
            {view === 'dashboard' && <Dashboard onView={navigateToView} onOpenProject={openProjectWorkspace} />}
            {view === 'projects' && (
              <ProjectsView
                activeProjectId={route.projectId}
                activeTaskId={route.taskId}
                activeProjectTab={route.projectTab}
                onOpenProject={openProjectWorkspace}
                onOpenProjectTab={openProjectTab}
                onBackToProjects={() => navigateToRoute(routeForView('projects'))}
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
