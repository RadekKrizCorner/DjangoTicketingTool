import type { ReactNode } from 'react'

export function PageHeading({ title, detail, actions }: { title: string; detail: string; actions?: ReactNode }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{detail}</p>
      </div>
      {actions}
    </div>
  )
}
