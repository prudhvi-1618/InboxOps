import { useState } from 'react'
import EmailInputPanel from './components/EmailInputPanel.jsx'
import EmailTable from './components/EmailTable.jsx'
import IngestPanel from './components/IngestPanel.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import StatsBar from './components/StatsBar.jsx'

export default function App() {
  const [emails, setEmails] = useState([])         // parsed emails from input
  const [ingestResult, setIngestResult] = useState(null)
  const [activeTab, setActiveTab] = useState('ingest') // 'ingest' | 'chat'

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Inbox Router</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Sales inbox → task router
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('ingest')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'ingest'
                  ? 'bg-brand-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Ingest
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-brand-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Ask questions
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {activeTab === 'ingest' && (
          <>
            {/* Step 1 + 2: JSON input + generate button */}
            <EmailInputPanel
              onEmailsParsed={setEmails}
            />

            {/* Step 3: Raw email table — renders BEFORE routing */}
            {emails.length > 0 && (
              <>
                <EmailTable emails={emails} />

                {/* Route batch button + result */}
                <IngestPanel
                  emails={emails}
                  onResult={setIngestResult}
                />
              </>
            )}

            {/* Stats bar — live from backend */}
            <StatsBar />
          </>
        )}

        {activeTab === 'chat' && (
          <ChatPanel />
        )}
      </main>
    </div>
  )
}
