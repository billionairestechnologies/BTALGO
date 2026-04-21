import { BarChart2, BookOpen, Loader2, SendHorizonal, Settings, Trash2, X, Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { showToast } from '@/utils/toast'
import { useBillyStore } from '@/stores/billyStore'
import { BillyMessage } from './BillyMessage'

const QUICK_ACTIONS = [
  { label: 'My Positions', icon: BarChart2, prompt: 'What are my current open positions and their P&L?' },
  { label: 'Trade Journal', icon: BookOpen, prompt: 'Analyze my recent trades and give me insights on my performance.' },
  { label: 'Market Research', icon: BarChart2, prompt: 'Research the current market conditions for NIFTY.' },
  { label: 'Create Strategy', icon: Zap, prompt: 'Help me create a new trading strategy.' },
]

export function BillyPanel() {
  const navigate = useNavigate()
  const { isOpen, close, messages, addMessage, updateMessage, clearMessages } = useBillyStore()
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }, [isOpen])

  const sendMessage = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return

    setInput('')
    setIsStreaming(true)

    // Add user message
    addMessage({ role: 'user', content: trimmed })

    // Add placeholder for Billy's response
    const billyMsgId = addMessage({ role: 'assistant', content: '', isStreaming: true })

    try {
      const response = await fetch('/api/billy/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: trimmed,
          context: { page: window.location.pathname },
        }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.message || 'Failed to connect to Billy')
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let toolCalls: string[] = []
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const event = line.slice(7).trim()
            const dataLine = lines[lines.indexOf(line) + 1]
            if (!dataLine?.startsWith('data: ')) continue

            try {
              const data = JSON.parse(dataLine.slice(6))
              if (event === 'text') {
                fullText += data.chunk
                updateMessage(billyMsgId, { content: fullText, isStreaming: true, toolCalls })
              } else if (event === 'tool_start') {
                if (!toolCalls.includes(data.name)) {
                  toolCalls = [...toolCalls, data.name]
                  updateMessage(billyMsgId, { toolCalls, isStreaming: true })
                }
              } else if (event === 'done') {
                fullText = data.message || fullText
                updateMessage(billyMsgId, { content: fullText, isStreaming: false, toolCalls })
              } else if (event === 'error') {
                throw new Error(data.message)
              }
            } catch {
              // skip parse errors
            }
          }
        }
      }

      if (!fullText) {
        updateMessage(billyMsgId, { content: "I'm here! What can I help you with?", isStreaming: false })
      }
    } catch (err: any) {
      updateMessage(billyMsgId, {
        content: `Sorry, something went wrong: ${err.message}. Check your Billy settings.`,
        isStreaming: false,
      })
      showToast.error(`Billy error: ${err.message}`)
    } finally {
      setIsStreaming(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed right-0 top-0 h-full w-[400px] z-50 flex flex-col bg-background border-l border-border shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-amber-500/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-white font-bold text-sm">
            B
          </div>
          <div>
            <p className="font-semibold text-sm leading-none">Billy</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">AI Trading Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => navigate('/billy/settings')}
            title="Billy Settings"
          >
            <Settings className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={clearMessages}
            title="Clear conversation"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-3 py-3" ref={scrollRef as any}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-amber-500 flex items-center justify-center text-white text-2xl font-bold mb-4">
              B
            </div>
            <h3 className="font-semibold mb-1">Hi, I'm Billy!</h3>
            <p className="text-xs text-muted-foreground max-w-[260px]">
              Your AI trading assistant. Ask me about markets, your portfolio, or let me create strategies for you.
            </p>
          </div>
        ) : (
          messages.map((msg) => <BillyMessage key={msg.id} message={msg} />)
        )}

        {isStreaming && messages[messages.length - 1]?.isStreaming === false && (
          <div className="flex gap-2 items-center text-muted-foreground text-xs py-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            Billy is thinking...
          </div>
        )}
      </ScrollArea>

      {/* Quick actions */}
      {messages.length === 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => sendMessage(action.prompt)}
              disabled={isStreaming}
              className="flex items-center gap-1 text-[11px] px-2.5 py-1.5 rounded-full border border-border hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-50"
            >
              <action.icon className="w-3 h-3" />
              {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3 pb-3 pt-2 border-t border-border">
        <div className="flex gap-2 items-end">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Billy anything..."
            className="min-h-[40px] max-h-[120px] resize-none text-sm"
            disabled={isStreaming}
            rows={1}
          />
          <Button
            size="icon"
            className="h-10 w-10 flex-shrink-0 bg-amber-500 hover:bg-amber-600"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isStreaming}
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <SendHorizonal className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
