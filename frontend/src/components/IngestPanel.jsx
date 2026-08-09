import { useState } from 'react'
import { API_URL } from '../config.js'

const CANDIDATE_ID = import.meta.env.VITE_CANDIDATE_ID || ''

export default function IngestPanel({ emails, onResult }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleIngest() {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const resp = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: CANDIDATE_ID,
          emails,
        }),
      })

      const data = await resp.json()

      if (!resp.ok) {
        throw new Error(data?.detail || `Server error ${resp.status}`)
      }

      setResult(data)
      if (onResult) onResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            3 — Route this batch
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {emails.length} email{emails.length !== 1 ? 's' : ''} ready to classify and route
          </p>
        </div>

        <button
          onClick={handleIngest}
          disabled={loading || emails.length === 0}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner />
              Routing…
            </>
          ) : (
            '⚡ Route batch'
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-100 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-blue-50 border border-blue-100">
          <Spinner className="text-blue-500" />
          <div>
            <p className="text-sm font-medium text-blue-700">Processing batch…</p>
            <p className="text-xs text-blue-500 mt-0.5">
              Classifying with Gemini and writing to Task API. This may take up to 60 seconds for large batches.
            </p>
          </div>
        </div>
      )}

      {/* Result summary */}
      {result && !loading && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <SummaryTile
              label="Processed"
              value={result.processed}
              color="gray"
            />
            <SummaryTile
              label="Tasks created"
              value={result.tasks_created}
              color="green"
            />
            <SummaryTile
              label="Tasks updated"
              value={result.tasks_updated}
              color="blue"
            />
            <SummaryTile
              label="Skipped"
              value={result.skipped}
              color="amber"
            />
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-100">
              <p className="text-sm font-medium text-red-700 mb-1">
                {result.errors.length} error{result.errors.length !== 1 ? 's' : ''}
              </p>
              <ul className="text-xs text-red-600 space-y-0.5">
                {result.errors.map((e, i) => (
                  <li key={i}>• {e}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs text-gray-400 text-right">
            Routing complete — switch to "Ask questions" to query results
          </p>
        </div>
      )}
    </div>
  )
}

function SummaryTile({ label, value, color }) {
  const colors = {
    gray:  'bg-gray-50  border-gray-200  text-gray-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    blue:  'bg-blue-50  border-blue-200  text-blue-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 ${colors[color]}`}>
      <p className="text-2xl font-semibold">{value ?? 0}</p>
      <p className="text-xs mt-0.5 opacity-70">{label}</p>
    </div>
  )
}

function Spinner() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" className="animate-spin" fill="none" stroke="currentColor" strokeWidth={2.5}>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
    </svg>
  )
}
