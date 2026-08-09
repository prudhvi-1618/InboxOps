import { useState, useRef } from 'react'
import { API_URL } from '../config.js'

export default function EmailInputPanel({ onEmailsParsed }) {
  const [jsonText, setJsonText] = useState('')
  const [parseError, setParseError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const fileInputRef = useRef(null)

  // ── Parse JSON from textarea ────────────────────────────────────────────────
  function handleParse() {
    setParseError('')
    const trimmed = jsonText.trim()
    if (!trimmed) {
      setParseError('Paste JSON or upload a file first.')
      return
    }
    try {
      const parsed = JSON.parse(trimmed)
      // Accept either a raw array or { emails: [...] }
      const emails = Array.isArray(parsed)
        ? parsed
        : Array.isArray(parsed?.emails)
          ? parsed.emails
          : null

      if (!emails || emails.length === 0) {
        setParseError('JSON must be an array of email objects (or { emails: [...] }).')
        return
      }
      if (emails.length > 100) {
        setParseError(`Batch limit is 100 emails. You pasted ${emails.length}.`)
        return
      }
      onEmailsParsed(emails)
    } catch (e) {
      setParseError(`Invalid JSON: ${e.message}`)
    }
  }

  // ── File upload ─────────────────────────────────────────────────────────────
  function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.json')) {
      setParseError('Please upload a .json file.')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      setJsonText(ev.target.result)
      setParseError('')
    }
    reader.onerror = () => setParseError('Failed to read file.')
    reader.readAsText(file)
  }

  // ── Generate 250 sample emails ──────────────────────────────────────────────
  async function handleGenerate() {
    setGenerating(true)
    setGenerateError('')
    setParseError('')
    try {
      const resp = await fetch(`${API_URL}/api/generate-samples`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 100 }), // max batch is 100
      })
      if (!resp.ok) throw new Error(`Backend returned ${resp.status}`)
      const data = await resp.json()
      const emails = Array.isArray(data) ? data : data?.emails
      if (!emails || emails.length === 0) throw new Error('No emails returned')
      const json = JSON.stringify(emails, null, 2)
      setJsonText(json)
      onEmailsParsed(emails)
    } catch (e) {
      setGenerateError(`Generate failed: ${e.message}`)
    } finally {
      setGenerating(false)
    }
  }

  // ── Clear ───────────────────────────────────────────────────────────────────
  function handleClear() {
    setJsonText('')
    setParseError('')
    setGenerateError('')
    onEmailsParsed([])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          1 — Paste or upload emails
        </h2>
        <div className="flex items-center gap-2">
          {/* File upload */}
          <label className="cursor-pointer px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">
            Upload .json
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          {/* Generate button — Task 2 */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <span className="flex items-center gap-1.5">
                <Spinner size={14} />
                Generating…
              </span>
            ) : (
              '✨ Generate 100 sample emails'
            )}
          </button>

          {jsonText && (
            <button
              onClick={handleClear}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-600 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {generateError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {generateError}
        </p>
      )}

      {/* JSON textarea */}
      <textarea
        value={jsonText}
        onChange={(e) => { setJsonText(e.target.value); setParseError('') }}
        placeholder={`Paste a JSON array of emails here, e.g.\n[\n  {\n    "email_id": "em_001",\n    "thread_id": "th_001",\n    "subject": "RFP - Enterprise DMS",\n    ...\n  }\n]`}
        className="w-full h-48 px-3 py-2.5 rounded-lg border border-gray-200 text-sm font-mono text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-y"
        spellCheck={false}
      />

      {parseError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {parseError}
        </p>
      )}

      <button
        onClick={handleParse}
        disabled={!jsonText.trim()}
        className="w-full py-2.5 rounded-lg text-sm font-semibold bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Preview emails as table →
      </button>
    </div>
  )
}

function Spinner({ size = 16 }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      className="animate-spin"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
    </svg>
  )
}
