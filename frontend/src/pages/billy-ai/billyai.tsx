import { useEffect, useRef, useState } from 'react'
import {
  ArrowUp,
  Bot,
  Check,
  ChevronDown,
  Copy,
  Loader2,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Square,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { useBillyAiStore } from '@/stores/billyAiStore'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { BillyMarkdown } from './BillyMarkdown'

// ── Greeting Component ───────────────────────────────────────────────────────

function ChatGreeting() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="flex flex-col items-center gap-4 max-w-lg text-center">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10">
          <Bot className="w-8 h-8 text-primary" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Billy AI</h1>
        <p className="text-muted-foreground leading-relaxed">
          BT Algo's trading assistant. Analyze your live portfolio, build strategies, debug
          webhooks, or explore options flows — all in one place.
        </p>
        <div className="flex flex-wrap gap-2 mt-2 justify-center">
          {[
            'Analyze my current positions',
            'Explain iron condor strategy',
            'Help me write a TradingView webhook',
            'What is my available margin?',
          ].map((suggestion) => (
            <SuggestionChip key={suggestion} text={suggestion} />
          ))}
        </div>
      </div>
    </div>
  )
}

function SuggestionChip({ text }: { text: string }) {
  const sendMessage = useBillyAiStore((s) => s.sendMessage)
  return (
    <button
      type="button"
      onClick={() => sendMessage(text)}
      className="px-3 py-1.5 text-xs rounded-full border border-border bg-background hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
    >
      {text}
    </button>
  )
}

// ── Sidebar ──────────────────────────────────────────────────────────────────

function ConversationSidebar() {
  const conversations = useBillyAiStore((s) => s.conversations)
  const currentConversationId = useBillyAiStore((s) => s.currentConversationId)
  const selectConversation = useBillyAiStore((s) => s.selectConversation)
  const deleteConversation = useBillyAiStore((s) => s.deleteConversation)
  const newChat = useBillyAiStore((s) => s.newChat)
  const sidebarOpen = useBillyAiStore((s) => s.sidebarOpen)
  const setSidebarOpen = useBillyAiStore((s) => s.setSidebarOpen)

  if (!sidebarOpen) return null

  return (
    <div className="w-72 border-r border-border bg-muted/30 flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <span className="font-semibold text-sm">Billy AI</span>
        </div>
        <div className="flex items-center gap-1">
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={newChat}>
                  <MessageSquarePlus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">New Chat</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setSidebarOpen(false)}
                >
                  <PanelLeftClose className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Close Sidebar</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Conversation List */}
      <ScrollArea className="flex-1">
        <div className="p-2 flex flex-col gap-0.5">
          {conversations.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-8">No conversations yet</p>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors ${
                conv.id === currentConversationId
                  ? 'bg-primary/10 text-primary'
                  : 'hover:bg-muted text-foreground'
              }`}
            >
              <button
                type="button"
                className="flex-1 text-left truncate"
                onClick={() => selectConversation(conv.id)}
              >
                {conv.title}
              </button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                onClick={(e) => {
                  e.stopPropagation()
                  deleteConversation(conv.id)
                }}
              >
                <Trash2 className="h-3 w-3 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

// ── Message Component ────────────────────────────────────────────────────────

function ChatMessage({ message }: { message: { role: string; content: string } }) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`w-full mx-auto max-w-3xl px-6 group/message ${isUser ? 'flex justify-end' : ''}`}>
      <div
        className={`${
          isUser
            ? 'ml-auto max-w-[80%] rounded-3xl bg-muted/60 backdrop-blur-sm px-5 py-3'
            : 'w-full'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </p>
        ) : (
          <>
            <div className="text-sm leading-7">
              <BillyMarkdown content={message.content} />
            </div>
            {/* Copy button for assistant messages */}
            <div className="flex items-center gap-1 mt-2 opacity-0 group-hover/message:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleCopy}
              >
                {copied ? (
                  <><Check className="h-3 w-3 mr-1" /> Copied</>
                ) : (
                  <><Copy className="h-3 w-3 mr-1" /> Copy</>
                )}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Streaming Indicator ──────────────────────────────────────────────────────

function StreamingMessage({ content }: { content: string }) {
  const toolStatus = useBillyAiStore((s) => s.toolStatus)

  if (!content) {
    return (
      <div className="w-full mx-auto max-w-3xl px-6">
        <div className="flex items-center gap-2 py-2">
          <div className="flex gap-1">
            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
            <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
          </div>
          <span className="text-xs text-muted-foreground">
            {toolStatus || 'Billy is thinking...'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full mx-auto max-w-3xl px-6">
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <BillyMarkdown content={content} />
      </div>
    </div>
  )
}

// ── Error Display ────────────────────────────────────────────────────────────

function ErrorDisplay({ message }: { message: string }) {
  const clearError = useBillyAiStore((s) => s.clearError)

  return (
    <div className="w-full mx-auto max-w-3xl px-6 animate-in fade-in mt-4">
      <div className="flex items-start gap-3 px-2 opacity-80">
        <div className="p-1.5 bg-destructive/10 rounded-lg shrink-0">
          <TriangleAlert className="h-4 w-4 text-destructive" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm mb-1">Error</p>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap break-words">
            {message}
          </p>
        </div>
        <Button variant="ghost" size="sm" className="shrink-0 text-xs" onClick={clearError}>
          Dismiss
        </Button>
      </div>
    </div>
  )
}

// ── Provider Selector ────────────────────────────────────────────────────────

function ProviderModelSelector() {
  const providers = useBillyAiStore((s) => s.providers)
  const selectedProvider = useBillyAiStore((s) => s.selectedProvider)
  const selectedModel = useBillyAiStore((s) => s.selectedModel)
  const setSelectedProvider = useBillyAiStore((s) => s.setSelectedProvider)
  const setSelectedModel = useBillyAiStore((s) => s.setSelectedModel)

  const currentProvider = providers.find((p) => p.id === selectedProvider)
  const currentModel = currentProvider?.models.find((m) => m.id === selectedModel)

  if (providers.length === 0) {
    return (
      <div className="text-xs text-muted-foreground text-center py-2">
        No AI providers configured. Add API keys to .env
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="text-xs">
            {currentProvider?.name || 'Provider'}
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-48">
          {providers.map((p) => (
            <DropdownMenuItem
              key={p.id}
              onClick={() => setSelectedProvider(p.id)}
              className={p.id === selectedProvider ? 'bg-accent' : ''}
            >
              <span className="flex items-center gap-2">
                {p.available ? (
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-gray-400" />
                )}
                {p.name}
              </span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="text-xs">
            {currentModel?.name || 'Model'}
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          {currentProvider?.models.map((m) => (
            <DropdownMenuItem
              key={m.id}
              onClick={() => setSelectedModel(m.id)}
              className={m.id === selectedModel ? 'bg-accent' : ''}
            >
              {m.name}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

// ── Input Area ───────────────────────────────────────────────────────────────

function ChatInputArea() {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const sendMessage = useBillyAiStore((s) => s.sendMessage)
  const isStreaming = useBillyAiStore((s) => s.isStreaming)
  const stopStreaming = useBillyAiStore((s) => s.stopStreaming)

  const handleSend = () => {
    const message = inputRef.current?.value.trim()
    if (!message) return
    sendMessage(message)
    if (inputRef.current) {
      inputRef.current.value = ''
      inputRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  return (
    <div className="border-t border-border bg-background p-4">
      <div className="mx-auto max-w-3xl space-y-3">
        <ProviderModelSelector />
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            placeholder="Ask Billy AI anything..."
            className="flex-1 resize-none border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            rows={1}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button
              size="icon"
              variant="destructive"
              onClick={stopStreaming}
              className="shrink-0"
            >
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSend}
              className="shrink-0"
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main Chat Page ──────────────────────────────────────────────────────────

export default function BillyAI() {
  const sidebarOpen = useBillyAiStore((s) => s.sidebarOpen)
  const setSidebarOpen = useBillyAiStore((s) => s.setSidebarOpen)
  const messages = useBillyAiStore((s) => s.messages)
  const streamingContent = useBillyAiStore((s) => s.streamingContent)
  const error = useBillyAiStore((s) => s.error)
  const isLoading = useBillyAiStore((s) => s.isLoading)

  const loadProviders = useBillyAiStore((s) => s.loadProviders)
  const loadConversations = useBillyAiStore((s) => s.loadConversations)

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadProviders()
    loadConversations()
  }, [loadProviders, loadConversations])

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent])

  const hasMessages = messages.length > 0 || streamingContent

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <ConversationSidebar />

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            )}
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              <h1 className="text-lg font-semibold">Billy AI</h1>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <ScrollArea className="flex-1 overflow-hidden">
          <div className="flex flex-col h-full">
            {!hasMessages && !isLoading && <ChatGreeting />}
            {isLoading && (
              <div className="flex items-center justify-center flex-1">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            )}
            {hasMessages && (
              <div className="flex flex-col gap-6 py-6">
                {messages.map((msg, idx) => (
                  <ChatMessage key={idx} message={msg} />
                ))}
                {streamingContent && <StreamingMessage content={streamingContent} />}
                {error && <ErrorDisplay message={error} />}
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <ChatInputArea />
      </div>
    </div>
  )
}
