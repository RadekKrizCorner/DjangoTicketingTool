import type { ViewKey } from '../features/navigation-model'
import type { ID } from './types'

export type ProjectTab = 'tasks' | 'members' | 'lifecycle' | 'audit' | 'attachments'

export type AppRoute = {
  view: ViewKey
  projectId: ID | null
  taskId: ID | null
  projectTab: ProjectTab
}

const defaultRoute: AppRoute = {
  view: 'dashboard',
  projectId: null,
  taskId: null,
  projectTab: 'tasks',
}

const viewPaths: Record<ViewKey, string> = {
  dashboard: '/',
  projects: '/projects',
  'my-tasks': '/my-tasks',
  'due-soon': '/due-soon',
  notifications: '/notifications',
  profile: '/profile',
}

const validProjectTabs = new Set<ProjectTab>(['tasks', 'members', 'lifecycle', 'audit', 'attachments'])

function parseId(value: string | undefined): ID | null {
  if (!value) return null
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function stripUiBase(pathname: string): string {
  if (pathname === '/ui') return '/'
  if (pathname.startsWith('/ui/')) return pathname.slice('/ui'.length) || '/'
  return pathname || '/'
}

export function routeFromPath(pathname: string): AppRoute {
  const path = stripUiBase(pathname)
  const parts = path.split('/').filter(Boolean)

  if (parts.length === 0) return defaultRoute
  if (parts[0] === 'projects') {
    const projectId = parseId(parts[1])
    if (!projectId) return { ...defaultRoute, view: 'projects' }
    if (parts[2] === 'tasks') {
      return { view: 'projects', projectId, taskId: parseId(parts[3]), projectTab: 'tasks' }
    }
    const tab = validProjectTabs.has(parts[2] as ProjectTab) ? (parts[2] as ProjectTab) : 'tasks'
    return { view: 'projects', projectId, taskId: null, projectTab: tab }
  }

  const view = Object.entries(viewPaths).find(([, viewPath]) => viewPath === path)?.[0] as ViewKey | undefined
  if (!view) return defaultRoute
  return { ...defaultRoute, view }
}

export function pathForRoute(route: AppRoute): string {
  let path = viewPaths[route.view]
  if (route.view === 'projects' && route.projectId) {
    if (route.taskId) {
      path = `/projects/${route.projectId}/tasks/${route.taskId}`
    } else if (route.projectTab !== 'tasks') {
      path = `/projects/${route.projectId}/${route.projectTab}`
    } else {
      path = `/projects/${route.projectId}`
    }
  }
  return `/ui${path === '/' ? '/' : path}`
}

export function routeForView(view: ViewKey): AppRoute {
  return { ...defaultRoute, view }
}
