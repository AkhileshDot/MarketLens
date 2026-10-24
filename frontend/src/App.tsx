import { useState, type FormEvent } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [ticker, setTicker] = useState('NSE:INFY')
  const [days, setDays] = useState(90)
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function buildFormData(): FormData {
    const formData = new FormData()
    formData.append('ticker', ticker)
    formData.append('days', String(days))
    if (file) formData.append('file', file)
    return formData
  }

  async function handleAnalyze(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setNote('')

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: buildFormData(),
      })
      if (!response.ok) {
        const body = await response.json()
        throw new Error(body.detail ?? `Request failed: ${response.status}`)
      }
      const data = await response.json()
      setNote(`${data.note}\n\n${data.disclaimer}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  async function handleChat(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setNote('')

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        body: buildFormData(),
      })
      if (!response.ok || !response.body) {
        const body = await response.json()
        throw new Error(body.detail ?? `Request failed: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          const text = frame.replace(/^data: /, '')
          if (text === '[DONE]') continue
          setNote((prev) => prev + text)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app">
      <h1>MarketLens</h1>
      <p className="disclaimer-banner">
        Personal research demo. Not investment advice. Not SEBI registered.
      </p>

      <form className="form">
        <label>
          Ticker
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="NSE:INFY"
          />
        </label>

        <label>
          Days
          <input
            type="number"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            min={1}
            max={365}
          />
        </label>

        <label>
          Chart or results PDF (optional)
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <div className="button-row">
          <button type="submit" onClick={handleAnalyze} disabled={loading}>
            Analyze
          </button>
          <button type="submit" onClick={handleChat} disabled={loading}>
            Chat (stream)
          </button>
        </div>
      </form>

      {loading && <p className="status">Working…</p>}
      {error && <p className="error">{error}</p>}
      {note && <pre className="note">{note}</pre>}
    </main>
  )
}

export default App
