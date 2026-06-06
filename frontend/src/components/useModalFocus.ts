import { useEffect, useRef, type KeyboardEvent } from 'react'

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function focusableChildren(container: HTMLElement | null) {
  if (!container) return []
  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (element) => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true',
  )
}

export function useModalFocus<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const containerRef = useRef<T | null>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return undefined
    returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const focusTarget =
      containerRef.current?.querySelector<HTMLElement>('[data-autofocus="true"]') ??
      focusableChildren(containerRef.current)[0] ??
      containerRef.current
    focusTarget?.focus()

    return () => {
      returnFocusRef.current?.focus()
    }
  }, [open])

  const onKeyDown = (event: KeyboardEvent<T>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }
    if (event.key !== 'Tab') return

    const focusable = focusableChildren(containerRef.current)
    if (!focusable.length) {
      event.preventDefault()
      containerRef.current?.focus()
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return { ref: containerRef, onKeyDown, tabIndex: -1 }
}
