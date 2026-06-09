export type ID = number

export type UserSummary = {
  id: ID
  email: string
  display_name: string
}

export type CurrentUser = UserSummary & {
  is_staff: boolean
}

export type Profile = {
  timezone: string
}

export type Pagination = {
  count: number
  page: number
  page_size: number
  total_pages: number
  next: string | null
  previous: string | null
}

export type Paginated<T> = {
  data: T[]
  meta?: { pagination: Pagination }
}

export type Envelope<T> = {
  data: T
}

export type ApiErrorItem = {
  code: string
  detail: string
  field: string | null
}

export type ApiErrorEnvelope = {
  errors: ApiErrorItem[]
}

export type ProjectVisibility = 'private' | 'public'
export type ProjectState = 'active' | 'closed'
export type CommentPolicy = 'members_only' | 'authenticated_users'
export type Role = 'owner' | 'manager' | 'member' | 'viewer'

export type ProjectCapabilities = {
  can_update: boolean
  can_delete: boolean
  can_manage_members: boolean
  can_transfer_ownership: boolean
  can_schedule: boolean
  can_close: boolean
  can_reopen: boolean
  can_read_audit_log: boolean
  can_create_task: boolean
  can_comment: boolean
  can_upload_task_attachment: boolean
  can_upload_comment_attachment: boolean
}

export type ProjectMembershipSummary = {
  id: ID
  role: Role
}

export type Project = {
  id: ID
  name: string
  description: string
  owner_id: ID
  owner?: UserSummary
  visibility: ProjectVisibility
  state: ProjectState
  public_comment_policy: CommentPolicy
  publish_at: string | null
  published_at: string | null
  close_at: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
  my_membership?: ProjectMembershipSummary | null
  capabilities?: ProjectCapabilities
}

export type ProjectMembership = {
  id: ID
  project_id: ID
  user_id: ID
  user?: UserSummary
  role: Role
  created_at: string
  updated_at: string
}

export type TaskStatus =
  | 'new'
  | 'accepted'
  | 'in_progress'
  | 'on_hold'
  | 'completed'
  | 'cancelled'

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

export type TaskCapabilities = {
  can_update: boolean
  can_delete: boolean
  can_transition: boolean
  can_watch: boolean
  can_unwatch: boolean
  can_comment: boolean
  can_upload_attachment: boolean
}

export type ProjectSummary = {
  id: ID
  name: string
  state: ProjectState
  visibility: ProjectVisibility
}

export type Task = {
  id: ID
  project_id: ID
  project?: ProjectSummary
  title: string
  description: string
  assignee_id: ID
  assignee?: UserSummary
  status: TaskStatus
  priority: TaskPriority
  due_at: string | null
  created_at: string
  updated_at: string
  watched: boolean
  allowed_transitions?: TaskStatus[]
  capabilities?: TaskCapabilities
}

export type CommentCapabilities = {
  can_update: boolean
  can_delete: boolean
  can_upload_attachment: boolean
}

export type TaskComment = {
  id: ID
  task_id: ID
  author_id: ID
  author?: UserSummary
  body: string
  created_at: string
  updated_at: string
  capabilities?: CommentCapabilities
}

export type AttachmentCapabilities = {
  can_download: boolean
  can_delete: boolean
}

export type Attachment = {
  id: ID
  task_id: ID | null
  comment_id: ID | null
  uploaded_by_id: ID
  uploaded_by?: UserSummary
  original_filename: string
  content_type: string
  size_bytes: number
  checksum_sha256: string
  created_at: string
  capabilities?: AttachmentCapabilities
}

export type AttachmentLimits = {
  allowed_content_types: string[]
  allowed_text_extensions: string[]
  max_file_size_bytes: number
  max_project_bytes: number
  project_used_bytes: number
  project_remaining_bytes: number
}

export type Notification = {
  id: ID
  type: string
  title: string
  message: string
  project_id: ID | null
  task_id: ID | null
  read_at: string | null
  created_at: string
}

export type AuditLog = {
  id: ID
  actor_id: ID | null
  actor?: UserSummary | null
  action: string
  entity_type: string
  entity_id: ID
  project_id: ID | null
  before: Record<string, unknown>
  after: Record<string, unknown>
  metadata: Record<string, unknown>
  ip_address: string | null
  user_agent: string
  idempotency_key: string
  created_at: string
}

export type ProjectFilters = {
  visibility?: ProjectVisibility | 'all'
  role?: Role | 'all'
  search?: string
  ordering?: string
}

export type AuthSession = {
  access: string
  refresh: string
}

export type StatusResponse = {
  status: string
  count?: number
}

export type DashboardAccess = 'owner' | 'editor' | 'viewer' | 'none'

export type DashboardWidgetType =
  | 'metric_tile'
  | 'status_breakdown'
  | 'priority_breakdown'
  | 'technician_workload'
  | 'due_soon_table'
  | 'recent_activity'

export type DashboardShareTargetType = 'user' | 'project_members'
export type DashboardShareAccess = 'viewer' | 'editor'
export type DashboardDueWindow = 'overdue' | 'next_24_hours' | 'next_7_days'

export type DashboardTaskFilters = {
  project_ids?: ID[]
  statuses?: TaskStatus[]
  priorities?: TaskPriority[]
  assignee_ids?: ID[]
  due_window?: DashboardDueWindow
}

export type DashboardWidget = {
  id: ID
  dashboard_id: ID
  type: DashboardWidgetType
  title: string
  config: DashboardTaskFilters
  x: number
  y: number
  w: number
  h: number
  order: number
  created_at: string
  updated_at: string
}

export type DashboardShare = {
  id: ID
  dashboard_id: ID
  target_type: DashboardShareTargetType
  user_id: ID | null
  user?: UserSummary | null
  project_id: ID | null
  project?: { id: ID; name: string } | null
  access: DashboardShareAccess
  created_at: string
  updated_at: string
}

export type DashboardCapabilities = {
  can_view: boolean
  can_edit: boolean
  can_manage_shares: boolean
  can_delete: boolean
}

export type ConfigurableDashboard = {
  id: ID
  name: string
  owner_id: ID
  owner?: UserSummary
  access: DashboardAccess
  capabilities: DashboardCapabilities
  widgets: DashboardWidget[]
  shares: DashboardShare[]
  created_at: string
  updated_at: string
}

export type DashboardLayoutItem = {
  id: ID
  x: number
  y: number
  w: number
  h: number
  order: number
}

export type DashboardDrilldown =
  | { type: 'task_list'; filters: DashboardTaskFilters }
  | { type: 'task_detail'; project_id: ID; task_id: ID }
  | { type: 'project_detail'; project_id: ID }
  | { type: 'activity' }

export type DashboardRenderedWidget = {
  id: ID
  type: DashboardWidgetType
  title: string
  config: DashboardTaskFilters
  layout: Omit<DashboardLayoutItem, 'id'>
  result: Record<string, unknown>
  drilldown: DashboardDrilldown
}

export type DashboardRender = {
  dashboard_id: ID
  widgets: DashboardRenderedWidget[]
}
