import type { QueryClient } from '@tanstack/react-query'
import { ApiError } from '../lib/api'
import type { ID } from '../lib/types'

export function mutationError(error: unknown) {
  if (error instanceof ApiError) return error.errors[0]?.detail ?? error.message
  if (error instanceof Error) return error.message
  return 'Request failed'
}

export function invalidateProject(queryClient: QueryClient, projectId?: ID) {
  queryClient.invalidateQueries({ queryKey: ['projects'] })
  queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  queryClient.invalidateQueries({ queryKey: ['my-tasks'] })
  queryClient.invalidateQueries({ queryKey: ['due-soon'] })
  if (projectId) {
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
    queryClient.invalidateQueries({ queryKey: ['members', projectId] })
    queryClient.invalidateQueries({ queryKey: ['audit', projectId] })
    queryClient.invalidateQueries({ queryKey: ['limits', projectId] })
  }
}
