import {
  type Attachment,
  type AttachmentLimits,
  type AuditLog,
  type AuthSession,
  type CurrentUser,
  type Envelope,
  type ID,
  type Notification,
  type Paginated,
  type Profile,
  type Project,
  type ProjectFilters,
  type ProjectMembership,
  type Role,
  type StatusResponse,
  type Task,
  type TaskComment,
  type TaskPriority,
  type TaskStatus,
  type UserSummary,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== 'live'
const TOKEN_KEY = 'rkriz.frontend.tokens'

type RequestOptions = {
  method?: string
  body?: unknown
  token?: string | null
  formData?: FormData
  retryOnAuth?: boolean
}

export class ApiError extends Error {
  status: number
  errors: { code: string; detail: string; field: string | null }[]

  constructor(status: number, errors: { code: string; detail: string; field: string | null }[]) {
    super(errors[0]?.detail ?? 'Request failed')
    this.status = status
    this.errors = errors
  }
}

export function getStoredSession(): AuthSession | null {
  const raw = localStorage.getItem(TOKEN_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthSession
  } catch {
    localStorage.removeItem(TOKEN_KEY)
    return null
  }
}

export function storeSession(session: AuthSession | null) {
  if (!session) {
    localStorage.removeItem(TOKEN_KEY)
    return
  }
  localStorage.setItem(TOKEN_KEY, JSON.stringify(session))
}

function isTokenNotValid(status: number, payload: { errors?: { code: string }[] }) {
  return status === 401 && (payload.errors ?? []).some((error) => error.code === 'token_not_valid')
}

async function refreshStoredSession(): Promise<AuthSession | null> {
  const session = getStoredSession()
  if (!session?.refresh) return null

  const response = await fetch(`${API_BASE}/users/token/refresh/`, {
    method: 'POST',
    headers: new Headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ refresh: session.refresh }),
  })

  if (!response.ok) {
    storeSession(null)
    return null
  }

  const payload = (await response.json()) as Envelope<AuthSession>
  const nextSession = {
    access: payload.data.access,
    refresh: payload.data.refresh ?? session.refresh,
  }
  storeSession(nextSession)
  return nextSession
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers()
  const token = options.token ?? getStoredSession()?.access
  let body: BodyInit | undefined

  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.formData) {
    body = options.formData
  } else if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body,
  })

  if (response.status === 204) return undefined as T

  const payload = await response.json()
  if (!response.ok) {
    if (options.retryOnAuth !== false && token && isTokenNotValid(response.status, payload)) {
      const nextSession = await refreshStoredSession()
      if (nextSession) {
        return request<T>(path, { ...options, token: nextSession.access, retryOnAuth: false })
      }
    }
    throw new ApiError(response.status, payload.errors ?? [])
  }
  return payload as T
}

function queryString(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== 'all') {
      search.set(key, String(value))
    }
  }
  const value = search.toString()
  return value ? `?${value}` : ''
}

type DemoState = {
  currentUser: CurrentUser
  profile: Profile
  users: CurrentUser[]
  projects: Project[]
  memberships: ProjectMembership[]
  tasks: Task[]
  comments: TaskComment[]
  attachments: Attachment[]
  notifications: Notification[]
  auditLogs: AuditLog[]
  nextId: number
}

const now = new Date('2026-06-06T10:00:00.000Z')
const iso = (offsetHours = 0) => new Date(now.getTime() + offsetHours * 60 * 60 * 1000).toISOString()

const demoUsers: CurrentUser[] = [
  { id: 1, email: 'demo.admin@example.com', display_name: 'Demo Admin', is_staff: true },
  { id: 2, email: 'marta.manager@example.com', display_name: 'Marta Manager', is_staff: false },
  { id: 3, email: 'nina.member@example.com', display_name: 'Nina Member', is_staff: false },
  { id: 4, email: 'vic.viewer@example.com', display_name: 'Vic Viewer', is_staff: false },
  { id: 5, email: 'owen.public@example.com', display_name: 'Owen Public', is_staff: false },
]

function userSummary(id: ID): UserSummary {
  const user = demoState.users.find((item) => item.id === id) ?? demoState.currentUser
  return { id: user.id, email: user.email, display_name: user.display_name }
}

const baseCapabilities = {
  can_update: false,
  can_delete: false,
  can_manage_members: false,
  can_transfer_ownership: false,
  can_schedule: false,
  can_close: false,
  can_reopen: false,
  can_read_audit_log: false,
  can_create_task: false,
  can_comment: false,
  can_upload_task_attachment: false,
  can_upload_comment_attachment: false,
}

const taskCapabilityBase = {
  can_update: false,
  can_delete: false,
  can_transition: false,
  can_watch: false,
  can_unwatch: false,
  can_comment: false,
  can_upload_attachment: false,
}

const allowedTransitions: Record<TaskStatus, TaskStatus[]> = {
  new: ['accepted', 'cancelled'],
  accepted: ['in_progress', 'on_hold', 'cancelled'],
  in_progress: ['on_hold', 'completed', 'cancelled'],
  on_hold: ['in_progress', 'cancelled'],
  completed: ['accepted'],
  cancelled: ['accepted'],
}

const demoState: DemoState = {
  currentUser: demoUsers[0],
  profile: { timezone: 'Europe/Prague' },
  users: demoUsers,
  projects: [],
  memberships: [],
  tasks: [],
  comments: [],
  attachments: [],
  notifications: [],
  auditLogs: [],
  nextId: 100,
}

function seedDemoState() {
  const projects: Project[] = [
    {
      id: 10,
      name: 'Launch Control',
      description: 'Release coordination workspace for API docs, deployment checks, and support.',
      owner_id: 1,
      visibility: 'private',
      state: 'active',
      public_comment_policy: 'members_only',
      publish_at: iso(24),
      published_at: null,
      close_at: iso(240),
      closed_at: null,
      created_at: iso(-120),
      updated_at: iso(-2),
    },
    {
      id: 11,
      name: 'Public Feedback',
      description: 'Public project for authenticated customer feedback and support triage.',
      owner_id: 1,
      visibility: 'public',
      state: 'active',
      public_comment_policy: 'authenticated_users',
      publish_at: null,
      published_at: iso(-72),
      close_at: null,
      closed_at: null,
      created_at: iso(-96),
      updated_at: iso(-5),
    },
    {
      id: 12,
      name: 'Archive Migration',
      description: 'Closed migration project retained for audit history and comment follow-up.',
      owner_id: 2,
      visibility: 'private',
      state: 'closed',
      public_comment_policy: 'members_only',
      publish_at: null,
      published_at: iso(-240),
      close_at: null,
      closed_at: iso(-12),
      created_at: iso(-360),
      updated_at: iso(-12),
    },
  ]

  demoState.projects = projects
  demoState.memberships = [
    membership(20, 10, 1, 'owner'),
    membership(21, 10, 2, 'manager'),
    membership(22, 10, 3, 'member'),
    membership(23, 10, 4, 'viewer'),
    membership(24, 11, 1, 'owner'),
    membership(25, 11, 3, 'member'),
    membership(26, 12, 2, 'owner'),
    membership(27, 12, 1, 'manager'),
  ]
  demoState.tasks = [
    task(30, 10, 2, 'Finalize deployment checklist', 'Confirm migration, worker, beat, and docs readiness.', 'in_progress', 'urgent', iso(8), true),
    task(31, 10, 3, 'Polish OpenAPI reviewer path', 'Make endpoint docs easy to scan before release.', 'accepted', 'high', iso(20), true),
    task(32, 10, 3, 'Validate attachment quotas', 'Exercise project and global upload limit behavior.', 'new', 'medium', iso(42), false),
    task(33, 11, 3, 'Collect public beta comments', 'Review authenticated public feedback and summarize issues.', 'on_hold', 'medium', iso(18), false),
    task(34, 12, 1, 'Archive audit export', 'Confirm old migration audit events are readable.', 'completed', 'low', null, true),
  ]
  demoState.comments = [
    comment(40, 30, 2, 'Worker health checks are green in staging.'),
    comment(41, 30, 1, 'Keep the release compose verification attached to this task.'),
    comment(42, 33, 5, 'Public comment policy is useful for authenticated beta users.'),
  ]
  demoState.attachments = [
    attachment(50, 30, null, 1, 'release-checklist.log', 'text/plain', 1842),
    attachment(51, null, 41, 1, 'compose-output.txt', 'text/plain', 902),
  ]
  demoState.notifications = [
    notification(60, 'task_assigned', 'Task assigned: Finalize deployment checklist', 'Task Finalize deployment checklist was assigned to you.', 10, 30, null, iso(-3)),
    notification(61, 'task_comment_created', 'New comment on task: Finalize deployment checklist', 'A teammate added a release note.', 10, 30, iso(-1), iso(-6)),
  ]
  demoState.auditLogs = [
    audit(70, 1, 'project.created', 'project', 10, 10, {}, { name: 'Launch Control' }, iso(-120)),
    audit(71, 1, 'membership.added', 'project_membership', 21, 10, {}, { role: 'manager' }, iso(-118)),
    audit(72, 1, 'task.created', 'task', 30, 10, {}, { title: 'Finalize deployment checklist' }, iso(-72)),
    audit(73, 2, 'task.transitioned', 'task', 30, 10, { status: 'accepted' }, { status: 'in_progress' }, iso(-4)),
  ]
}

function membership(id: ID, projectId: ID, userId: ID, role: Role): ProjectMembership {
  return {
    id,
    project_id: projectId,
    user_id: userId,
    user: userSummary(userId),
    role,
    created_at: iso(-100),
    updated_at: iso(-10),
  }
}

function task(
  id: ID,
  projectId: ID,
  assigneeId: ID,
  title: string,
  description: string,
  status: TaskStatus,
  priority: TaskPriority,
  dueAt: string | null,
  watched: boolean,
): Task {
  const project = demoState.projects.find((item) => item.id === projectId)
  return {
    id,
    project_id: projectId,
    project: project
      ? { id: project.id, name: project.name, state: project.state, visibility: project.visibility }
      : undefined,
    title,
    description,
    assignee_id: assigneeId,
    assignee: userSummary(assigneeId),
    status,
    priority,
    due_at: dueAt,
    created_at: iso(-72),
    updated_at: iso(-2),
    watched,
    allowed_transitions: allowedTransitions[status],
  }
}

function comment(id: ID, taskId: ID, authorId: ID, body: string): TaskComment {
  return {
    id,
    task_id: taskId,
    author_id: authorId,
    author: userSummary(authorId),
    body,
    created_at: iso(-5),
    updated_at: iso(-5),
  }
}

function attachment(
  id: ID,
  taskId: ID | null,
  commentId: ID | null,
  uploadedById: ID,
  filename: string,
  contentType: string,
  size: number,
): Attachment {
  return {
    id,
    task_id: taskId,
    comment_id: commentId,
    uploaded_by_id: uploadedById,
    uploaded_by: userSummary(uploadedById),
    original_filename: filename,
    content_type: contentType,
    size_bytes: size,
    checksum_sha256: `demo-${id}`,
    created_at: iso(-4),
  }
}

function notification(
  id: ID,
  type: string,
  title: string,
  message: string,
  projectId: ID | null,
  taskId: ID | null,
  readAt: string | null,
  createdAt: string,
): Notification {
  return { id, type, title, message, project_id: projectId, task_id: taskId, read_at: readAt, created_at: createdAt }
}

function audit(
  id: ID,
  actorId: ID | null,
  action: string,
  entityType: string,
  entityId: ID,
  projectId: ID | null,
  before: Record<string, unknown>,
  after: Record<string, unknown>,
  createdAt: string,
): AuditLog {
  return {
    id,
    actor_id: actorId,
    actor: actorId ? userSummary(actorId) : null,
    action,
    entity_type: entityType,
    entity_id: entityId,
    project_id: projectId,
    before,
    after,
    metadata: {},
    ip_address: null,
    user_agent: 'demo',
    idempotency_key: '',
    created_at: createdAt,
  }
}

seedDemoState()

function nextId() {
  demoState.nextId += 1
  return demoState.nextId
}

function currentMembership(projectId: ID) {
  return demoState.memberships.find(
    (item) => item.project_id === projectId && item.user_id === demoState.currentUser.id,
  )
}

function decorateProject(project: Project): Project {
  const member = currentMembership(project.id)
  const isOwner = member?.role === 'owner' && project.owner_id === demoState.currentUser.id
  const canWriteTask = project.state === 'active' && !!member && ['owner', 'manager', 'member'].includes(member.role)
  const canComment =
    !!member ||
    (project.visibility === 'public' && project.public_comment_policy === 'authenticated_users')
  const lifecycle = isOwner || demoState.currentUser.is_staff
  return {
    ...project,
    owner: userSummary(project.owner_id),
    my_membership: member ? { id: member.id, role: member.role } : null,
    capabilities: {
      ...baseCapabilities,
      can_update: isOwner,
      can_delete: isOwner,
      can_manage_members: isOwner,
      can_transfer_ownership: isOwner,
      can_schedule: lifecycle,
      can_close: lifecycle && project.state === 'active',
      can_reopen: lifecycle && project.state === 'closed',
      can_read_audit_log: isOwner,
      can_create_task: canWriteTask,
      can_comment: canComment,
      can_upload_task_attachment: canWriteTask,
      can_upload_comment_attachment: canComment,
    },
  }
}

function decorateTask(taskItem: Task): Task {
  const project = decorateProject(demoState.projects.find((item) => item.id === taskItem.project_id)!)
  const member = currentMembership(taskItem.project_id)
  const canWrite = project.state === 'active' && !!member && ['owner', 'manager', 'member'].includes(member.role)
  const canComment = !!project.capabilities?.can_comment
  return {
    ...taskItem,
    project: { id: project.id, name: project.name, state: project.state, visibility: project.visibility },
    assignee: userSummary(taskItem.assignee_id),
    allowed_transitions: canWrite ? allowedTransitions[taskItem.status] : [],
    capabilities: {
      ...taskCapabilityBase,
      can_update: canWrite,
      can_delete: canWrite,
      can_transition: canWrite,
      can_watch: !!member && !taskItem.watched,
      can_unwatch: !!member && taskItem.watched,
      can_comment: canComment,
      can_upload_attachment: canWrite,
    },
  }
}

function decorateComment(item: TaskComment): TaskComment {
  const taskItem = demoState.tasks.find((taskRow) => taskRow.id === item.task_id)
  const project = taskItem ? decorateProject(demoState.projects.find((row) => row.id === taskItem.project_id)!) : null
  const member = taskItem ? currentMembership(taskItem.project_id) : null
  const canManagerDelete = !!member && ['owner', 'manager'].includes(member.role)
  return {
    ...item,
    author: userSummary(item.author_id),
    capabilities: {
      can_update: item.author_id === demoState.currentUser.id,
      can_delete: item.author_id === demoState.currentUser.id || canManagerDelete,
      can_upload_attachment: !!project?.capabilities?.can_comment,
    },
  }
}

function decorateAttachment(item: Attachment): Attachment {
  const taskId =
    item.task_id ??
    demoState.comments.find((commentRow) => commentRow.id === item.comment_id)?.task_id ??
    null
  const taskItem = taskId ? demoState.tasks.find((row) => row.id === taskId) : null
  const member = taskItem ? currentMembership(taskItem.project_id) : null
  const canManagerDelete = !!member && ['owner', 'manager'].includes(member.role)
  return {
    ...item,
    uploaded_by: userSummary(item.uploaded_by_id),
    capabilities: {
      can_download: !!taskItem,
      can_delete: item.uploaded_by_id === demoState.currentUser.id || canManagerDelete,
    },
  }
}

function page<T>(data: T[]): Paginated<T> {
  return {
    data,
    meta: {
      pagination: {
        count: data.length,
        page: 1,
        page_size: 100,
        total_pages: 1,
        next: null,
        previous: null,
      },
    },
  }
}

function delay<T>(value: T) {
  return new Promise<T>((resolve) => window.setTimeout(() => resolve(value), 80))
}

const liveApi = {
  login: (payload: { email: string; password: string }) =>
    request<Envelope<AuthSession>>('/users/token/', { method: 'POST', body: payload }).then((res) => res.data),
  register: (payload: { email: string; password: string; password_confirm: string; display_name: string }) =>
    request<Envelope<UserSummary>>('/users/register/', { method: 'POST', body: payload }).then((res) => res.data),
  logout: (refresh: string) =>
    request<Envelope<StatusResponse>>('/users/logout/', { method: 'POST', body: { refresh } }).then((res) => res.data),
  me: () => request<Envelope<CurrentUser>>('/users/me/').then((res) => res.data),
  profile: () => request<Envelope<Profile>>('/users/profile/').then((res) => res.data),
  updateProfile: (payload: Profile) =>
    request<Envelope<Profile>>('/users/profile/', { method: 'PATCH', body: payload }).then((res) => res.data),
  changePassword: (payload: { old_password: string; new_password: string; new_password_confirm: string }) =>
    request<Envelope<StatusResponse>>('/users/password/', { method: 'POST', body: payload }).then((res) => res.data),
  passwordResetRequest: (payload: { email: string }) =>
    request<Envelope<StatusResponse>>('/users/password-reset/request/', { method: 'POST', body: payload }).then((res) => res.data),
  passwordResetConfirm: (payload: { uid: string; token: string; new_password: string; new_password_confirm: string }) =>
    request<Envelope<StatusResponse>>('/users/password-reset/confirm/', { method: 'POST', body: payload }).then((res) => res.data),
  searchUsers: (query: string) => request<Paginated<UserSummary>>(`/users/search/${queryString({ q: query })}`).then((res) => res.data),
  projects: (filters: ProjectFilters) => request<Paginated<Project>>(`/projects/${queryString(filters)}`).then((res) => res.data),
  project: (id: ID) => request<Envelope<Project>>(`/projects/${id}/`).then((res) => res.data),
  createProject: (payload: Partial<Project>) => request<Envelope<Project>>('/projects/', { method: 'POST', body: payload }).then((res) => res.data),
  updateProject: (id: ID, payload: Partial<Project>) => request<Envelope<Project>>(`/projects/${id}/`, { method: 'PATCH', body: payload }).then((res) => res.data),
  deleteProject: (id: ID) => request<void>(`/projects/${id}/`, { method: 'DELETE' }),
  closeProject: (id: ID) => request<Envelope<Project>>(`/projects/${id}/close/`, { method: 'POST', body: {} }).then((res) => res.data),
  reopenProject: (id: ID) => request<Envelope<Project>>(`/projects/${id}/reopen/`, { method: 'POST', body: {} }).then((res) => res.data),
  schedulePublish: (id: ID, publish_at: string) =>
    request<Envelope<Project>>(`/projects/${id}/publish-schedule/`, { method: 'PUT', body: { publish_at } }).then((res) => res.data),
  cancelPublish: (id: ID) => request<void>(`/projects/${id}/publish-schedule/`, { method: 'DELETE' }),
  scheduleClose: (id: ID, close_at: string) =>
    request<Envelope<Project>>(`/projects/${id}/close-schedule/`, { method: 'PUT', body: { close_at } }).then((res) => res.data),
  cancelClose: (id: ID) => request<void>(`/projects/${id}/close-schedule/`, { method: 'DELETE' }),
  members: (projectId: ID) => request<Paginated<ProjectMembership>>(`/projects/${projectId}/members/`).then((res) => res.data),
  addMember: (projectId: ID, payload: { user_id: ID; role: Role }) =>
    request<Envelope<ProjectMembership>>(`/projects/${projectId}/members/`, { method: 'POST', body: payload }).then((res) => res.data),
  updateMember: (projectId: ID, membershipId: ID, role: Role) =>
    request<Envelope<ProjectMembership>>(`/projects/${projectId}/members/${membershipId}/`, { method: 'PATCH', body: { role } }).then((res) => res.data),
  removeMember: (projectId: ID, membershipId: ID) => request<void>(`/projects/${projectId}/members/${membershipId}/`, { method: 'DELETE' }),
  transferOwnership: (projectId: ID, new_owner_id: ID) =>
    request<Envelope<Project>>(`/projects/${projectId}/ownership-transfer/`, { method: 'POST', body: { new_owner_id } }).then((res) => res.data),
  auditLog: (projectId: ID) => request<Paginated<AuditLog>>(`/projects/${projectId}/audit-log/`).then((res) => res.data),
  attachmentLimits: (projectId: ID) => request<Envelope<AttachmentLimits>>(`/projects/${projectId}/attachments/limits/`).then((res) => res.data),
  tasks: (projectId: ID) => request<Paginated<Task>>(`/projects/${projectId}/tasks/`).then((res) => res.data),
  task: (projectId: ID, taskId: ID) => request<Envelope<Task>>(`/projects/${projectId}/tasks/${taskId}/`).then((res) => res.data),
  createTask: (projectId: ID, payload: { title: string; description?: string; assignee_id: ID; priority?: TaskPriority; due_at?: string | null }) =>
    request<Envelope<Task>>(`/projects/${projectId}/tasks/`, { method: 'POST', body: payload }).then((res) => res.data),
  updateTask: (projectId: ID, taskId: ID, payload: Partial<Task> & { assignee_id?: ID }) =>
    request<Envelope<Task>>(`/projects/${projectId}/tasks/${taskId}/`, { method: 'PATCH', body: payload }).then((res) => res.data),
  deleteTask: (projectId: ID, taskId: ID) => request<void>(`/projects/${projectId}/tasks/${taskId}/`, { method: 'DELETE' }),
  transitionTask: (projectId: ID, taskId: ID, status: TaskStatus, note: string) =>
    request<Envelope<Task>>(`/projects/${projectId}/tasks/${taskId}/transition/`, { method: 'POST', body: { status, note } }).then((res) => res.data),
  watchTask: (projectId: ID, taskId: ID) => request<Envelope<{ watched: boolean }>>(`/projects/${projectId}/tasks/${taskId}/watch/`, { method: 'POST' }).then((res) => res.data),
  unwatchTask: (projectId: ID, taskId: ID) => request<Envelope<{ watched: boolean }>>(`/projects/${projectId}/tasks/${taskId}/watch/`, { method: 'DELETE' }).then((res) => res.data),
  myTasks: () => request<Paginated<Task>>('/tasks/my/').then((res) => res.data),
  dueSoon: () => request<Paginated<Task>>('/tasks/due-soon/').then((res) => res.data),
  comments: (projectId: ID, taskId: ID) => request<Paginated<TaskComment>>(`/projects/${projectId}/tasks/${taskId}/comments/`).then((res) => res.data),
  createComment: (projectId: ID, taskId: ID, body: string) =>
    request<Envelope<TaskComment>>(`/projects/${projectId}/tasks/${taskId}/comments/`, { method: 'POST', body: { body } }).then((res) => res.data),
  updateComment: (projectId: ID, taskId: ID, commentId: ID, body: string) =>
    request<Envelope<TaskComment>>(`/projects/${projectId}/tasks/${taskId}/comments/${commentId}/`, { method: 'PATCH', body: { body } }).then((res) => res.data),
  deleteComment: (projectId: ID, taskId: ID, commentId: ID) =>
    request<void>(`/projects/${projectId}/tasks/${taskId}/comments/${commentId}/`, { method: 'DELETE' }),
  taskAttachments: (projectId: ID, taskId: ID) => request<Paginated<Attachment>>(`/projects/${projectId}/tasks/${taskId}/attachments/`).then((res) => res.data),
  commentAttachments: (projectId: ID, taskId: ID, commentId: ID) =>
    request<Paginated<Attachment>>(`/projects/${projectId}/tasks/${taskId}/comments/${commentId}/attachments/`).then((res) => res.data),
  uploadTaskAttachment: (projectId: ID, taskId: ID, file: File) => {
    const formData = new FormData()
    formData.set('file', file)
    return request<Envelope<Attachment>>(`/projects/${projectId}/tasks/${taskId}/attachments/`, { method: 'POST', formData }).then((res) => res.data)
  },
  uploadCommentAttachment: (projectId: ID, taskId: ID, commentId: ID, file: File) => {
    const formData = new FormData()
    formData.set('file', file)
    return request<Envelope<Attachment>>(`/projects/${projectId}/tasks/${taskId}/comments/${commentId}/attachments/`, { method: 'POST', formData }).then((res) => res.data)
  },
  deleteAttachment: (attachmentId: ID) => request<void>(`/attachments/${attachmentId}/`, { method: 'DELETE' }),
  downloadUrl: (attachmentId: ID) => `${API_BASE}/attachments/${attachmentId}/download/`,
  notifications: () => request<Paginated<Notification>>('/notifications/').then((res) => res.data),
  readNotification: (id: ID) => request<Envelope<Notification>>(`/notifications/${id}/read/`, { method: 'POST' }).then((res) => res.data),
  readAllNotifications: () => request<Envelope<StatusResponse>>('/notifications/read-all/', { method: 'POST' }).then((res) => res.data),
}

const demoApi = {
  login: async () => delay({ access: 'demo-access-token', refresh: 'demo-refresh-token' }),
  register: async (payload: { email: string; display_name: string }) => {
    const user = { id: nextId(), email: payload.email, display_name: payload.display_name, is_staff: false }
    demoState.users.push(user)
    demoState.currentUser = user
    return delay(userSummary(user.id))
  },
  logout: async () => delay({ status: 'logged_out' }),
  me: async () => delay(demoState.currentUser),
  profile: async () => delay(demoState.profile),
  updateProfile: async (payload: Profile) => {
    demoState.profile = payload
    return delay(demoState.profile)
  },
  changePassword: async () => delay({ status: 'password_changed' }),
  passwordResetRequest: async () => delay({ status: 'accepted' }),
  passwordResetConfirm: async () => delay({ status: 'password_reset' }),
  searchUsers: async (query: string) => {
    const normalized = query.toLowerCase()
    return delay(demoState.users.filter((user) => `${user.email} ${user.display_name}`.toLowerCase().includes(normalized)).map((user) => userSummary(user.id)))
  },
  projects: async (filters: ProjectFilters) => {
    let rows = demoState.projects.map(decorateProject)
    if (filters.visibility && filters.visibility !== 'all') rows = rows.filter((item) => item.visibility === filters.visibility)
    if (filters.role && filters.role !== 'all') rows = rows.filter((item) => item.my_membership?.role === filters.role)
    if (filters.search) {
      const query = filters.search.toLowerCase()
      rows = rows.filter((item) => `${item.name} ${item.description}`.toLowerCase().includes(query))
    }
    return delay(rows)
  },
  project: async (id: ID) => delay(decorateProject(demoState.projects.find((item) => item.id === id)!)),
  createProject: async (payload: Partial<Project>) => {
    const project: Project = {
      id: nextId(),
      name: payload.name ?? 'Untitled Project',
      description: payload.description ?? '',
      owner_id: demoState.currentUser.id,
      visibility: payload.visibility ?? 'private',
      state: 'active',
      public_comment_policy: payload.public_comment_policy ?? 'members_only',
      publish_at: null,
      published_at: null,
      close_at: null,
      closed_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    demoState.projects.unshift(project)
    demoState.memberships.push(membership(nextId(), project.id, demoState.currentUser.id, 'owner'))
    return delay(decorateProject(project))
  },
  updateProject: async (id: ID, payload: Partial<Project>) => {
    const project = demoState.projects.find((item) => item.id === id)!
    Object.assign(project, payload, { updated_at: new Date().toISOString() })
    return delay(decorateProject(project))
  },
  deleteProject: async (id: ID) => {
    demoState.projects = demoState.projects.filter((item) => item.id !== id)
    return delay(undefined)
  },
  closeProject: async (id: ID) => {
    const project = demoState.projects.find((item) => item.id === id)!
    Object.assign(project, { state: 'closed', close_at: null, closed_at: new Date().toISOString() })
    return delay(decorateProject(project))
  },
  reopenProject: async (id: ID) => {
    const project = demoState.projects.find((item) => item.id === id)!
    Object.assign(project, { state: 'active', close_at: null, closed_at: null })
    return delay(decorateProject(project))
  },
  schedulePublish: async (id: ID, publish_at: string) => demoApi.updateProject(id, { publish_at }),
  cancelPublish: async (id: ID) => demoApi.updateProject(id, { publish_at: null }).then(() => undefined),
  scheduleClose: async (id: ID, close_at: string) => demoApi.updateProject(id, { close_at }),
  cancelClose: async (id: ID) => demoApi.updateProject(id, { close_at: null }).then(() => undefined),
  members: async (projectId: ID) => delay(demoState.memberships.filter((item) => item.project_id === projectId).map((item) => ({ ...item, user: userSummary(item.user_id) }))),
  addMember: async (projectId: ID, payload: { user_id: ID; role: Role }) => {
    const row = membership(nextId(), projectId, payload.user_id, payload.role)
    demoState.memberships.push(row)
    return delay(row)
  },
  updateMember: async (_projectId: ID, membershipId: ID, role: Role) => {
    const row = demoState.memberships.find((item) => item.id === membershipId)!
    row.role = role
    return delay({ ...row, user: userSummary(row.user_id) })
  },
  removeMember: async (_projectId: ID, membershipId: ID) => {
    demoState.memberships = demoState.memberships.filter((item) => item.id !== membershipId)
    return delay(undefined)
  },
  transferOwnership: async (projectId: ID, new_owner_id: ID) => {
    const project = demoState.projects.find((item) => item.id === projectId)!
    const oldOwner = demoState.memberships.find((item) => item.project_id === projectId && item.role === 'owner')
    if (oldOwner) oldOwner.role = 'manager'
    const nextOwner = demoState.memberships.find((item) => item.project_id === projectId && item.user_id === new_owner_id)
    if (nextOwner) nextOwner.role = 'owner'
    project.owner_id = new_owner_id
    return delay(decorateProject(project))
  },
  auditLog: async (projectId: ID) => delay(demoState.auditLogs.filter((item) => item.project_id === projectId)),
  attachmentLimits: async (projectId: ID) => {
    const used = demoState.attachments
      .filter((item) => {
        const taskId = item.task_id ?? demoState.comments.find((commentRow) => commentRow.id === item.comment_id)?.task_id
        const taskRow = demoState.tasks.find((row) => row.id === taskId)
        return taskRow?.project_id === projectId
      })
      .reduce((sum, item) => sum + item.size_bytes, 0)
    return delay({
      allowed_content_types: ['image/jpeg', 'image/png', 'text/plain'],
      allowed_text_extensions: ['.err', '.log', '.out', '.txt'],
      max_file_size_bytes: 1_048_576,
      max_project_bytes: 20_971_520,
      project_used_bytes: used,
      project_remaining_bytes: 20_971_520 - used,
    })
  },
  tasks: async (projectId: ID) => delay(demoState.tasks.filter((item) => item.project_id === projectId).map(decorateTask)),
  task: async (_projectId: ID, taskId: ID) => delay(decorateTask(demoState.tasks.find((item) => item.id === taskId)!)),
  createTask: async (projectId: ID, payload: { title: string; description?: string; assignee_id: ID; priority?: TaskPriority; due_at?: string | null }) => {
    const row = task(nextId(), projectId, payload.assignee_id, payload.title, payload.description ?? '', 'new', payload.priority ?? 'medium', payload.due_at ?? null, true)
    demoState.tasks.unshift(row)
    return delay(decorateTask(row))
  },
  updateTask: async (_projectId: ID, taskId: ID, payload: Partial<Task> & { assignee_id?: ID }) => {
    const row = demoState.tasks.find((item) => item.id === taskId)!
    Object.assign(row, payload, { updated_at: new Date().toISOString() })
    if (payload.assignee_id) row.assignee = userSummary(payload.assignee_id)
    return delay(decorateTask(row))
  },
  deleteTask: async (_projectId: ID, taskId: ID) => {
    demoState.tasks = demoState.tasks.filter((item) => item.id !== taskId)
    return delay(undefined)
  },
  transitionTask: async (_projectId: ID, taskId: ID, status: TaskStatus) => {
    const row = demoState.tasks.find((item) => item.id === taskId)!
    row.status = status
    return delay(decorateTask(row))
  },
  watchTask: async (_projectId: ID, taskId: ID) => {
    demoState.tasks.find((item) => item.id === taskId)!.watched = true
    return delay({ watched: true })
  },
  unwatchTask: async (_projectId: ID, taskId: ID) => {
    demoState.tasks.find((item) => item.id === taskId)!.watched = false
    return delay({ watched: false })
  },
  myTasks: async () => delay(demoState.tasks.filter((item) => item.assignee_id === demoState.currentUser.id).map(decorateTask)),
  dueSoon: async () => delay(demoState.tasks.filter((item) => item.due_at && !['completed', 'cancelled'].includes(item.status)).map(decorateTask)),
  comments: async (_projectId: ID, taskId: ID) => delay(demoState.comments.filter((item) => item.task_id === taskId).map(decorateComment)),
  createComment: async (_projectId: ID, taskId: ID, body: string) => {
    const row = comment(nextId(), taskId, demoState.currentUser.id, body)
    demoState.comments.push(row)
    return delay(decorateComment(row))
  },
  updateComment: async (_projectId: ID, _taskId: ID, commentId: ID, body: string) => {
    const row = demoState.comments.find((item) => item.id === commentId)!
    row.body = body
    row.updated_at = new Date().toISOString()
    return delay(decorateComment(row))
  },
  deleteComment: async (_projectId: ID, _taskId: ID, commentId: ID) => {
    demoState.comments = demoState.comments.filter((item) => item.id !== commentId)
    return delay(undefined)
  },
  taskAttachments: async (_projectId: ID, taskId: ID) => delay(demoState.attachments.filter((item) => item.task_id === taskId).map(decorateAttachment)),
  commentAttachments: async (_projectId: ID, _taskId: ID, commentId: ID) => delay(demoState.attachments.filter((item) => item.comment_id === commentId).map(decorateAttachment)),
  uploadTaskAttachment: async (_projectId: ID, taskId: ID, file: File) => {
    const row = attachment(nextId(), taskId, null, demoState.currentUser.id, file.name, file.type || 'text/plain', file.size)
    demoState.attachments.unshift(row)
    return delay(decorateAttachment(row))
  },
  uploadCommentAttachment: async (_projectId: ID, _taskId: ID, commentId: ID, file: File) => {
    const row = attachment(nextId(), null, commentId, demoState.currentUser.id, file.name, file.type || 'text/plain', file.size)
    demoState.attachments.unshift(row)
    return delay(decorateAttachment(row))
  },
  deleteAttachment: async (attachmentId: ID) => {
    demoState.attachments = demoState.attachments.filter((item) => item.id !== attachmentId)
    return delay(undefined)
  },
  downloadUrl: (attachmentId: ID) => `${API_BASE}/attachments/${attachmentId}/download/`,
  notifications: async () => delay(demoState.notifications),
  readNotification: async (id: ID) => {
    const row = demoState.notifications.find((item) => item.id === id)!
    row.read_at = new Date().toISOString()
    return delay(row)
  },
  readAllNotifications: async () => {
    const unread = demoState.notifications.filter((item) => !item.read_at)
    unread.forEach((item) => {
      item.read_at = new Date().toISOString()
    })
    return delay({ status: 'read', count: unread.length })
  },
}

export const api = DEMO_MODE ? demoApi : liveApi
export const isDemoMode = DEMO_MODE
export const toPage = page
