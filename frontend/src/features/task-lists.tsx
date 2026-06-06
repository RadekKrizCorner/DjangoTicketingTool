import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Star } from 'lucide-react'
import type { ID, Task } from '../lib/types'
import { formatDateTime, priorityTone, statusTone } from '../lib/utils'
import { Button, DataTable, EmptyState, Panel, StatusBadge } from '../components/ui'
import { PageHeading } from './layout'

export function TaskListPage({
  title,
  queryKey,
  queryFn,
  onOpenTask,
}: {
  title: string
  queryKey: unknown[]
  queryFn: () => Promise<Task[]>
  onOpenTask: (projectId: ID, taskId: ID) => void
}) {
  const tasksQuery = useQuery({ queryKey, queryFn })
  return (
    <>
      <PageHeading title={title} detail="Direct task endpoints for assigned and due-soon work." />
      <Panel title={title}>
        <TaskTable tasks={tasksQuery.data ?? []} onOpenTask={onOpenTask} />
      </Panel>
    </>
  )
}

function TaskTable({ tasks, onOpenTask }: { tasks: Task[]; onOpenTask: (projectId: ID, taskId: ID) => void }) {
  if (!tasks.length) return <EmptyState title="No tasks in this queue" />
  return (
    <DataTable>
      <thead>
        <tr>
          <th>Task</th>
          <th>Project</th>
          <th>Status</th>
          <th>Priority</th>
          <th>Due</th>
          <th>Watch</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((task) => (
          <tr key={task.id}>
            <td>
              <div className="strong">{task.title}</div>
              <div className="muted small">{task.description}</div>
            </td>
            <td>{task.project?.name ?? task.project_id}</td>
            <td><StatusBadge value={task.status} tone={statusTone[task.status]} /></td>
            <td><StatusBadge value={task.priority} tone={priorityTone[task.priority]} /></td>
            <td>{formatDateTime(task.due_at)}</td>
            <td>{task.watched ? <Star size={16} fill="currentColor" /> : '—'}</td>
            <td>
              <Button aria-label={`Open ${task.title}`} onClick={() => onOpenTask(task.project_id, task.id)}>
                Open <ChevronRight size={14} />
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  )
}
