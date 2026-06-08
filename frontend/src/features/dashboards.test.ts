import { describe, expect, it } from 'vitest'
import {
  layoutItemsOverlap,
  mergeLayoutDraft,
  normalizeLayoutItem,
} from './dashboard-layout'
import type { DashboardLayoutItem } from '../lib/types'

describe('dashboard layout helpers', () => {
  it('allows adjacent widgets that only touch edges', () => {
    const first: DashboardLayoutItem = { id: 1, x: 0, y: 0, w: 4, h: 2, order: 1 }
    const second: DashboardLayoutItem = { id: 2, x: 4, y: 0, w: 4, h: 2, order: 2 }

    expect(layoutItemsOverlap(first, second)).toBe(false)
  })

  it('detects partial widget overlap', () => {
    const first: DashboardLayoutItem = { id: 1, x: 0, y: 0, w: 4, h: 2, order: 1 }
    const second: DashboardLayoutItem = { id: 2, x: 3, y: 1, w: 4, h: 2, order: 2 }

    expect(layoutItemsOverlap(first, second)).toBe(true)
  })

  it('normalizes widgets to the responsive grid bounds', () => {
    const item: DashboardLayoutItem = { id: 1, x: 11, y: -2, w: 4, h: 0, order: 1 }

    expect(normalizeLayoutItem(item)).toEqual({ id: 1, x: 8, y: 0, w: 4, h: 1, order: 1 })
  })

  it('ignores stale layout overrides for removed widgets', () => {
    const base: Record<number, DashboardLayoutItem> = {
      1: { id: 1, x: 0, y: 0, w: 4, h: 2, order: 1 },
    }
    const overrides: Record<number, DashboardLayoutItem> = {
      1: { id: 1, x: 4, y: 0, w: 4, h: 2, order: 1 },
      99: { id: 99, x: 8, y: 0, w: 4, h: 2, order: 2 },
    }

    expect(mergeLayoutDraft(base, overrides)).toEqual({
      1: { id: 1, x: 4, y: 0, w: 4, h: 2, order: 1 },
    })
  })
})
