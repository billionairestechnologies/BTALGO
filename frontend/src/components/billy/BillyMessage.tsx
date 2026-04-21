import { Bot, User, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { BillyMessage as BillyMessageType } from '@/stores/billyStore'

interface Props {
  message: BillyMessageType
}

export function BillyMessage({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-2 mb-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white',
          isUser ? 'bg-primary' : 'bg-amber-500'
        )}
      >
        {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>

      {/* Bubble */}
      <div className={cn('max-w-[85%] space-y-1', isUser ? 'items-end' : 'items-start')}>
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {message.toolCalls.map((tool, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
              >
                <Wrench className="w-2.5 h-2.5" />
                {tool.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div
          className={cn(
            'px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm'
          )}
        >
          {message.content}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current opacity-70 animate-pulse rounded-sm" />
          )}
        </div>

        {/* Timestamp */}
        <p className={cn('text-[10px] text-muted-foreground px-1', isUser ? 'text-right' : '')}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
