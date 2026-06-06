import { clsx, type ClassValue } from 'clsx'
import { formatDistanceToNowStrict, format } from 'date-fns'
import { twMerge } from 'tailwind-merge'
import type { TaskPriority, TaskStatus } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

export function formatDateTime(value: string | null) {
  if (!value) return 'Not set'
  return format(new Date(value), 'MMM d, yyyy HH:mm')
}

export function relativeTime(value: string | null) {
  if (!value) return 'No date'
  return formatDistanceToNowStrict(new Date(value), { addSuffix: true })
}

export function bytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

export const statusTone: Record<TaskStatus, string> = {
  new: 'tone-neutral',
  accepted: 'tone-info',
  in_progress: 'tone-active',
  on_hold: 'tone-warning',
  completed: 'tone-success',
  cancelled: 'tone-danger',
}

export const priorityTone: Record<TaskPriority, string> = {
  low: 'tone-neutral',
  medium: 'tone-info',
  high: 'tone-warning',
  urgent: 'tone-danger',
}

export const workflowOrder: TaskStatus[] = [
  'new',
  'accepted',
  'in_progress',
  'on_hold',
  'completed',
  'cancelled',
]
