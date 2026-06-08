import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronsUpDown,
  Grip,
  ListFilter,
  Maximize2,
  Move,
  Plus,
  Save,
  Search,
  Settings2,
  Share2,
  Star,
  Trash2,
} from 'lucide-react'
import { api } from '../lib/api'
import type {
  ConfigurableDashboard,
  DashboardDrilldown,
  DashboardDueWindow,
  DashboardLayoutItem,
  DashboardRender,
  DashboardRenderedWidget,
  DashboardShare,
  DashboardTaskFilters,
  DashboardWidget,
  DashboardWidgetType,
  ID,
  Project,
  Task,
  TaskStatus,
  UserSummary,
} from '../lib/types'
import { formatDateTime, priorityTone, statusTone, titleCase } from '../lib/utils'
import { ActionRow, Badge, Button, DataTable, Dialog, EmptyState, Field, IconButton, Input, Panel, Select, StatusBadge } from '../components/ui'
import {
  DASHBOARD_GRID_COLUMNS as GRID_COLUMNS,
  layoutCollides,
  mergeLayoutDraft,
  normalizeLayoutItem,
} from './dashboard-layout'
import { PageHeading } from './layout'

const GRID_ROW_HEIGHT = 84
const EMPTY_DASHBOARDS: ConfigurableDashboard[] = []
const EMPTY_DASHBOARD_WIDGETS: ConfigurableDashboard['widgets'] = []
const EMPTY_RENDERED_WIDGETS: DashboardRenderedWidget[] = []
const defaultWidgetTitle: Record<DashboardWidgetType, string> = {
  metric_tile: 'New metric',
  status_breakdown: 'Status breakdown',
  priority_breakdown: 'Priority breakdown',
  technician_workload: 'Technician workload',
  due_soon_table: 'Due soon table',
  recent_activity: 'Recent activity',
}

type DragState = {
  id: ID
  mode: 'move' | 'resize'
  startX: number
  startY: number
  origin: DashboardLayoutItem
}

type DraftShareRow = {
  key: string
  persistedKey?: string
  addedIndex?: number
  share: Partial<DashboardShare>
}

export function DashboardsView({
  activeDashboardId,
  onOpenDashboard,
  onDrilldown,
}: {
  activeDashboardId: ID | null
  onOpenDashboard: (dashboardId: ID | null) => void
  onDrilldown: (drilldown: DashboardDrilldown) => void
}) {
  const queryClient = useQueryClient()
  const [localDashboardId, setLocalDashboardId] = useState<ID | null>(activeDashboardId)
  const [filters, setFilters] = useState<DashboardTaskFilters>({})
  const [editLayout, setEditLayout] = useState(false)
  const [layoutOverrides, setLayoutOverrides] = useState<Record<ID, DashboardLayoutItem>>({})
  const [layoutMessage, setLayoutMessage] = useState('')
  const [dashboardSearch, setDashboardSearch] = useState('')
  const [switcherOpen, setSwitcherOpen] = useState(false)
  const [favoriteDashboardIds, setFavoriteDashboardIds] = useState<Set<ID>>(() => new Set())
  const [createOpen, setCreateOpen] = useState(false)
  const [newDashboardName, setNewDashboardName] = useState('New dashboard')
  const [addOpen, setAddOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [newWidgetType, setNewWidgetType] = useState<DashboardWidgetType>('metric_tile')
  const [newWidgetTitle, setNewWidgetTitle] = useState(defaultWidgetTitle.metric_tile)
  const dragState = useRef<DragState | null>(null)
  const gridRef = useRef<HTMLDivElement | null>(null)
  const favoritesInitialized = useRef(false)

  const dashboardsQuery = useQuery({ queryKey: ['dashboards'], queryFn: api.dashboards })
  const projectsQuery = useQuery({ queryKey: ['projects', 'dashboard-filter'], queryFn: () => api.projects({}) })

  const dashboards = dashboardsQuery.data ?? EMPTY_DASHBOARDS
  const selectedId = activeDashboardId ?? localDashboardId ?? dashboards[0]?.id ?? null
  const selectedDashboard = dashboards.find((dashboard) => dashboard.id === selectedId) ?? dashboards[0] ?? null
  const searchedDashboards = useMemo(
    () => filterDashboards(dashboards, dashboardSearch),
    [dashboards, dashboardSearch],
  )
  const favoriteDashboards = useMemo(
    () => dashboards.filter((dashboard) => favoriteDashboardIds.has(dashboard.id)),
    [dashboards, favoriteDashboardIds],
  )

  const renderQuery = useQuery({
    queryKey: ['dashboard-render', selectedDashboard?.id, filters],
    queryFn: () => api.renderDashboard(selectedDashboard!.id, filters),
    enabled: !!selectedDashboard,
  })
  const sharesQuery = useQuery({
    queryKey: ['dashboard-shares', selectedDashboard?.id],
    queryFn: () => api.dashboardShares(selectedDashboard!.id),
    enabled: !!selectedDashboard?.capabilities.can_manage_shares,
  })

  const renderedWidgets = renderQuery.data?.widgets ?? EMPTY_RENDERED_WIDGETS
  const dashboardWidgets = selectedDashboard?.widgets ?? EMPTY_DASHBOARD_WIDGETS
  const baseLayoutDraft = useMemo(() => {
    const widgets = renderedWidgets.length
      ? renderedWidgets.map((widget) => ({
          id: widget.id,
          x: widget.layout.x,
          y: widget.layout.y,
          w: widget.layout.w,
          h: widget.layout.h,
          order: widget.layout.order,
        }))
      : dashboardWidgets.map((widget) => ({
          id: widget.id,
          x: widget.x,
          y: widget.y,
          w: widget.w,
          h: widget.h,
          order: widget.order,
        }))
    return Object.fromEntries(widgets.map((widget) => [widget.id, widget])) as Record<ID, DashboardLayoutItem>
  }, [dashboardWidgets, renderedWidgets])
  const layoutDraft = useMemo(
    () => mergeLayoutDraft(baseLayoutDraft, layoutOverrides),
    [baseLayoutDraft, layoutOverrides],
  )
  const shareRows = sharesQuery.data ?? selectedDashboard?.shares ?? []

  useEffect(() => {
    if (!dashboards.length || favoritesInitialized.current) return
    favoritesInitialized.current = true
    setFavoriteDashboardIds(new Set([dashboards[0].id]))
  }, [dashboards])

  const updateLayoutItem = (widgetId: ID, patch: Partial<DashboardLayoutItem>) => {
    const item = layoutDraft[widgetId]
    if (!item) return
    const next = normalizeLayoutItem({ ...item, ...patch })
    if (layoutCollides(next, Object.values(layoutDraft).filter((other) => other.id !== widgetId))) {
      setLayoutMessage('Move blocked: widgets cannot overlap')
      return
    }
    setLayoutMessage('')
    setLayoutOverrides((current) => ({ ...current, [widgetId]: next }))
  }

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const state = dragState.current
      const grid = gridRef.current
      if (!state || !grid) return
      const columnWidth = Math.max(1, grid.clientWidth / GRID_COLUMNS)
      const deltaX = Math.round((event.clientX - state.startX) / columnWidth)
      const deltaY = Math.round((event.clientY - state.startY) / GRID_ROW_HEIGHT)
      if (state.mode === 'move') {
        updateLayoutItem(state.id, {
          x: clamp(state.origin.x + deltaX, 0, GRID_COLUMNS - state.origin.w),
          y: Math.max(0, state.origin.y + deltaY),
        })
      } else {
        updateLayoutItem(state.id, {
          w: clamp(state.origin.w + deltaX, 1, GRID_COLUMNS - state.origin.x),
          h: Math.max(1, state.origin.h + deltaY),
        })
      }
    }
    const handlePointerUp = () => {
      dragState.current = null
    }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  })

  const saveLayoutMutation = useMutation({
    mutationFn: () =>
      api.saveDashboardLayout(
        selectedDashboard!.id,
        Object.values(layoutDraft).sort((first, second) => first.order - second.order || first.id - second.id),
      ),
    onSuccess: async (widgets) => {
      setLayoutMessage('Layout saved')
      setLayoutOverrides({})
      if (selectedDashboard) {
        cacheSavedDashboardLayout(queryClient, selectedDashboard.id, widgets)
      }
      await queryClient.invalidateQueries({ queryKey: ['dashboards'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-render', selectedDashboard?.id] })
    },
  })

  const createWidgetMutation = useMutation({
    mutationFn: () =>
      api.createDashboardWidget(selectedDashboard!.id, {
        type: newWidgetType,
        title: newWidgetTitle || defaultWidgetTitle[newWidgetType],
        config: {},
        x: 0,
        y: nextWidgetY(selectedDashboard),
        w: newWidgetType === 'recent_activity' ? 12 : 4,
        h: newWidgetType === 'metric_tile' ? 2 : 3,
        order: (selectedDashboard?.widgets.length ?? 0) + 1,
      }),
    onSuccess: async () => {
      setAddOpen(false)
      setLayoutOverrides({})
      await queryClient.invalidateQueries({ queryKey: ['dashboards'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-render', selectedDashboard?.id] })
    },
  })

  const createDashboardMutation = useMutation({
    mutationFn: () => api.createDashboard({ name: newDashboardName.trim() }),
    onSuccess: async (dashboard) => {
      setCreateOpen(false)
      setNewDashboardName('New dashboard')
      setLocalDashboardId(dashboard.id)
      setLayoutOverrides({})
      onOpenDashboard(dashboard.id)
      await queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })

  const selectDashboard = (dashboardId: ID) => {
    setLocalDashboardId(dashboardId)
    setLayoutMessage('')
    setLayoutOverrides({})
    setSwitcherOpen(false)
    onOpenDashboard(dashboardId)
  }

  const toggleFavoriteDashboard = (dashboardId: ID) => {
    setFavoriteDashboardIds((current) => {
      const next = new Set(current)
      if (next.has(dashboardId)) {
        next.delete(dashboardId)
      } else {
        next.add(dashboardId)
      }
      return next
    })
  }

  const startPointerEdit = (
    event: ReactPointerEvent<HTMLElement>,
    widgetId: ID,
    mode: DragState['mode'],
  ) => {
    if (!editLayout) return
    const item = layoutDraft[widgetId]
    if (!item) return
    event.preventDefault()
    dragState.current = {
      id: widgetId,
      mode,
      startX: event.clientX,
      startY: event.clientY,
      origin: item,
    }
  }

  const updateProjectFilter = (value: string) => {
    setFilters((current) => ({
      ...current,
      project_ids: value === 'all' ? undefined : [Number(value)],
    }))
  }

  const updateStatusFilter = (value: string) => {
    setFilters((current) => ({
      ...current,
      statuses: value === 'all' ? undefined : value === 'open' ? ['new', 'accepted', 'in_progress', 'on_hold'] : [value as TaskStatus],
    }))
  }

  const updateDueFilter = (value: string) => {
    setFilters((current) => ({
      ...current,
      due_window: value === 'all' ? undefined : (value as DashboardDueWindow),
    }))
  }

  if (!dashboards.length && !dashboardsQuery.isLoading) {
    return (
      <>
        <PageHeading
          title="Dashboards"
          detail="Create shared dashboard views for project operations."
          actions={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus size={15} aria-hidden="true" /> New dashboard
            </Button>
          }
        />
        <EmptyState title="No dashboards visible" detail="Create a dashboard to start adding widgets." />
        <CreateDashboardDialog
          open={createOpen}
          name={newDashboardName}
          isPending={createDashboardMutation.isPending}
          onName={setNewDashboardName}
          onClose={() => setCreateOpen(false)}
          onCreate={() => createDashboardMutation.mutate()}
        />
      </>
    )
  }

  return (
    <>
      <PageHeading
        title="Dashboards"
        detail="Create shared dashboard views for project operations."
        actions={
          <div className="toolbar dashboard-page-actions">
            <Button onClick={() => setCreateOpen(true)}>
              <Plus size={15} aria-hidden="true" /> New dashboard
            </Button>
            {selectedDashboard?.capabilities.can_edit && (
              <Button onClick={() => setAddOpen(true)}>
                <Plus size={15} aria-hidden="true" /> Add widget
              </Button>
            )}
            {selectedDashboard?.capabilities.can_edit && (
              <Button onClick={() => setEditLayout((current) => !current)}>
                <Move size={15} aria-hidden="true" /> {editLayout ? 'Stop editing' : 'Edit layout'}
              </Button>
            )}
            {selectedDashboard?.capabilities.can_manage_shares && (
              <Button onClick={() => setShareOpen(true)}>
                <Share2 size={15} aria-hidden="true" /> Share
              </Button>
            )}
          </div>
        }
      />

      {selectedDashboard && (
        <DashboardSwitcher
          dashboards={dashboards}
          favoriteDashboards={favoriteDashboards}
          favoriteDashboardIds={favoriteDashboardIds}
          search={dashboardSearch}
          searchedDashboards={searchedDashboards}
          selectedDashboard={selectedDashboard}
          open={switcherOpen}
          onOpenChange={setSwitcherOpen}
          onSearch={setDashboardSearch}
          onSelect={selectDashboard}
          onToggleFavorite={toggleFavoriteDashboard}
        />
      )}

      <div className="dashboard-workspace">
        {selectedDashboard && (
          <Panel
            title={selectedDashboard.name}
            subtitle={`${selectedDashboard.widgets.length} widgets`}
            actions={
              <div className="dashboard-share-summary">
                {shareRows.map((share) => (
                  <Badge key={share.id} tone={share.access === 'editor' ? 'tone-warning' : 'tone-neutral'}>
                    {share.target_type === 'project_members' ? 'Project members' : share.user?.display_name ?? `User ${share.user_id}`}
                  </Badge>
                ))}
              </div>
            }
          >
            <DashboardFilters
              projects={projectsQuery.data ?? []}
              filters={filters}
              onProject={updateProjectFilter}
              onStatus={updateStatusFilter}
              onDue={updateDueFilter}
            />
            {editLayout && (
              <div className="layout-edit-bar">
                <span className="muted small">
                  <Settings2 size={14} aria-hidden="true" /> 12-column grid
                </span>
                <ActionRow>
                  {layoutMessage && <span className="muted small">{layoutMessage}</span>}
                  <Button variant="primary" disabled={saveLayoutMutation.isPending} onClick={() => saveLayoutMutation.mutate()}>
                    <Save size={15} aria-hidden="true" /> Save layout
                  </Button>
                </ActionRow>
              </div>
            )}
            <div ref={gridRef} className={`dashboard-grid ${editLayout ? 'editing' : ''}`}>
              {renderedWidgets.map((widget) => (
                <DashboardWidgetCard
                  key={widget.id}
                  widget={widget}
                  layout={layoutDraft[widget.id] ?? { id: widget.id, ...widget.layout }}
                  editLayout={editLayout}
                  onDrilldown={onDrilldown}
                  onMove={(patch) => updateLayoutItem(widget.id, patch)}
                  onPointerEdit={startPointerEdit}
                />
              ))}
            </div>
          </Panel>
        )}
      </div>

      <Dialog title="Add widget" open={addOpen} onClose={() => setAddOpen(false)}>
        <div className="form-grid">
          <Field label="Widget type">
            <Select
              value={newWidgetType}
              onChange={(event) => {
                const type = event.target.value as DashboardWidgetType
                setNewWidgetType(type)
                setNewWidgetTitle(defaultWidgetTitle[type])
              }}
            >
              {Object.entries(defaultWidgetTitle).map(([type, title]) => (
                <option key={type} value={type}>{title}</option>
              ))}
            </Select>
          </Field>
          <Field label="Title">
            <Input value={newWidgetTitle} onChange={(event) => setNewWidgetTitle(event.target.value)} />
          </Field>
          <div className="span-2">
            <ActionRow>
              <Button onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button variant="primary" disabled={!selectedDashboard || createWidgetMutation.isPending} onClick={() => createWidgetMutation.mutate()}>
                Add widget
              </Button>
            </ActionRow>
          </div>
        </div>
      </Dialog>

      {selectedDashboard && shareOpen && (
        <ShareDashboardDialog
          dashboard={selectedDashboard}
          shares={shareRows}
          open
          onClose={() => setShareOpen(false)}
        />
      )}

      <CreateDashboardDialog
        open={createOpen}
        name={newDashboardName}
        isPending={createDashboardMutation.isPending}
        onName={setNewDashboardName}
        onClose={() => setCreateOpen(false)}
        onCreate={() => createDashboardMutation.mutate()}
      />
    </>
  )
}

function CreateDashboardDialog({
  open,
  name,
  isPending,
  onName,
  onClose,
  onCreate,
}: {
  open: boolean
  name: string
  isPending: boolean
  onName: (name: string) => void
  onClose: () => void
  onCreate: () => void
}) {
  const canCreate = name.trim().length > 0
  return (
    <Dialog title="Create dashboard" open={open} onClose={onClose}>
      <div className="form-grid">
        <Field label="Name" className="span-2">
          <Input value={name} onChange={(event) => onName(event.target.value)} data-autofocus="true" />
        </Field>
        <div className="span-2">
          <ActionRow>
            <Button onClick={onClose}>Cancel</Button>
            <Button variant="primary" disabled={!canCreate || isPending} onClick={onCreate}>
              Create dashboard
            </Button>
          </ActionRow>
        </div>
      </div>
    </Dialog>
  )
}

function DashboardSwitcher({
  dashboards,
  favoriteDashboards,
  favoriteDashboardIds,
  search,
  searchedDashboards,
  selectedDashboard,
  open,
  onOpenChange,
  onSearch,
  onSelect,
  onToggleFavorite,
}: {
  dashboards: ConfigurableDashboard[]
  favoriteDashboards: ConfigurableDashboard[]
  favoriteDashboardIds: Set<ID>
  search: string
  searchedDashboards: ConfigurableDashboard[]
  selectedDashboard: ConfigurableDashboard
  open: boolean
  onOpenChange: (open: boolean) => void
  onSearch: (search: string) => void
  onSelect: (dashboardId: ID) => void
  onToggleFavorite: (dashboardId: ID) => void
}) {
  const hasSearch = search.trim().length > 0
  const menuDashboards = hasSearch
    ? searchedDashboards
    : dashboards.filter((dashboard) => !favoriteDashboardIds.has(dashboard.id))

  return (
    <div className="dashboard-switcher">
      <div>
        <span className="muted small strong">Saved dashboards</span>
        <button
          className="dashboard-switcher-trigger"
          aria-label="Open dashboard menu"
          aria-expanded={open}
          onClick={() => onOpenChange(!open)}
        >
          <span>
            <strong>{selectedDashboard.name}</strong>
            <span className="muted small">{selectedDashboard.owner?.display_name ?? selectedDashboard.owner_id}</span>
          </span>
          <ChevronDown size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="dashboard-switcher-meta">
        <Badge tone={selectedDashboard.access === 'owner' ? 'tone-success' : 'tone-info'}>
          {titleCase(`${selectedDashboard.access} access`)}
        </Badge>
        <span className="muted small">{dashboards.length} saved</span>
      </div>

      {open && (
        <div className="dashboard-switcher-menu">
          <label className="dashboard-search">
            <Search size={15} aria-hidden="true" />
            <span className="sr-only">Search dashboards</span>
            <Input
              aria-label="Search dashboards"
              value={search}
              placeholder="Search dashboards"
              onChange={(event) => onSearch(event.target.value)}
            />
          </label>

          {!hasSearch && (
            <DashboardSwitcherSection
              title="Favorites"
              dashboards={favoriteDashboards}
              favoriteDashboardIds={favoriteDashboardIds}
              selectedDashboardId={selectedDashboard.id}
              emptyText="No favorites yet"
              onSelect={onSelect}
              onToggleFavorite={onToggleFavorite}
            />
          )}

          <DashboardSwitcherSection
            title={hasSearch ? 'Search results' : 'Other dashboards'}
            dashboards={menuDashboards}
            favoriteDashboardIds={favoriteDashboardIds}
            selectedDashboardId={selectedDashboard.id}
            emptyText="No dashboards match"
            onSelect={onSelect}
            onToggleFavorite={onToggleFavorite}
          />
        </div>
      )}
    </div>
  )
}

function DashboardSwitcherSection({
  title,
  dashboards,
  favoriteDashboardIds,
  selectedDashboardId,
  emptyText,
  onSelect,
  onToggleFavorite,
}: {
  title: string
  dashboards: ConfigurableDashboard[]
  favoriteDashboardIds: Set<ID>
  selectedDashboardId: ID
  emptyText: string
  onSelect: (dashboardId: ID) => void
  onToggleFavorite: (dashboardId: ID) => void
}) {
  return (
    <div className="dashboard-switcher-section">
      <div className="dashboard-switcher-section-title">{title}</div>
      {dashboards.length === 0 && <div className="muted small">{emptyText}</div>}
      {dashboards.map((dashboard) => {
        const isFavorite = favoriteDashboardIds.has(dashboard.id)
        return (
          <div key={`${title}-${dashboard.id}`} className={`dashboard-menu-row ${selectedDashboardId === dashboard.id ? 'active' : ''}`}>
            <button
              className="dashboard-menu-select"
              aria-label={`Select ${dashboard.name}`}
              aria-current={selectedDashboardId === dashboard.id ? 'page' : undefined}
              onClick={() => onSelect(dashboard.id)}
            >
              <span>
                <strong>{dashboard.name}</strong>
                <span className="muted small">{dashboard.owner?.display_name ?? dashboard.owner_id}</span>
              </span>
              <Badge tone={dashboard.access === 'owner' ? 'tone-success' : 'tone-info'}>
                {titleCase(dashboard.access)}
              </Badge>
            </button>
            <IconButton
              aria-label={`${isFavorite ? 'Remove' : 'Add'} ${dashboard.name} favorite`}
              className={isFavorite ? 'favorite active' : 'favorite'}
              onClick={() => onToggleFavorite(dashboard.id)}
            >
              <Star size={14} aria-hidden="true" />
            </IconButton>
          </div>
        )
      })}
    </div>
  )
}

function DashboardFilters({
  projects,
  filters,
  onProject,
  onStatus,
  onDue,
}: {
  projects: Project[]
  filters: DashboardTaskFilters
  onProject: (value: string) => void
  onStatus: (value: string) => void
  onDue: (value: string) => void
}) {
  return (
    <div className="dashboard-filter-bar">
      <span className="muted small strong"><ListFilter size={14} aria-hidden="true" /> Filters</span>
      <Field label="Project">
        <Select value={filters.project_ids?.[0] ?? 'all'} onChange={(event) => onProject(event.target.value)}>
          <option value="all">All visible projects</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Status">
        <Select value={filters.statuses?.length === 4 ? 'open' : filters.statuses?.[0] ?? 'all'} onChange={(event) => onStatus(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="open">Open</option>
          <option value="new">New</option>
          <option value="accepted">Accepted</option>
          <option value="in_progress">In progress</option>
          <option value="on_hold">On hold</option>
          <option value="completed">Completed</option>
        </Select>
      </Field>
      <Field label="Due">
        <Select value={filters.due_window ?? 'all'} onChange={(event) => onDue(event.target.value)}>
          <option value="all">Any due date</option>
          <option value="overdue">Overdue</option>
          <option value="next_24_hours">Next 24 hours</option>
          <option value="next_7_days">Next 7 days</option>
        </Select>
      </Field>
    </div>
  )
}

function DashboardWidgetCard({
  widget,
  layout,
  editLayout,
  onDrilldown,
  onMove,
  onPointerEdit,
}: {
  widget: DashboardRenderedWidget
  layout: DashboardLayoutItem
  editLayout: boolean
  onDrilldown: (drilldown: DashboardDrilldown) => void
  onMove: (patch: Partial<DashboardLayoutItem>) => void
  onPointerEdit: (event: ReactPointerEvent<HTMLElement>, widgetId: ID, mode: DragState['mode']) => void
}) {
  const slug = widget.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
  return (
    <section
      className="dashboard-widget panel"
      data-testid={`dashboard-widget-${slug}`}
      style={{
        gridColumn: `${layout.x + 1} / span ${layout.w}`,
        gridRow: `${layout.y + 1} / span ${layout.h}`,
      }}
    >
      <div
        className="dashboard-widget-header"
        onPointerDown={(event) => onPointerEdit(event, widget.id, 'move')}
      >
        <div>
          <h2 className="panel-title">{widget.title}</h2>
          <p className="panel-subtitle">{titleCase(widget.type)}</p>
        </div>
        {editLayout && <Grip size={16} aria-hidden="true" />}
      </div>
      <div className="dashboard-widget-body">
        <WidgetResult widget={widget} onDrilldown={onDrilldown} />
      </div>
      {editLayout && (
        <div className="layout-controls">
          <IconButton aria-label={`Move ${widget.title} left`} onClick={() => onMove({ x: Math.max(0, layout.x - 1) })}>
            <ChevronsUpDown size={14} aria-hidden="true" className="rotate-left" />
          </IconButton>
          <IconButton aria-label={`Move ${widget.title} right`} onClick={() => onMove({ x: Math.min(GRID_COLUMNS - layout.w, layout.x + 1) })}>
            <ChevronsUpDown size={14} aria-hidden="true" className="rotate-right" />
          </IconButton>
          <IconButton aria-label={`Resize ${widget.title} wider`} onClick={() => onMove({ w: Math.min(GRID_COLUMNS - layout.x, layout.w + 1) })}>
            <Maximize2 size={14} aria-hidden="true" />
          </IconButton>
        </div>
      )}
      {editLayout && (
        <button
          className="resize-handle"
          aria-label={`Drag resize ${widget.title}`}
          onPointerDown={(event) => onPointerEdit(event, widget.id, 'resize')}
        />
      )}
    </section>
  )
}

function WidgetResult({ widget, onDrilldown }: { widget: DashboardRenderedWidget; onDrilldown: (drilldown: DashboardDrilldown) => void }) {
  if (widget.type === 'metric_tile') {
    return (
      <div className="metric-widget">
        <strong>{String(widget.result.value ?? 0)}</strong>
        <Button onClick={() => onDrilldown(widget.drilldown)} aria-label={`Open matching tasks for ${widget.title}`}>
          Open matching tasks
        </Button>
      </div>
    )
  }
  if (widget.type === 'status_breakdown' || widget.type === 'priority_breakdown') {
    const rows = (widget.result.items ?? []) as { value: string; count: number }[]
    return (
      <div className="breakdown-list">
        {rows.map((row) => (
          <div key={row.value} className="breakdown-row">
            <span>{titleCase(row.value)}</span>
            <strong>{row.count}</strong>
          </div>
        ))}
      </div>
    )
  }
  if (widget.type === 'technician_workload') {
    const rows = (widget.result.rows ?? []) as { assignee: { display_name: string; email: string }; open_count: number; oldest_due_at: string | null }[]
    return (
      <div className="detail-list">
        {rows.map((row) => (
          <div key={row.assignee.email} className="detail-row">
            <span><strong>{row.assignee.display_name}</strong><br /><span className="muted small">{row.assignee.email}</span></span>
            <span className="strong">{row.open_count}</span>
          </div>
        ))}
      </div>
    )
  }
  if (widget.type === 'due_soon_table') {
    const rows = (widget.result.rows ?? []) as Task[]
    if (!rows.length) return <EmptyState title="No matching tasks" />
    return (
      <DataTable>
        <tbody>
          {rows.map((task) => (
            <tr key={task.id}>
              <td data-label="Task">
                <button className="link-button strong" onClick={() => onDrilldown({ type: 'task_detail', project_id: task.project_id, task_id: task.id })}>
                  {task.title}
                </button>
                <div className="muted small">{task.project?.name}</div>
              </td>
              <td data-label="Status"><StatusBadge value={task.status} tone={statusTone[task.status]} /></td>
              <td data-label="Priority"><StatusBadge value={task.priority} tone={priorityTone[task.priority]} /></td>
              <td data-label="Due">{formatDateTime(task.due_at)}</td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    )
  }
  const rows = (widget.result.items ?? []) as { id: ID; action: string; project_id: ID | null; created_at: string }[]
  return (
    <div className="detail-list">
      {rows.map((item) => (
        <div key={item.id} className="detail-row">
          <span><strong>{item.action}</strong><br /><span className="muted small">Project {item.project_id}</span></span>
          <span className="muted small">{formatDateTime(item.created_at)}</span>
        </div>
      ))}
    </div>
  )
}

function ShareDashboardDialog({
  dashboard,
  shares,
  open,
  onClose,
}: {
  dashboard: ConfigurableDashboard
  shares: DashboardShare[]
  open: boolean
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const projectsQuery = useQuery({ queryKey: ['projects', 'dashboard-share'], queryFn: () => api.projects({}), enabled: open })
  const [targetType, setTargetType] = useState<DashboardShare['target_type']>('project_members')
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [userSearch, setUserSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState<UserSummary | null>(null)
  const [access, setAccess] = useState<DashboardShare['access']>('viewer')
  const [addedShares, setAddedShares] = useState<Partial<DashboardShare>[]>([])
  const [removedShareKeys, setRemovedShareKeys] = useState<Set<string>>(() => new Set())
  const projects = projectsQuery.data ?? []
  const selectedProject = selectedProjectId
    ? projects.find((project) => project.id === Number(selectedProjectId)) ?? null
    : projects[0] ?? null
  const userSearchQuery = useQuery({
    queryKey: ['users', 'dashboard-share', userSearch.trim()],
    queryFn: () => api.searchUsers(userSearch.trim()),
    enabled: open && targetType === 'user' && userSearch.trim().length >= 2,
  })
  const userResults = userSearchQuery.data ?? []
  const draftShareRows = useMemo(() => {
    const existingRows = shares
      .map((share, index) => {
        const persistedKey = dashboardShareKey(share, index)
        return {
          key: persistedKey,
          persistedKey,
          share,
        }
      })
      .filter((row) => !removedShareKeys.has(row.persistedKey))
    const addedRows = addedShares.map((share, index) => ({
      key: `added-${index}`,
      addedIndex: index,
      share,
    }))
    return [...existingRows, ...addedRows]
  }, [addedShares, removedShareKeys, shares])
  const draftShares = useMemo(
    () => draftShareRows.map((row) => row.share),
    [draftShareRows],
  )
  const existingShareTargetKeys = useMemo(
    () => new Set(draftShares.map(shareTargetKey).filter((key): key is string => key !== null)),
    [draftShares],
  )
  const pendingShareTargetKey = targetType === 'project_members' && selectedProject
    ? `project_members:${selectedProject.id}`
    : targetType === 'user' && selectedUser
      ? `user:${selectedUser.id}`
      : null
  const targetAlreadyShared = pendingShareTargetKey !== null && existingShareTargetKeys.has(pendingShareTargetKey)
  const canAddShare = pendingShareTargetKey !== null && !targetAlreadyShared

  const saveSharesMutation = useMutation({
    mutationFn: () => api.saveDashboardShares(dashboard.id, draftShares),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['dashboard-shares', dashboard.id] })
      await queryClient.invalidateQueries({ queryKey: ['dashboards'] })
      onClose()
    },
  })

  const addShare = () => {
    if (targetType === 'project_members' && !selectedProject) return
    if (targetType === 'user' && !selectedUser) return
    setAddedShares((current) => [
      ...current,
      {
        target_type: targetType,
        user_id: targetType === 'user' ? selectedUser!.id : null,
        user: targetType === 'user' ? selectedUser : null,
        project_id: targetType === 'project_members' ? selectedProject!.id : null,
        project: targetType === 'project_members' ? { id: selectedProject!.id, name: selectedProject!.name } : null,
        access,
      },
    ])
    setSelectedUser(null)
    setUserSearch('')
  }

  const removeShare = (row: DraftShareRow) => {
    if (row.addedIndex !== undefined) {
      setAddedShares((current) => current.filter((_share, index) => index !== row.addedIndex))
      return
    }
    if (!row.persistedKey) return
    setRemovedShareKeys((current) => new Set(current).add(row.persistedKey!))
  }

  return (
    <Dialog title="Share dashboard" open={open} onClose={onClose}>
      <div className="grid">
        <div className="detail-list">
          {draftShareRows.map((row, index) => (
            <div key={row.key} className="detail-row">
              <span>
                <strong>{row.share.target_type === 'project_members' ? 'Project members' : 'Specific user'}</strong>
                <br />
                <span className="muted small">
                  {shareTargetLabel(row.share, projects)}
                </span>
              </span>
              <span className="share-row-actions">
                <Badge tone={row.share.access === 'editor' ? 'tone-warning' : 'tone-neutral'}>{titleCase(`${row.share.access} access`)}</Badge>
                <IconButton
                  aria-label={`Remove share ${index + 1}`}
                  onClick={() => removeShare(row)}
                >
                  <Trash2 size={14} aria-hidden="true" />
                </IconButton>
              </span>
            </div>
          ))}
        </div>
        <div className="form-grid">
          <Field label="Target">
            <Select
              value={targetType}
              onChange={(event) => {
                setTargetType(event.target.value as DashboardShare['target_type'])
                setSelectedUser(null)
                setUserSearch('')
              }}
            >
              <option value="project_members">Project members</option>
              <option value="user">Specific user</option>
            </Select>
          </Field>
          {targetType === 'project_members' ? (
            <Field label="Project">
              <Select
                value={selectedProject ? String(selectedProject.id) : ''}
                onChange={(event) => setSelectedProjectId(event.target.value)}
              >
                {!projects.length && (
                  <option value="" disabled>
                    {projectsQuery.isLoading ? 'Loading projects...' : 'No projects available'}
                  </option>
                )}
                {projects.map((project) => (
                  <option key={project.id} value={String(project.id)}>{project.name}</option>
                ))}
              </Select>
            </Field>
          ) : (
            <div className="field">
              <span id="dashboard-share-user-search-label">Search users</span>
              <Input
                id="dashboard-share-user-search"
                aria-labelledby="dashboard-share-user-search-label"
                value={userSearch}
                placeholder="Search by name or email"
                onChange={(event) => {
                  setUserSearch(event.target.value)
                  setSelectedUser(null)
                }}
              />
              {selectedUser && (
                <div className="selected-share-target">
                  <span>
                    <strong>{selectedUser.display_name}</strong>
                    <span className="muted small">{selectedUser.email}</span>
                  </span>
                </div>
              )}
              {userSearch.trim().length >= 2 && !selectedUser && (
                <div className="share-picker-results">
                  {userSearchQuery.isLoading && <span className="muted small">Searching users...</span>}
                  {userResults.map((user) => (
                    <button
                      key={user.id}
                      className="share-picker-result"
                      type="button"
                      aria-label={`Select ${user.display_name}`}
                      onClick={() => setSelectedUser(user)}
                    >
                      <strong>{user.display_name}</strong>
                      <span className="muted small">{user.email}</span>
                    </button>
                  ))}
                  {!userSearchQuery.isLoading && userResults.length === 0 && (
                    <span className="muted small">No users match</span>
                  )}
                </div>
              )}
            </div>
          )}
          <Field label="Access">
            <Select value={access} onChange={(event) => setAccess(event.target.value as DashboardShare['access'])}>
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
            </Select>
          </Field>
          <div className="field">
            <span>{targetAlreadyShared ? 'Already shared' : '\u00a0'}</span>
            <Button disabled={!canAddShare} onClick={addShare}>Add share</Button>
          </div>
        </div>
        <ActionRow>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={saveSharesMutation.isPending} onClick={() => saveSharesMutation.mutate()}>
            Save sharing
          </Button>
        </ActionRow>
      </div>
    </Dialog>
  )
}

function filterDashboards(dashboards: ConfigurableDashboard[], search: string) {
  const query = search.trim().toLowerCase()
  if (!query) return dashboards
  return dashboards.filter((dashboard) =>
    `${dashboard.name} ${dashboard.owner?.display_name ?? ''} ${dashboard.owner?.email ?? ''}`
      .toLowerCase()
      .includes(query),
  )
}

function shareTargetLabel(share: Partial<DashboardShare>, projects: Project[]) {
  if (share.target_type === 'project_members') {
    return share.project?.name ?? projects.find((project) => project.id === share.project_id)?.name ?? `Project ${share.project_id}`
  }
  if (share.user?.display_name && share.user.email) {
    return `${share.user.display_name} (${share.user.email})`
  }
  return share.user?.display_name ?? share.user?.email ?? `User ${share.user_id}`
}

function shareTargetKey(share: Partial<DashboardShare>) {
  if (share.target_type === 'project_members' && share.project_id) {
    return `project_members:${share.project_id}`
  }
  if (share.target_type === 'user' && share.user_id) {
    return `user:${share.user_id}`
  }
  return null
}

function cacheSavedDashboardLayout(queryClient: ReturnType<typeof useQueryClient>, dashboardId: ID, widgets: DashboardWidget[]) {
  const widgetMap = new Map(widgets.map((widget) => [widget.id, widget]))
  queryClient.setQueryData<ConfigurableDashboard[]>(['dashboards'], (current) =>
    current?.map((dashboard) =>
      dashboard.id === dashboardId
        ? {
            ...dashboard,
            widgets: dashboard.widgets.map((widget) => {
              const savedWidget = widgetMap.get(widget.id)
              return savedWidget ? { ...widget, ...savedWidget } : widget
            }),
          }
        : dashboard,
    ),
  )
  queryClient.setQueriesData<DashboardRender>(
    { queryKey: ['dashboard-render', dashboardId] },
    (current) => {
      if (!current) return current
      return {
        ...current,
        widgets: current.widgets.map((widget) => {
          const savedWidget = widgetMap.get(widget.id)
          return savedWidget
            ? {
                ...widget,
                layout: {
                  x: savedWidget.x,
                  y: savedWidget.y,
                  w: savedWidget.w,
                  h: savedWidget.h,
                  order: savedWidget.order,
                },
              }
            : widget
        }),
      }
    },
  )
}

function dashboardShareKey(share: DashboardShare, index: number) {
  return share.id ? `share-${share.id}` : `${share.target_type}-${share.user_id ?? ''}-${share.project_id ?? ''}-${index}`
}

function nextWidgetY(dashboard: ConfigurableDashboard | null) {
  if (!dashboard?.widgets.length) return 0
  return Math.max(...dashboard.widgets.map((widget) => widget.y + widget.h))
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
