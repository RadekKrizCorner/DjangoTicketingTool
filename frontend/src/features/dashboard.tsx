import { useQuery } from '@tanstack/react-query'
import { Bell, ClipboardList, FolderKanban, Plus } from 'lucide-react'
import { api } from '../lib/api'
import type { ID, Project, Task } from '../lib/types'
import { relativeTime } from '../lib/utils'
import { Button, EmptyState, Panel, StatusBadge } from '../components/ui'
import { PageHeading } from './layout'
import type { ViewKey } from './navigation-model'

export function Dashboard({
  onView,
  onOpenProject,
}: {
  onView: (view: ViewKey) => void
  onOpenProject: (projectId: ID, taskId?: ID | null) => void
}) {
  const projectsQuery = useQuery({ queryKey: ['projects', {}], queryFn: () => api.projects({}) })
  const myTasksQuery = useQuery({ queryKey: ['my-tasks'], queryFn: api.myTasks })
  const dueQuery = useQuery({ queryKey: ['due-soon'], queryFn: api.dueSoon })
  const notificationsQuery = useQuery({ queryKey: ['notifications'], queryFn: api.notifications })

  const projects = projectsQuery.data ?? []
  const activeProjects = projects.filter((project) => project.state === 'active')
  const myTasks = myTasksQuery.data ?? []
  const dueSoon = dueQuery.data ?? []
  const unread = notificationsQuery.data?.filter((item) => !item.read_at).length ?? 0

  return (
    <>
      <PageHeading
        title="Delivery Dashboard"
        detail="Operational overview across visible projects, task queues, and notifications."
        actions={<Button variant="primary" onClick={() => onView('projects')}><Plus size={15} /> New project</Button>}
      />
      <div className="grid cols-3">
        <Metric title="Active projects" value={activeProjects.length} detail={`${projects.length} visible`} icon={FolderKanban} onClick={() => onView('projects')} />
        <Metric title="My open tasks" value={myTasks.filter((task) => !['completed', 'cancelled'].includes(task.status)).length} detail={`${dueSoon.length} due soon`} icon={ClipboardList} onClick={() => onView('my-tasks')} />
        <Metric title="Unread notifications" value={unread} detail="Watcher and schedule events" icon={Bell} onClick={() => onView('notifications')} />
      </div>
      <div className="grid cols-2">
        <Panel title="Recent Projects" actions={<Button onClick={() => onView('projects')}>Open projects</Button>}>
          <ProjectMiniList projects={projects.slice(0, 5)} onOpenProject={onOpenProject} />
        </Panel>
        <Panel title="Due Soon" actions={<Button onClick={() => onView('due-soon')}>View queue</Button>}>
          <TaskMiniList tasks={dueSoon.slice(0, 6)} onOpenTask={onOpenProject} />
        </Panel>
      </div>
    </>
  )
}

export function Metric({ title, value, detail, icon: Icon, onClick }: { title: string; value: number; detail: string; icon: typeof Bell; onClick?: () => void }) {
  const content = (
    <div className="toolbar" style={{ justifyContent: 'space-between' }}>
      <div>
        <div className="muted small strong">{title}</div>
        <div style={{ fontSize: 34, fontWeight: 880, marginTop: 6 }}>{value}</div>
        <div className="muted small">{detail}</div>
      </div>
      <span className="avatar"><Icon size={18} /></span>
    </div>
  )

  if (!onClick) return <Panel>{content}</Panel>

  return (
    <button className="panel metric-card" onClick={onClick}>
      <div className="panel-body">{content}</div>
    </button>
  )
}

function ProjectMiniList({ projects, onOpenProject }: { projects: Project[]; onOpenProject: (projectId: ID) => void }) {
  if (!projects.length) return <EmptyState title="No visible projects" />
  return (
    <div className="grid">
      {projects.map((project) => (
        <button key={project.id} className="detail-row row-action" onClick={() => onOpenProject(project.id)}>
          <span><strong>{project.name}</strong><br /><span className="muted small">{project.my_membership?.role ?? 'public'}</span></span>
          <StatusBadge value={project.state} tone={project.state === 'active' ? 'tone-success' : 'tone-danger'} />
        </button>
      ))}
    </div>
  )
}

function TaskMiniList({ tasks, onOpenTask }: { tasks: Task[]; onOpenTask: (projectId: ID, taskId: ID) => void }) {
  if (!tasks.length) return <EmptyState title="No due-soon tasks" />
  return (
    <div className="grid">
      {tasks.map((task) => (
        <button key={task.id} className="detail-row row-action" onClick={() => onOpenTask(task.project_id, task.id)}>
          <span><strong>{task.title}</strong><br /><span className="muted small">{task.project?.name}</span></span>
          <span className="muted small">{relativeTime(task.due_at)}</span>
        </button>
      ))}
    </div>
  )
}
