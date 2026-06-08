import type { DashboardLayoutItem, ID } from '../lib/types'

export const DASHBOARD_GRID_COLUMNS = 12

export function mergeLayoutDraft(base: Record<ID, DashboardLayoutItem>, overrides: Record<ID, DashboardLayoutItem>) {
  const draft = { ...base }
  Object.values(overrides).forEach((override) => {
    if (Object.hasOwn(base, override.id)) draft[override.id] = override
  })
  return draft
}

export function normalizeLayoutItem(item: DashboardLayoutItem): DashboardLayoutItem {
  const next = { ...item }
  next.w = clamp(next.w, 1, DASHBOARD_GRID_COLUMNS)
  next.x = clamp(next.x, 0, DASHBOARD_GRID_COLUMNS - next.w)
  next.h = Math.max(1, next.h)
  next.y = Math.max(0, next.y)
  return next
}

export function layoutCollides(item: DashboardLayoutItem, others: DashboardLayoutItem[]) {
  return others.some((other) => layoutItemsOverlap(item, other))
}

export function layoutItemsOverlap(first: DashboardLayoutItem, second: DashboardLayoutItem) {
  return !(
    first.x + first.w <= second.x ||
    second.x + second.w <= first.x ||
    first.y + first.h <= second.y ||
    second.y + second.h <= first.y
  )
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
