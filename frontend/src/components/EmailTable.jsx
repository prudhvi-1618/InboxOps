import { useState } from 'react'

// Columns exactly as specified in the brief
const COLUMNS = [
  { key: 'from_name',   label: 'From name',    width: 'w-36' },
  { key: 'from_email',  label: 'From email',   width: 'w-48' },
  { key: 'subject',     label: 'Subject',      width: 'w-56' },
  { key: 'received_at', label: 'Received at',  width: 'w-40' },
  { key: 'thread_id',   label: 'Thread ID',    width: 'w-28' },
  { key: '_body',       label: 'Body preview', width: 'w-64' },
]

function formatDate(raw) {
  if (!raw) return '—'
  try {
    return new Date(raw).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  } catch {
    return raw
  }
}

function getCellValue(email, key) {
  if (key === '_body') {
    const body = email.body || ''
    return body.length > 80 ? body.slice(0, 80) + '…' : body
  }
  if (key === 'received_at') return formatDate(email.received_at)
  return email[key] || '—'
}

export default function EmailTable({ emails }) {
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20
  const totalPages = Math.ceil(emails.length / PAGE_SIZE)
  const visible = emails.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Table header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            2 — Raw email preview
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {emails.length} email{emails.length !== 1 ? 's' : ''} — shown before routing, independent of classification logic
          </p>
        </div>
        <span className="px-2.5 py-1 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
          {emails.length} emails
        </span>
      </div>

      {/* Scrollable table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-10">
                #
              </th>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  className={`text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide ${col.width}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {visible.map((email, idx) => (
              <tr
                key={email.email_id || idx}
                className="hover:bg-gray-50 transition-colors"
              >
                <td className="px-4 py-3 text-xs text-gray-400 font-mono">
                  {page * PAGE_SIZE + idx + 1}
                </td>
                {COLUMNS.map(col => (
                  <td
                    key={col.key}
                    className={`px-4 py-3 text-gray-700 ${col.width} max-w-0`}
                  >
                    <div className="truncate" title={String(email[col.key] || '')}>
                      {col.key === 'thread_id' ? (
                        <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                          {getCellValue(email, col.key)}
                        </span>
                      ) : col.key === '_body' ? (
                        <span className="text-gray-400 italic text-xs">
                          {getCellValue(email, col.key)}
                        </span>
                      ) : (
                        getCellValue(email, col.key)
                      )}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-gray-50">
          <p className="text-xs text-gray-500">
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, emails.length)} of {emails.length}
          </p>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-gray-200 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  page === i
                    ? 'bg-brand-500 text-white border-brand-500'
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-100'
                }`}
              >
                {i + 1}
              </button>
            ))}
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-gray-200 text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
