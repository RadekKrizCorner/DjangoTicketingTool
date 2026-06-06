import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, SlidersHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import type { ID, Project, ProjectFilters } from '../lib/types'
import { titleCase } from '../lib/utils'
import { ActionRow, Badge, Button, ConfirmButton, DataTable, Dialog, EmptyState, Field, Input, Panel, Select, StatusBadge, Textarea } from '../components/ui'
import { invalidateProject, mutationError } from './helpers'
import { PageHeading } from './layout'
import { MembersPanel, LifecyclePanel, AuditPanel, AttachmentLimitsPanel } from './project-admin'
import { ProjectTasks } from './project-tasks'

type ProjectTab = 'tasks' | 'members' | 'lifecycle' | 'audit' | 'attachments'

export function ProjectsView({
  activeProjectId,
  activeTaskId,
  onOpenProject,
  onBackToProjects,
}: {
  activeProjectId: ID | null
  activeTaskId: ID | null
  onOpenProject: (projectId: ID, taskId?: ID | null) => void
  onBackToProjects: () => void
}) {
  const [filters, setFilters] = useState<ProjectFilters>({ visibility: 'all', role: 'all', ordering: '-created_at' })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [projectDialog, setProjectDialog] = useState(false)
  const projectsQuery = useQuery({ queryKey: ['projects', filters], queryFn: () => api.projects(filters) })
  const projects = projectsQuery.data ?? []

  if (activeProjectId) {
    return (
      <>
        <PageHeading
          title="Project Workspace"
          detail="Work through tasks first, then switch to members, lifecycle, audit, or attachment limits when needed."
          actions={<Button onClick={onBackToProjects}><ChevronLeft size={15} /> Back to projects</Button>}
        />
        <ProjectDetail key={`${activeProjectId}-${activeTaskId ?? 'default'}`} projectId={activeProjectId} initialTaskId={activeTaskId} />
      </>
    )
  }

  return (
    <>
      <PageHeading
        title="Projects"
        detail="Create, filter, schedule, close, reopen, and audit visible project workspaces."
        actions={(
          <ActionRow>
            <Button onClick={() => setFiltersOpen((current) => !current)}>
              <SlidersHorizontal size={15} /> Filters
            </Button>
            <Button variant="primary" onClick={() => setProjectDialog(true)}><Plus size={15} /> Project</Button>
          </ActionRow>
        )}
      />
      {filtersOpen && (
        <Panel title="Project Filters" subtitle="Narrow the list when the workspace has many projects.">
          <div className="toolbar filters-toolbar">
            <Input
              placeholder="Search projects"
              value={filters.search ?? ''}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
            <Select value={filters.visibility ?? 'all'} onChange={(event) => setFilters((current) => ({ ...current, visibility: event.target.value as ProjectFilters['visibility'] }))}>
              <option value="all">All visibility</option>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </Select>
            <Select value={filters.role ?? 'all'} onChange={(event) => setFilters((current) => ({ ...current, role: event.target.value as ProjectFilters['role'] }))}>
              <option value="all">All roles</option>
              <option value="owner">Owner</option>
              <option value="manager">Manager</option>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </Select>
            <Select value={filters.ordering ?? '-created_at'} onChange={(event) => setFilters((current) => ({ ...current, ordering: event.target.value }))}>
              <option value="-created_at">Newest</option>
              <option value="name">Name</option>
              <option value="-updated_at">Recently updated</option>
            </Select>
          </div>
        </Panel>
      )}
      <div className="projects-list-layout">
        <Panel title="Project List" subtitle={`${projects.length} visible projects`}>
          <ProjectTable projects={projects} onSelect={(projectId) => onOpenProject(projectId)} />
        </Panel>
      </div>
      <ProjectDialog open={projectDialog} onClose={() => setProjectDialog(false)} />
    </>
  )
}

function ProjectTable({ projects, onSelect }: { projects: Project[]; onSelect: (id: ID) => void }) {
  if (!projects.length) return <EmptyState title="No projects match the filters" />
  return (
    <DataTable>
      <thead>
        <tr>
          <th>Name</th>
          <th>State</th>
          <th>Role</th>
          <th>Visibility</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {projects.map((project) => (
          <tr key={project.id} data-testid={`project-row-${project.id}`}>
            <td>
              <div className="strong">{project.name}</div>
              <div className="muted small">{project.description}</div>
            </td>
            <td><StatusBadge value={project.state} tone={project.state === 'closed' ? 'tone-danger' : 'tone-success'} /></td>
            <td><Badge>{project.my_membership?.role ?? 'public'}</Badge></td>
            <td><Badge>{project.visibility}</Badge></td>
            <td>
              <Button aria-label={`Open ${project.name}`} onClick={() => onSelect(project.id)}>
                Open <ChevronRight size={14} />
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </DataTable>
  )
}

function ProjectDetail({ projectId, initialTaskId }: { projectId: ID; initialTaskId?: ID | null }) {
  const [tab, setTab] = useState<ProjectTab>('tasks')
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => api.project(projectId) })
  const project = projectQuery.data

  if (!project) return <Panel><EmptyState title="Loading project" /></Panel>

  return (
    <Panel
      title={project.name}
      subtitle={`${titleCase(project.state)} · ${titleCase(project.visibility)} · ${project.my_membership?.role ?? 'public access'}`}
      actions={<ProjectActions project={project} />}
    >
      <div className="tabs" style={{ marginBottom: 16 }}>
        {(['tasks', 'members', 'lifecycle', 'audit', 'attachments'] as ProjectTab[]).map((item) => (
          <button
            key={item}
            data-testid={`project-tab-${item}`}
            className={`tab ${tab === item ? 'active' : ''}`}
            onClick={() => setTab(item)}
          >
            {titleCase(item)}
          </button>
        ))}
      </div>
      {tab === 'tasks' && <ProjectTasks project={project} initialTaskId={initialTaskId} />}
      {tab === 'members' && <MembersPanel project={project} />}
      {tab === 'lifecycle' && <LifecyclePanel project={project} />}
      {tab === 'audit' && <AuditPanel project={project} />}
      {tab === 'attachments' && <AttachmentLimitsPanel project={project} />}
    </Panel>
  )
}

function ProjectActions({ project }: { project: Project }) {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteProject(project.id),
    onSuccess: () => {
      toast.success('Project deleted')
      invalidateProject(queryClient, project.id)
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  return (
    <ActionRow>
      {project.capabilities?.can_delete && (
        <ConfirmButton
          variant="danger"
          title="Delete project"
          description={`Delete ${project.name}? This removes it from project lists and hides its active workspace data.`}
          confirmLabel="Delete project"
          onConfirm={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
        >
          Delete
        </ConfirmButton>
      )}
    </ActionRow>
  )
}

function ProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [visibility, setVisibility] = useState<'private' | 'public'>('private')
  const [policy, setPolicy] = useState<'members_only' | 'authenticated_users'>('members_only')
  const createMutation = useMutation({
    mutationFn: () => api.createProject({ name, description, visibility, public_comment_policy: policy }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project created')
      onClose()
    },
    onError: (error) => toast.error(mutationError(error)),
  })

  return (
    <Dialog title="Create Project" open={open} onClose={onClose}>
      <div className="form-grid">
        <Field label="Name" className="span-2">
          <Input value={name} onChange={(event) => setName(event.target.value)} />
        </Field>
        <Field label="Description" className="span-2">
          <Textarea value={description} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <Field label="Visibility">
          <Select value={visibility} onChange={(event) => setVisibility(event.target.value as 'private' | 'public')}>
            <option value="private">Private</option>
            <option value="public">Public</option>
          </Select>
        </Field>
        <Field label="Public comments">
          <Select value={policy} onChange={(event) => setPolicy(event.target.value as 'members_only' | 'authenticated_users')}>
            <option value="members_only">Members only</option>
            <option value="authenticated_users">Authenticated users</option>
          </Select>
        </Field>
        <div className="span-2">
          <Button variant="primary" disabled={!name} onClick={() => createMutation.mutate()}>Create project</Button>
        </div>
      </div>
    </Dialog>
  )
}
