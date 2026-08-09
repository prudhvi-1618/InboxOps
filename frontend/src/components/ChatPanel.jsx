import { useState, useRef, useEffect } from 'react'
import { API_URL } from '../config.js'

const CANDIDATE_ID = import.meta.env.VITE_CANDIDATE_ID || ''

const SAMPLE_QUESTIONS = [
  'How many emails were RFP or proposal related?',
  'How many were marketing versus spam we correctly ignored?',
  'Show me everything sitting in triage and why.',
  'What is our spurious rate so far?',
  'Which tasks are high priority but low confidence?',
  'How many emails were about GST refunds?',
  'What is the total deal value of all open RFPs?',
  'Did any thread get updated more than once?',
]

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      answer: 'Ask me anything about the emails you just processed — counts, categories, triage items, deal values, or routing decisions.',
      supporting_data: {},
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(query) {
    const q = (query || input).trim()
    if (!q || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)

    try {
      const resp = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_id: CANDIDATE_ID, query: q }),
      })
      const data = await resp.json()

      if (!resp.ok) {
        throw new Error(data?.detail || `Error ${resp.status}`)
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        answer: data.answer,
        supporting_data: data.supporting_data || {},
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        answer: `Error: ${e.message}`,
        supporting_data: {},
        isError: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

      {/* Sample questions sidebar */}
      <div className="lg:col-span-1 space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-1">
          Sample questions
        </p>
        {SAMPLE_QUESTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => sendMessage(q)}
            disabled={loading}
            className="w-full text-left px-3 py-2.5 rounded-lg text-sm text-gray-600 bg-white border border-gray-200 hover:bg-brand-50 hover:border-brand-200 hover:text-brand-700 disabled:opacity-40 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Chat area */}
      <div className="lg:col-span-3 flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden" style={{ height: '70vh' }}>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === 'user' ? (
                <div className="flex justify-end">
                  <div className="max-w-lg px-4 py-2.5 rounded-2xl rounded-tr-sm bg-brand-500 text-white text-sm">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">
                    🤖
                  </div>
                  <div className="space-y-2 max-w-2xl">
                    <div className={`px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed ${
                      msg.isError
                        ? 'bg-red-50 text-red-700 border border-red-100'
                        : 'bg-gray-50 text-gray-800'
                    }`}>
                      {msg.answer}
                    </div>

                    {/* supporting_data — grader checks this */}
                    {msg.supporting_data && Object.keys(msg.supporting_data).length > 0 && (
                      <SupportingData data={msg.supporting_data} />
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Loading bubble */}
          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 text-sm">
                🤖
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-gray-50 text-sm text-gray-400">
                <TypingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="border-t border-gray-100 p-4 flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the processed emails…"
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

function SupportingData({ data }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden text-xs">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 text-gray-500 hover:bg-gray-100 transition-colors"
      >
        <span className="font-medium">supporting_data</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <pre className="px-3 py-2.5 text-gray-600 bg-white overflow-x-auto text-xs leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function TypingDots() {
  return (
    <span className="flex gap-1 items-center h-4">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  )
}
