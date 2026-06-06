import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, Paperclip, Plus } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import type { Attachment, ID, Project, Task, TaskComment, TaskPriority, TaskStatus } from '../lib/types'
import { bytes, formatDateTime, priorityTone, relativeTime, statusTone, titleCase, workflowOrder } from '../lib/utils'
import { ActionRow, Button, ConfirmButton, DataTable, Dialog, EmptyState, Field, Input, Panel, Select, StatusBadge, Textarea } from '../components/ui'
import { invalidateProject, mutationError } from './helpers'
import { Avatar } from './navigation'

const priorityOptions: TaskPriority[] = ['low', 'medium', 'high', 'urgent']

export function ProjectTasks({ project, initialTaskId }: { project: Project; initialTaskId?: ID | null }) {
  const [taskDialog, setTaskDialog] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState<ID | null>(initialTaskId ?? null)
  const detailRef = useRef<HTMLDivElement>(null)
  const tasksQuery = useQuery({ queryKey: ['tasks', project.id], queryFn: () => api.tasks(project.id) })
  const tasks = tasksQuery.data ?? []
  const selectedTask = selectedTaskId ? tasks.find((task) => task.id === selectedTaskId) : undefined

  useEffect(() => {
    if (selectedTask?.id) {
      detailRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    }
  }, [selectedTask?.id])

  return (
    <div className="grid project-tasks-workspace">
      <Panel
        title="Task Overview"
        subtitle="High-level task health before opening individual detail."
        actions={(
          <Button variant="primary" disabled={!project.capabilities?.can_create_task} onClick={() => setTaskDialog(true)}>
            <Plus size={15} /> Task
          </Button>
        )}
      >
        <TaskOverview tasks={tasks} />
      </Panel>
      <Panel title="Kanban Board" subtitle="Select a task card to inspect status, comments, transitions, and attachments.">
        <TaskBoard tasks={tasks} selectedTaskId={selectedTask?.id} onSelect={setSelectedTaskId} />
      </Panel>
      {selectedTask ? (
        <div ref={detailRef}>
          <TaskDetail project={project} task={selectedTask} />
        </div>
      ) : (
        <EmptyState
          title={tasks.length ? 'Select a task for detail' : 'No tasks yet'}
          detail={tasks.length ? 'The board above stays visible while detail opens below it.' : 'Create the first task for this project.'}
        />
      )}
      <TaskDialog project={project} open={taskDialog} onClose={() => setTaskDialog(false)} />
    </div>
  )
}

function TaskOverview({ tasks }: { tasks: Task[] }) {
  const dueSoonCutoffMs = useDueSoonCutoffMs()
  const openStatuses: TaskStatus[] = ['new', 'accepted', 'in_progress', 'on_hold']
  const openTasks = tasks.filter((task) => openStatuses.includes(task.status)).length
  const completedTasks = tasks.filter((task) => task.status === 'completed').length
  const urgentTasks = tasks.filter((task) => task.priority === 'urgent').length
  const dueSoonTasks = tasks.filter((task) => {
    if (!task.due_at || dueSoonCutoffMs === null) return false
    const dueAt = new Date(task.due_at).getTime()
    return Number.isFinite(dueAt) && dueAt <= dueSoonCutoffMs
  }).length
  const statusCounts = workflowOrder.slice(0, 5).map((status) => ({
    status,
    count: tasks.filter((task) => task.status === status).length,
  }))

  return (
    <div className="grid">
      <div className="task-overview-grid">
        <div className="overview-card">
          <span className="muted small strong">Open</span>
          <strong>{openTasks}</strong>
        </div>
        <div className="overview-card">
          <span className="muted small strong">Due soon</span>
          <strong>{dueSoonTasks}</strong>
        </div>
        <div className="overview-card">
          <span className="muted small strong">Urgent</span>
          <strong>{urgentTasks}</strong>
        </div>
        <div className="overview-card">
          <span className="muted small strong">Completed</span>
          <strong>{completedTasks}</strong>
        </div>
      </div>
      <div className="task-status-strip" aria-label="Task status summary">
        {statusCounts.map((item) => (
          <span key={item.status} className="status-chip">
            <StatusBadge value={item.status} tone={statusTone[item.status]} />
            <strong>{item.count}</strong>
          </span>
        ))}
      </div>
    </div>
  )
}

function useDueSoonCutoffMs() {
  const [cutoffMs, setCutoffMs] = useState<number | null>(null)

  useEffect(() => {
    const updateCutoff = () => setCutoffMs(Date.now() + 7 * 24 * 60 * 60 * 1000)
    updateCutoff()
    const intervalId = window.setInterval(updateCutoff, 60_000)
    return () => window.clearInterval(intervalId)
  }, [])

  return cutoffMs
}

function TaskBoard({ tasks, selectedTaskId, onSelect }: { tasks: Task[]; selectedTaskId?: ID; onSelect: (id: ID) => void }) {
  const grouped = workflowOrder.slice(0, 5).map((status) => ({
    status,
    tasks: tasks.filter((task) => task.status === status),
  }))

  return (
    <div className="task-board">
      {grouped.map((group) => (
        <section key={group.status} className="board-column">
          <div className="toolbar" style={{ justifyContent: 'space-between' }}>
            <StatusBadge value={group.status} tone={statusTone[group.status]} />
            <span className="muted small">{group.tasks.length}</span>
          </div>
          {group.tasks.map((task) => (
            <button
              key={task.id}
              data-testid={`task-card-${task.id}`}
              className={`task-card ${selectedTaskId === task.id ? 'selected' : ''}`}
              onClick={() => onSelect(task.id)}
            >
              <div className="strong" style={{ textAlign: 'left' }}>{task.title}</div>
              <div className="toolbar" style={{ justifyContent: 'space-between' }}>
                <StatusBadge value={task.priority} tone={priorityTone[task.priority]} />
                <span className="muted small">{relativeTime(task.due_at)}</span>
              </div>
              <div className="toolbar">
                <Avatar user={task.assignee} />
                <span className="muted small">{task.assignee?.display_name ?? `User ${task.assignee_id}`}</span>
              </div>
            </button>
          ))}
        </section>
      ))}
    </div>
  )
}

function TaskDetail({ project, task }: { project: Project; task: Task }) {
  const queryClient = useQueryClient()
  const [transitionNote, setTransitionNote] = useState('')
  const [commentBody, setCommentBody] = useState('')
  const commentsQuery = useQuery({ queryKey: ['comments', project.id, task.id], queryFn: () => api.comments(project.id, task.id) })
  const attachmentsQuery = useQuery({ queryKey: ['task-attachments', project.id, task.id], queryFn: () => api.taskAttachments(project.id, task.id) })
  const transitionMutation = useMutation({
    mutationFn: (status: TaskStatus) => api.transitionTask(project.id, task.id, status, transitionNote),
    onSuccess: () => {
      setTransitionNote('')
      invalidateProject(queryClient, project.id)
      toast.success('Task transitioned')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const watchMutation = useMutation({
    mutationFn: () => (task.watched ? api.unwatchTask(project.id, task.id) : api.watchTask(project.id, task.id)),
    onSuccess: () => invalidateProject(queryClient, project.id),
  })
  const commentMutation = useMutation({
    mutationFn: () => api.createComment(project.id, task.id, commentBody),
    onSuccess: () => {
      setCommentBody('')
      queryClient.invalidateQueries({ queryKey: ['comments', project.id, task.id] })
      toast.success('Comment added')
    },
    onError: (error) => toast.error(mutationError(error)),
  })

  return (
    <div className="grid">
      <Panel title={task.title} subtitle={task.description || 'No task description'}>
        <div className="detail-list">
          <div className="detail-row"><span>Status</span><StatusBadge value={task.status} tone={statusTone[task.status]} /></div>
          <div className="detail-row"><span>Priority</span><StatusBadge value={task.priority} tone={priorityTone[task.priority]} /></div>
          <div className="detail-row"><span>Assignee</span><strong>{task.assignee?.display_name ?? task.assignee_id}</strong></div>
          <div className="detail-row"><span>Due</span><strong>{formatDateTime(task.due_at)}</strong></div>
        </div>
        <div className="grid" style={{ marginTop: 16 }}>
          <ActionRow>
            <Button disabled={!task.capabilities?.can_watch && !task.capabilities?.can_unwatch} onClick={() => watchMutation.mutate()}>
              <Eye size={15} /> {task.watched ? 'Unwatch' : 'Watch'}
            </Button>
          </ActionRow>
          <Field label="Transition note">
            <Input value={transitionNote} onChange={(event) => setTransitionNote(event.target.value)} placeholder="Optional audit note" />
          </Field>
          <ActionRow>
            {(task.allowed_transitions ?? []).map((status) => (
              <Button key={status} onClick={() => transitionMutation.mutate(status)}>
                Move to {titleCase(status)}
              </Button>
            ))}
          </ActionRow>
        </div>
      </Panel>
      <Panel title="Comments" subtitle="Comments remain available after project close when policy allows.">
        <div className="grid">
          <Field label="New comment">
            <Textarea value={commentBody} onChange={(event) => setCommentBody(event.target.value)} />
          </Field>
          <Button variant="primary" disabled={!task.capabilities?.can_comment || !commentBody.trim()} onClick={() => commentMutation.mutate()}>
            Add comment
          </Button>
          <CommentList project={project} task={task} comments={commentsQuery.data ?? []} />
        </div>
      </Panel>
      <Panel title="Task Attachments" actions={<UploadButton disabled={!task.capabilities?.can_upload_attachment} onUpload={(file) => api.uploadTaskAttachment(project.id, task.id, file).then(() => queryClient.invalidateQueries({ queryKey: ['task-attachments', project.id, task.id] }))} />}>
        <AttachmentList attachments={attachmentsQuery.data ?? []} />
      </Panel>
    </div>
  )
}

function CommentList({ project, task, comments }: { project: Project; task: Task; comments: TaskComment[] }) {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: (commentId: ID) => api.deleteComment(project.id, task.id, commentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['comments', project.id, task.id] }),
  })
  const uploadMutation = useMutation({
    mutationFn: ({ commentId, file }: { commentId: ID; file: File }) => api.uploadCommentAttachment(project.id, task.id, commentId, file),
    onSuccess: () => toast.success('Comment attachment uploaded'),
  })

  if (!comments.length) return <EmptyState title="No comments yet" />
  return (
    <div className="grid">
      {comments.map((comment) => (
        <div key={comment.id} className="panel" style={{ boxShadow: 'none' }}>
          <div className="panel-body grid">
            <div className="toolbar" style={{ justifyContent: 'space-between' }}>
              <div className="toolbar">
                <Avatar user={comment.author} />
                <div>
                  <div className="strong small">{comment.author?.display_name ?? `User ${comment.author_id}`}</div>
                  <div className="muted small">{relativeTime(comment.created_at)}</div>
                </div>
              </div>
              <ActionRow>
                <UploadButton
                  compact
                  disabled={!comment.capabilities?.can_upload_attachment}
                  onUpload={(file) => uploadMutation.mutate({ commentId: comment.id, file })}
                />
                {comment.capabilities?.can_delete && (
                  <ConfirmButton
                    variant="danger"
                    title="Delete comment"
                    description="Delete this comment from the task discussion?"
                    confirmLabel="Delete comment"
                    onConfirm={() => deleteMutation.mutate(comment.id)}
                  >
                    Delete
                  </ConfirmButton>
                )}
              </ActionRow>
            </div>
            <p>{comment.body}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function AttachmentList({ attachments }: { attachments: Attachment[] }) {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: (attachmentId: ID) => api.deleteAttachment(attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries()
      toast.success('Attachment deleted')
    },
  })
  if (!attachments.length) return <EmptyState title="No attachments" />
  return (
    <DataTable>
      <thead>
        <tr>
          <th>File</th>
          <th>Type</th>
          <th>Size</th>
          <th>Uploader</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {attachments.map((attachment) => (
          <tr key={attachment.id}>
            <td className="strong"><Paperclip size={14} /> {attachment.original_filename}</td>
            <td>{attachment.content_type}</td>
            <td>{bytes(attachment.size_bytes)}</td>
            <td>{attachment.uploaded_by?.display_name ?? attachment.uploaded_by_id}</td>
            <td>
              <ActionRow>
                <a className="button" href={api.downloadUrl(attachment.id)}>Download</a>
                {attachment.capabilities?.can_delete && (
                  <ConfirmButton
                    variant="danger"
                    title="Delete attachment"
                    description={`Delete ${attachment.original_filename}?`}
                    confirmLabel="Delete attachment"
                    onConfirm={() => deleteMutation.mutate(attachment.id)}
                  >
                    Delete
                  </ConfirmButton>
                )}
              </ActionRow>
            </td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  )
}

function UploadButton({ disabled, onUpload, compact }: { disabled?: boolean; compact?: boolean; onUpload: (file: File) => Promise<unknown> | void }) {
  return (
    <label className={`button ${disabled ? 'disabled' : ''}`}>
      <Paperclip size={15} /> {compact ? 'Attach' : 'Upload'}
      <input
        type="file"
        disabled={disabled}
        style={{ display: 'none' }}
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) void onUpload(file)
          event.currentTarget.value = ''
        }}
      />
    </label>
  )
}

function TaskDialog({ project, open, onClose }: { project: Project; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const membersQuery = useQuery({ queryKey: ['members', project.id], queryFn: () => api.members(project.id) })
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('medium')
  const [dueAt, setDueAt] = useState('')
  const createMutation = useMutation({
    mutationFn: () =>
      api.createTask(project.id, {
        title,
        description,
        assignee_id: Number(assigneeId),
        priority,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      }),
    onSuccess: () => {
      setTitle('')
      setDescription('')
      invalidateProject(queryClient, project.id)
      toast.success('Task created')
      onClose()
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const assignees = (membersQuery.data ?? []).filter((member) => member.role !== 'viewer')

  return (
    <Dialog title="Create Task" open={open} onClose={onClose}>
      <div className="form-grid">
        <Field label="Title" className="span-2">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} />
        </Field>
        <Field label="Description" className="span-2">
          <Textarea value={description} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <Field label="Assignee">
          <Select value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}>
            <option value="">Select assignee</option>
            {assignees.map((member) => <option key={member.user_id} value={member.user_id}>{member.user?.display_name}</option>)}
          </Select>
        </Field>
        <Field label="Priority">
          <Select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
            {priorityOptions.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
          </Select>
        </Field>
        <Field label="Due at">
          <Input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} />
        </Field>
        <div className="span-2">
          <Button variant="primary" disabled={!title || !assigneeId} onClick={() => createMutation.mutate()}>Create task</Button>
        </div>
      </div>
    </Dialog>
  )
}
