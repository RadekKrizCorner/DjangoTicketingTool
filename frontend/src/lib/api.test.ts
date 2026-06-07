import { afterEach, describe, expect, it, vi } from 'vitest'

function jsonResponse(status: number, payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('live api client', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.resetModules()
  })

  it('refreshes an expired access token and retries the original mutation once', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_DEMO_MODE', 'live')
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { errors: [{ code: 'token_not_valid', detail: 'Given token not valid for any token type', field: null }] }))
      .mockResolvedValueOnce(jsonResponse(200, { data: { access: 'new-access', refresh: 'new-refresh' } }))
      .mockResolvedValueOnce(jsonResponse(201, { data: { id: 91, name: 'Retry Project' } }))
    vi.stubGlobal('fetch', fetchMock)

    const { api, getStoredSession, storeSession } = await import('./api')
    storeSession({ access: 'expired-access', refresh: 'old-refresh' })

    const project = await api.createProject({ name: 'Retry Project', description: '' })

    expect(project.id).toBe(91)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/projects/')
    expect((fetchMock.mock.calls[0][1].headers as Headers).get('Authorization')).toBe('Bearer expired-access')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/users/token/refresh/')
    expect(fetchMock.mock.calls[2][0]).toBe('/api/v1/projects/')
    expect((fetchMock.mock.calls[2][1].headers as Headers).get('Authorization')).toBe('Bearer new-access')
    expect(getStoredSession()).toEqual({ access: 'new-access', refresh: 'new-refresh' })
  })
})
