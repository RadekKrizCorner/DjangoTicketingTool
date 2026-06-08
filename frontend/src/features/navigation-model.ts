import { Bell, CalendarClock, ClipboardList, FolderKanban, LayoutDashboard, PanelsTopLeft, Settings } from 'lucide-react'

export type ViewKey = 'dashboard' | 'dashboards' | 'dashboard-tasks' | 'projects' | 'my-tasks' | 'due-soon' | 'notifications' | 'profile'

export const navItems: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'dashboards', label: 'Dashboards', icon: PanelsTopLeft },
  { key: 'projects', label: 'Projects', icon: FolderKanban },
  { key: 'my-tasks', label: 'My Tasks', icon: ClipboardList },
  { key: 'due-soon', label: 'Due Soon', icon: CalendarClock },
  { key: 'notifications', label: 'Notifications', icon: Bell },
  { key: 'profile', label: 'Profile', icon: Settings },
]
