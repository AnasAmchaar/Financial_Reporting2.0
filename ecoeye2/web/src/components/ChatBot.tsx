import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { apiFetch } from '../lib/api'

type Message = {
  role: 'user' | 'ai'
  content: string
}

declare global {
  interface Window {
    __ECOEYE_CONTEXT__?: any
  }
}

export function ChatBot() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: 'Hello! I am your **RAG-enhanced** AI Financial Analyst. I can now answer questions grounded in your actual financial data, CPI/PPI indicators, and economic metrics. Try asking me about specific partners, trends, or inflation impacts!' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [useRag, setUseRag] = useState(true)
  const [isReindexing, setIsReindexing] = useState(false)
  const [provider, setProvider] = useState<string>('googlegenai')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen) scrollToBottom()
  }, [messages, isOpen])

  // Fetch the active provider on mount
  useEffect(() => {
    apiFetch<{ active: string }>('/api/v1/ai/provider')
      .then((res) => setProvider(res.active))
      .catch(() => {})
  }, [])

  const handleSend = async () => {
    if (!input.trim()) return
    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setIsLoading(true)

    try {
      const context = window.__ECOEYE_CONTEXT__ ? JSON.stringify(window.__ECOEYE_CONTEXT__) : "No specific context available on this page."
      
      const payload = {
        message: userMsg,
        context: context,
        use_rag: useRag
      }

      const res = await apiFetch<{ response: string; mode?: string; provider?: string }>('/api/v1/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })

      if (res.provider) setProvider(res.provider)
      setMessages((prev) => [...prev, { role: 'ai', content: res.response }])
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: 'ai', content: `**Error:** ${e.message || 'Failed to communicate with AI.'}` }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 p-4 bg-emerald-600 text-white rounded-full shadow-[0_0_15px_rgba(16,185,129,0.5)] hover:bg-emerald-500 transition-all z-50 ${isOpen ? 'scale-0' : 'scale-100'}`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/>
          <path d="M8.5 14h.01"/><path d="M15.5 14h.01"/><path d="M12 14h.01"/>
        </svg>
      </button>

      {/* Chat Window */}
      <div className={`fixed bottom-6 right-6 w-96 h-[32rem] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50 transition-all origin-bottom-right ${isOpen ? 'scale-100 opacity-100' : 'scale-0 opacity-0 pointer-events-none'}`}>
        
        {/* Header */}
        <div className="bg-slate-800/80 p-3 border-b border-slate-700/80 backdrop-blur-md">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${useRag ? 'bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.8)]' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]'}`} />
              <h3 className="text-slate-200 font-semibold text-sm tracking-wide">EcoEye2 AI Analyst</h3>
              <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-slate-700/60 text-slate-400 border border-slate-600/30">
                via {provider === 'groq' ? 'Groq' : 'Gemini'}
              </span>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-200">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-700/50">
            <button
              onClick={() => setUseRag(r => !r)}
              className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full transition-colors ${useRag ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30' : 'bg-slate-700/50 text-slate-500 border border-slate-600/30'}`}
            >
              RAG {useRag ? 'ON' : 'OFF'}
            </button>
            <button
              onClick={async () => {
                setIsReindexing(true)
                try {
                  await apiFetch('/api/v1/ai/rag/reindex', { method: 'POST' })
                  setMessages(prev => [...prev, { role: 'ai', content: '✅ **RAG index rebuilt successfully.** I now have the latest data from your database.' }])
                } catch (e: any) {
                  setMessages(prev => [...prev, { role: 'ai', content: `⚠️ Re-index failed: ${e.message}` }])
                } finally {
                  setIsReindexing(false)
                }
              }}
              disabled={isReindexing}
              className="text-[10px] text-slate-500 hover:text-violet-400 transition-colors disabled:opacity-40"
            >
              {isReindexing ? '⟳ Indexing…' : '⟳ Re-index Data'}
            </button>
          </div>
        </div>

        {/* Message Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-2 ${m.role === 'user' ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-200 border border-slate-700/50 rounded-bl-none'}`}>
                {m.role === 'ai' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-400 border border-slate-700/50 rounded-2xl rounded-bl-none px-4 py-2 text-sm flex space-x-1 items-center">
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-3 bg-slate-800/80 border-t border-slate-700/80 backdrop-blur-md">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your data..."
              disabled={isLoading}
              className="flex-1 bg-slate-900 border border-slate-700/80 text-slate-200 text-sm rounded-full px-4 py-2 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-2 bg-emerald-600 text-white rounded-full hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
            </button>
          </form>
        </div>
      </div>
    </>
  )
}
