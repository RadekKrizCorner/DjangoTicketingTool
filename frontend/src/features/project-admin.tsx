import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, History, Paperclip, Shield } from 'lucide-react'
import { toast } from 'sonner'
import { api, isDemoMode } from '../lib/api'
import type { ID, Project, ProjectMembership, Role } from '../lib/types'
import { bytes, formatDateTime, titleCase } from '../lib/utils'
import { ActionRow, Badge, Button, ConfirmButton, DataTable, EmptyState, Field, Input, Panel, Select } from '../components/ui'
import { invalidateProject, mutationError } from './helpers'
import { Metric } from './dashboard'
import { Avatar } from './navigation'

const roleOptions: Role[] = ['manager', 'member', 'viewer']

export function MembersPanel({ project }: { project: Project }) {
  const queryClient = useQueryClient()
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<Role>('member')
  const membersQuery = useQuery({ queryKey: ['members', project.id], queryFn: () => api.members(project.id) })
  const usersQuery = useQuery({ queryKey: ['users', userId], queryFn: () => api.searchUsers(userId), enabled: userId.length > 0 || isDemoMode })
  const addMutation = useMutation({
    mutationFn: () => api.addMember(project.id, { user_id: Number(userId), role }),
    onSuccess: () => {
      setUserId('')
      invalidateProject(queryClient, project.id)
      toast.success('Member added')
    },
    onError: (error) => toast.error(mutationError(error)),
  })

  return (
    <div className="grid">
      <Panel title="Add Member" subtitle="Owners can add active users as manager, member, or viewer.">
        <div className="form-grid">
          <Field label="User search or ID">
            <Input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="Search or type user ID" disabled={!project.capabilities?.can_manage_members} />
          </Field>
          <Field label="Role">
            <Select value={role} onChange={(event) => setRole(event.target.value as Role)} disabled={!project.capabilities?.can_manage_members}>
              {roleOptions.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
            </Select>
          </Field>
          <div className="span-2">
            <ActionRow>
              <Button variant="primary" disabled={!project.capabilities?.can_manage_members || !userId} onClick={() => addMutation.mutate()}>
                Add member
              </Button>
              {(usersQuery.data ?? []).slice(0, 4).map((user) => (
                <Button key={user.id} onClick={() => setUserId(String(user.id))}>{user.display_name}</Button>
              ))}
            </ActionRow>
          </div>
        </div>
      </Panel>
      <MemberTable project={project} members={membersQuery.data ?? []} />
    </div>
  )
}

function MemberTable({ project, members }: { project: Project; members: ProjectMembership[] }) {
  const queryClient = useQueryClient()
  const updateMutation = useMutation({
    mutationFn: ({ id, role }: { id: ID; role: Role }) => api.updateMember(project.id, id, role),
    onSuccess: () => invalidateProject(queryClient, project.id),
  })
  const removeMutation = useMutation({
    mutationFn: (id: ID) => api.removeMember(project.id, id),
    onSuccess: () => invalidateProject(queryClient, project.id),
  })
  const transferMutation = useMutation({
    mutationFn: (userId: ID) => api.transferOwnership(project.id, userId),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Ownership transferred')
    },
  })

  return (
    <DataTable>
      <thead>
        <tr>
          <th>User</th>
          <th>Role</th>
          <th>Added</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <tr key={member.id}>
            <td data-label="User">
              <div className="toolbar"><Avatar user={member.user} /><span>{member.user?.display_name ?? member.user_id}</span></div>
            </td>
            <td data-label="Role">
              <Select
                value={member.role}
                disabled={!project.capabilities?.can_manage_members || member.role === 'owner'}
                onChange={(event) => updateMutation.mutate({ id: member.id, role: event.target.value as Role })}
              >
                <option value="owner">Owner</option>
                {roleOptions.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
              </Select>
            </td>
            <td data-label="Added">{formatDateTime(member.created_at)}</td>
            <td data-label="Action">
              <ActionRow>
                {project.capabilities?.can_transfer_ownership && member.role !== 'owner' && (
                  <ConfirmButton
                    title="Transfer ownership"
                    description={`Transfer project ownership to ${member.user?.display_name ?? `user ${member.user_id}`}?`}
                    confirmLabel="Transfer owner"
                    onConfirm={() => transferMutation.mutate(member.user_id)}
                  >
                    Transfer owner
                  </ConfirmButton>
                )}
                {project.capabilities?.can_manage_members && member.role !== 'owner' && (
                  <ConfirmButton
                    variant="danger"
                    title="Remove member"
                    description={`Remove ${member.user?.display_name ?? `user ${member.user_id}`} from this project?`}
                    confirmLabel="Remove member"
                    onConfirm={() => removeMutation.mutate(member.id)}
                  >
                    Remove
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

export function LifecyclePanel({ project }: { project: Project }) {
  const queryClient = useQueryClient()
  const [publishAt, setPublishAt] = useState('')
  const [closeAt, setCloseAt] = useState('')
  const closeMutation = useMutation({
    mutationFn: () => api.closeProject(project.id),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Project closed')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const reopenMutation = useMutation({
    mutationFn: () => api.reopenProject(project.id),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Project reopened')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const publishMutation = useMutation({
    mutationFn: () => api.schedulePublish(project.id, new Date(publishAt).toISOString()),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Publish schedule saved')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const closeScheduleMutation = useMutation({
    mutationFn: () => api.scheduleClose(project.id, new Date(closeAt).toISOString()),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Close schedule saved')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const cancelPublishMutation = useMutation({
    mutationFn: () => api.cancelPublish(project.id),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Publish schedule cancelled')
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const cancelCloseMutation = useMutation({
    mutationFn: () => api.cancelClose(project.id),
    onSuccess: () => {
      invalidateProject(queryClient, project.id)
      toast.success('Close schedule cancelled')
    },
    onError: (error) => toast.error(mutationError(error)),
  })

  return (
    <div className="grid">
      <div className="detail-list">
        <div className="detail-row"><span>Published</span><strong>{formatDateTime(project.published_at)}</strong></div>
        <div className="detail-row"><span>Publish schedule</span><strong>{formatDateTime(project.publish_at)}</strong></div>
        <div className="detail-row"><span>Closed</span><strong>{formatDateTime(project.closed_at)}</strong></div>
        <div className="detail-row"><span>Close schedule</span><strong>{formatDateTime(project.close_at)}</strong></div>
      </div>
      <Panel title="Lifecycle Actions">
        <ActionRow>
          <ConfirmButton
            disabled={!project.capabilities?.can_close}
            title="Close project"
            description={`Close ${project.name}? Task changes and task uploads will be disabled until it is reopened.`}
            confirmLabel="Close project"
            onConfirm={() => closeMutation.mutate()}
          >
            Close project
          </ConfirmButton>
          <Button disabled={!project.capabilities?.can_reopen} onClick={() => reopenMutation.mutate()}>Reopen project</Button>
        </ActionRow>
      </Panel>
      <Panel title="Schedules">
        <div className="form-grid">
          <Field label="Publish at">
            <Input type="datetime-local" value={publishAt} onChange={(event) => setPublishAt(event.target.value)} />
          </Field>
          <Field label="Close at">
            <Input type="datetime-local" value={closeAt} onChange={(event) => setCloseAt(event.target.value)} />
          </Field>
          <ActionRow>
            <Button disabled={!project.capabilities?.can_schedule || !publishAt} onClick={() => publishMutation.mutate()}>Save publish</Button>
            <ConfirmButton
              disabled={!project.capabilities?.can_schedule}
              title="Cancel publish schedule"
              description={`Cancel the publish schedule for ${project.name}?`}
              confirmLabel="Cancel publish"
              onConfirm={() => cancelPublishMutation.mutate()}
            >
              Cancel publish
            </ConfirmButton>
            <Button disabled={!project.capabilities?.can_schedule || !closeAt} onClick={() => closeScheduleMutation.mutate()}>Save close</Button>
            <ConfirmButton
              disabled={!project.capabilities?.can_schedule}
              title="Cancel close schedule"
              description={`Cancel the close schedule for ${project.name}?`}
              confirmLabel="Cancel close"
              onConfirm={() => cancelCloseMutation.mutate()}
            >
              Cancel close
            </ConfirmButton>
          </ActionRow>
        </div>
      </Panel>
    </div>
  )
}

export function AuditPanel({ project }: { project: Project }) {
  const auditQuery = useQuery({ queryKey: ['audit', project.id], queryFn: () => api.auditLog(project.id), enabled: !!project.capabilities?.can_read_audit_log })
  if (!project.capabilities?.can_read_audit_log) return <EmptyState title="Audit log is owner-only" detail="The backend returns permission_denied for non-owner readers." />
  return (
    <DataTable>
      <thead>
        <tr>
          <th>Action</th>
          <th>Actor</th>
          <th>Entity</th>
          <th>When</th>
        </tr>
      </thead>
      <tbody>
        {(auditQuery.data ?? []).map((item) => (
          <tr key={item.id}>
            <td data-label="Action"><Badge><History size={13} /> {item.action}</Badge></td>
            <td data-label="Actor">{item.actor?.display_name ?? 'System'}</td>
            <td data-label="Entity">{item.entity_type} #{item.entity_id}</td>
            <td data-label="When">{formatDateTime(item.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  )
}

export function AttachmentLimitsPanel({ project }: { project: Project }) {
  const limitsQuery = useQuery({ queryKey: ['limits', project.id], queryFn: () => api.attachmentLimits(project.id) })
  const limits = limitsQuery.data
  if (!limits) return <EmptyState title="Loading attachment limits" />
  const usedPct = Math.round((limits.project_used_bytes / limits.max_project_bytes) * 100)
  return (
    <div className="grid">
      <div className="grid cols-3">
        <Metric title="Project used" value={usedPct} detail={`${bytes(limits.project_used_bytes)} used`} icon={Paperclip} />
        <Metric title="Remaining MB" value={Math.round(limits.project_remaining_bytes / 1024 / 1024)} detail={`${bytes(limits.max_project_bytes)} quota`} icon={FileText} />
        <Metric title="Max file MB" value={Math.round(limits.max_file_size_bytes / 1024 / 1024)} detail="Per upload request" icon={Shield} />
      </div>
      <Panel title="Allowed Uploads">
        <ActionRow>
          {limits.allowed_content_types.map((item) => <Badge key={item}>{item}</Badge>)}
          {limits.allowed_text_extensions.map((item) => <Badge key={item}>{item}</Badge>)}
        </ActionRow>
      </Panel>
    </div>
  )
}
