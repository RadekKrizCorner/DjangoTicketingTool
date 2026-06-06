import {
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'
import { X } from 'lucide-react'
import { cn, titleCase } from '../lib/utils'
import { useModalFocus } from './useModalFocus'

export function Button({
  className,
  variant = 'default',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'primary' | 'danger' | 'ghost' }) {
  return <button className={cn('button', variant !== 'default' && variant, className)} {...props} />
}

export function IconButton({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cn('icon-button', className)} {...props} />
}

export function Field({
  label,
  children,
  className,
}: {
  label: string
  children: ReactNode
  className?: string
}) {
  return (
    <label className={cn('field', className)}>
      <span>{label}</span>
      {children}
    </label>
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn('input', props.className)} {...props} />
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn('select', props.className)} {...props} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn('textarea', props.className)} {...props} />
}

export function Badge({ children, tone }: { children: ReactNode; tone?: string }) {
  return <span className={cn('badge', tone)}>{children}</span>
}

export function StatusBadge({ value, tone }: { value: string; tone?: string }) {
  return <Badge tone={tone}>{titleCase(value)}</Badge>
}

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('panel', className)}>
      {(title || subtitle || actions) && (
        <div className="panel-header">
          <div>
            {title && <h2 className="panel-title">{title}</h2>}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="panel-body">{children}</div>
    </section>
  )
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="empty">
      <div>
        <div className="strong">{title}</div>
        {detail && <p className="muted small">{detail}</p>}
      </div>
    </div>
  )
}

export function Dialog({
  title,
  open,
  onClose,
  children,
}: {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
}) {
  const focusScope = useModalFocus<HTMLElement>(open, onClose)

  if (!open) return null
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        {...focusScope}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <h2 className="panel-title">{title}</h2>
          <IconButton aria-label="Close dialog" onClick={onClose}>
            <X size={16} aria-hidden="true" />
          </IconButton>
        </div>
        <div className="dialog-body">{children}</div>
      </section>
    </div>
  )
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isPending = false,
  onConfirm,
  onClose,
}: {
  open: boolean
  title: string
  description: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  isPending?: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <Dialog title={title} open={open} onClose={onClose}>
      <div className="grid">
        <p className="muted" style={{ margin: 0 }}>{description}</p>
        <ActionRow>
          <Button data-autofocus="true" onClick={onClose} disabled={isPending}>{cancelLabel}</Button>
          <Button
            variant="danger"
            onClick={() => {
              onConfirm()
              onClose()
            }}
            disabled={isPending}
          >
            {confirmLabel}
          </Button>
        </ActionRow>
      </div>
    </Dialog>
  )
}

export function ConfirmButton({
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  children,
  disabled,
  ...props
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'> & {
  title: string
  description: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  variant?: 'default' | 'primary' | 'danger' | 'ghost'
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button {...props} disabled={disabled} onClick={() => setOpen(true)}>
        {children}
      </Button>
      <ConfirmDialog
        open={open}
        title={title}
        description={description}
        confirmLabel={confirmLabel}
        cancelLabel={cancelLabel}
        isPending={disabled}
        onConfirm={onConfirm}
        onClose={() => setOpen(false)}
      />
    </>
  )
}

export function DataTable({ children }: { children: ReactNode }) {
  return (
    <div className="table-wrap">
      <table className="data-table">{children}</table>
    </div>
  )
}

export function ActionRow({ children }: { children: ReactNode }) {
  return <div className="toolbar">{children}</div>
}
