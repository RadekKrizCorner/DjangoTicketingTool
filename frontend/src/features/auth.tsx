import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '../lib/api'
import { ActionRow, Button, Field, Input } from '../components/ui'
import { mutationError } from './helpers'

export function AuthScreen({ onAuthenticated }: { onAuthenticated: (session: { access: string; refresh: string }) => void }) {
  const [mode, setMode] = useState<'login' | 'register' | 'reset'>('login')
  const [email, setEmail] = useState('demo.admin@example.com')
  const [password, setPassword] = useState('DemoAdmin123!')
  const [displayName, setDisplayName] = useState('Demo Admin')
  const [resetToken, setResetToken] = useState('')
  const [resetUid, setResetUid] = useState('')

  const loginMutation = useMutation({
    mutationFn: () => api.login({ email, password }),
    onSuccess: (session) => {
      toast.success('Signed in')
      onAuthenticated(session)
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const registerMutation = useMutation({
    mutationFn: () =>
      api.register({
        email,
        password,
        password_confirm: password,
        display_name: displayName,
      }),
    onSuccess: async () => {
      const session = await api.login({ email, password })
      toast.success('Account created')
      onAuthenticated(session)
    },
    onError: (error) => toast.error(mutationError(error)),
  })
  const resetRequestMutation = useMutation({
    mutationFn: () => api.passwordResetRequest({ email }),
    onSuccess: () => toast.success('Password reset accepted'),
    onError: (error) => toast.error(mutationError(error)),
  })
  const resetConfirmMutation = useMutation({
    mutationFn: () =>
      api.passwordResetConfirm({
        uid: resetUid,
        token: resetToken,
        new_password: password,
        new_password_confirm: password,
      }),
    onSuccess: () => toast.success('Password reset confirmed'),
    onError: (error) => toast.error(mutationError(error)),
  })

  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="brand-row">
          <span className="brand-mark">RK</span>
          <span>RKRIZ Workspace</span>
        </div>
        <div>
          <h1>Project delivery control for the Django ticketing backend.</h1>
          <p>
            Manage projects, roles, task workflow, comments, attachments, notifications, lifecycle
            schedules, and audit history from one operational UI.
          </p>
        </div>
        <p className="small">React 19 · TanStack Query · Vite · TypeScript · DRF API</p>
      </section>
      <section className="auth-card">
        <div className="grid" style={{ gap: 22 }}>
          <div>
            <div className="brand-row">
              <span className="brand-mark">RK</span>
              <span>Django Ticketing Tool</span>
            </div>
            <h1 style={{ margin: '28px 0 8px', fontSize: 30 }}>
              {mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : 'Reset password'}
            </h1>
            <p className="muted">Use the seeded demo account or connect to your local API.</p>
          </div>
          <div className="tabs">
            <button className={`tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>Login</button>
            <button className={`tab ${mode === 'register' ? 'active' : ''}`} onClick={() => setMode('register')}>Register</button>
            <button className={`tab ${mode === 'reset' ? 'active' : ''}`} onClick={() => setMode('reset')}>Reset</button>
          </div>
          <div className="grid">
            {mode === 'register' && (
              <Field label="Display name">
                <Input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </Field>
            )}
            <Field label="Email">
              <Input value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
            <Field label={mode === 'reset' ? 'New password' : 'Password'}>
              <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </Field>
            {mode === 'reset' && (
              <div className="form-grid">
                <Field label="UID">
                  <Input value={resetUid} onChange={(event) => setResetUid(event.target.value)} />
                </Field>
                <Field label="Token">
                  <Input value={resetToken} onChange={(event) => setResetToken(event.target.value)} />
                </Field>
              </div>
            )}
            {mode === 'login' && (
              <Button variant="primary" onClick={() => loginMutation.mutate()} disabled={loginMutation.isPending}>
                Sign in
              </Button>
            )}
            {mode === 'register' && (
              <Button variant="primary" onClick={() => registerMutation.mutate()} disabled={registerMutation.isPending}>
                Create account
              </Button>
            )}
            {mode === 'reset' && (
              <ActionRow>
                <Button onClick={() => resetRequestMutation.mutate()}>Request reset</Button>
                <Button variant="primary" onClick={() => resetConfirmMutation.mutate()}>Confirm reset</Button>
              </ActionRow>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}
