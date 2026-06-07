import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, LogOut } from 'lucide-react'
import { toast } from 'sonner'
import { api, getStoredSession } from '../lib/api'
import type { CurrentUser, ID } from '../lib/types'
import { relativeTime } from '../lib/utils'
import { ActionRow, Badge, Button, ConfirmButton, EmptyState, Field, Input, Panel } from '../components/ui'
import { mutationError } from './helpers'
import { PageHeading } from './layout'

const priorityTimezones = ['UTC', 'Europe/Prague', 'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles', 'Asia/Tokyo']

function timezoneOptions(currentTimezone?: string) {
  const supported = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : []
  return Array.from(new Set([currentTimezone, ...priorityTimezones, ...supported].filter(Boolean) as string[]))
}

export function NotificationsView() {
  const queryClient = useQueryClient()
  const notificationsQuery = useQuery({ queryKey: ['notifications'], queryFn: api.notifications })
  const readMutation = useMutation({
    mutationFn: (id: ID) => api.readNotification(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const readAllMutation = useMutation({
    mutationFn: api.readAllNotifications,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const notifications = notificationsQuery.data ?? []
  return (
    <>
      <PageHeading
        title="Notifications"
        detail="Read watcher, assignment, lifecycle, and reminder notifications."
        actions={<Button onClick={() => readAllMutation.mutate()}><Check size={15} /> Mark all read</Button>}
      />
      <Panel>
        {notifications.length ? (
          <div className="grid">
            {notifications.map((item) => (
              <div key={item.id} className="panel" style={{ boxShadow: 'none' }}>
                <div className="panel-body toolbar" style={{ justifyContent: 'space-between' }}>
                  <div>
                    <div className="strong">{item.title}</div>
                    <div className="muted small">{item.message}</div>
                    <div className="muted small">{relativeTime(item.created_at)}</div>
                  </div>
                  <ActionRow>
                    <Badge tone={item.read_at ? 'tone-neutral' : 'tone-info'}>{item.read_at ? 'Read' : 'Unread'}</Badge>
                    {!item.read_at && <Button onClick={() => readMutation.mutate(item.id)}>Mark read</Button>}
                  </ActionRow>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No notifications" />
        )}
      </Panel>
    </>
  )
}

export function ProfileView({ user, onLoggedOut }: { user?: CurrentUser; onLoggedOut: () => void }) {
  const queryClient = useQueryClient()
  const profileQuery = useQuery({ queryKey: ['profile'], queryFn: api.profile })
  const [timezoneDraft, setTimezoneDraft] = useState<string | null>(null)
  const timezone = timezoneDraft ?? profileQuery.data?.timezone ?? 'Europe/Prague'
  const timezones = useMemo(() => timezoneOptions(profileQuery.data?.timezone), [profileQuery.data?.timezone])
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const updateProfileMutation = useMutation({
    mutationFn: () => api.updateProfile({ timezone }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setTimezoneDraft(null)
      toast.success('Profile updated')
    },
  })
  const passwordMutation = useMutation({
    mutationFn: () =>
      api.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newPassword,
      }),
    onSuccess: () => toast.success('Password changed'),
    onError: (error) => toast.error(mutationError(error)),
  })
  const logoutMutation = useMutation({
    mutationFn: () => api.logout(getStoredSession()?.refresh ?? ''),
    onSettled: onLoggedOut,
  })

  return (
    <>
      <PageHeading title="Profile" detail="Manage local account preferences and password flows." />
      <div className="grid cols-2">
        <Panel title="Account">
          <div className="detail-list">
            <div className="detail-row"><span>Name</span><strong>{user?.display_name}</strong></div>
            <div className="detail-row"><span>Email</span><strong>{user?.email}</strong></div>
            <div className="detail-row"><span>Staff</span><strong>{user?.is_staff ? 'Yes' : 'No'}</strong></div>
            <div className="detail-row"><span>Current timezone</span><strong>{profileQuery.data?.timezone}</strong></div>
          </div>
        </Panel>
        <Panel title="Preferences">
          <div className="grid">
            <Field label="Timezone">
              <select className="select" value={timezone} onChange={(event) => setTimezoneDraft(event.target.value)}>
                {timezones.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </Field>
            <Button variant="primary" onClick={() => updateProfileMutation.mutate()}>Save timezone</Button>
          </div>
        </Panel>
        <Panel title="Password">
          <div className="grid">
            <Field label="Old password"><Input type="password" value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} /></Field>
            <Field label="New password"><Input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></Field>
            <Button onClick={() => passwordMutation.mutate()}>Change password</Button>
          </div>
        </Panel>
        <Panel title="Session">
          <ConfirmButton
            variant="danger"
            title="Log out"
            description="End this browser session and return to authentication."
            confirmLabel="Log out"
            onConfirm={() => logoutMutation.mutate()}
          >
            <LogOut size={15} /> Log out
          </ConfirmButton>
        </Panel>
      </div>
    </>
  )
}
