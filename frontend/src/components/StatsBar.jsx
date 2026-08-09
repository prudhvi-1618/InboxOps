import { useState, useEffect } from 'react'
import { API_URL } from '../config.js'

export default function StatsBar() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function fetchStats() {
    try {
      const resp = await fetch(`${API_URL}/api/stats`)
      if (!resp.ok) throw new Error(`${resp.status}`)
      const data = await resp.json()
      setStats(data)
      setError('')
    } catch (e) {
      setError(`Could not load stats: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Fetch on mount + every 30 seconds
  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30_000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-5 py-4">
        <p className="text-sm text-gray-400 animate-pulse">Loading stats…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex items-center justify-between">
        <p className="text-sm text-red-500">{error}</p>
        <button
          onClick={fetchStats}
          className="text-xs text-brand-500 hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  const totals = stats?.totals || {}
  const byCategory = stats?.by_category || []
  const skipReasons = stats?.skip_reasons || []
  const spurious = stats?.spurious_rate || {}

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          Live stats
        </h2>
        <button
          onClick={fetchStats}
          className="text-xs text-gray-400 hover:text-brand-500 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Top-level tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Tile label="Processed" value={totals.processed ?? 0} color="gray" />
        <Tile label="Created"   value={totals.created   ?? 0} color="green" />
        <Tile label="Updated"   value={totals.updated   ?? 0} color="blue" />
        <Tile label="Skipped"   value={totals.skipped   ?? 0} color="amber" />
      </div>

      {/* Category breakdown */}
      {byCategory.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            By category
          </p>
          <div className="flex flex-wrap gap-2">
            {byCategory.map(row => (
              <span
                key={row.category}
                className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600"
              >
                {row.category} · {row.count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Skip reasons */}
      {skipReasons.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Skipped
          </p>
          <div className="flex flex-wrap gap-2">
            {skipReasons.map(row => (
              <span
                key={row.skipped_reason}
                className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700"
              >
                {row.skipped_reason} · {row.count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Spurious rate */}
      {spurious.processed > 0 && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="font-medium text-gray-700">Spurious rate:</span>
          <span className={spurious.rate > 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {(spurious.rate * 100).toFixed(1)}%
          </span>
          <span>({spurious.spurious_count} spurious / {spurious.processed} processed)</span>
        </div>
      )}
    </div>
  )
}

function Tile({ label, value, color }) {
  const colors = {
    gray:  'bg-gray-50  border-gray-200  text-gray-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    blue:  'bg-blue-50  border-blue-200  text-blue-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 ${colors[color]}`}>
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-xs mt-0.5 opacity-70">{label}</p>
    </div>
  )
}
