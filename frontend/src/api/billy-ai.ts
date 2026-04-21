import { webClient } from './client'

export interface Provider {
  id: string
  name: string
  available: boolean
  models: { id: string; name: string }[]
}

export interface Conversation {
  id: number
  title: string
  provider: string
  model: string
  created_at: string | null
  updated_at: string | null
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  provider: string | null
  model: string | null
  created_at: string | null
}

export const billyAiApi = {
  getProviders: async (): Promise<Provider[]> => {
    const res = await webClient.get('/billy-ai/providers')
    return res.data.data
  },

  getConversations: async (): Promise<Conversation[]> => {
    const res = await webClient.get('/billy-ai/conversations')
    return res.data.data
  },

  createConversation: async (
    provider: string,
    model: string
  ): Promise<{ id: number }> => {
    const res = await webClient.post('/billy-ai/conversations', {
      provider,
      model,
    })
    return res.data.data
  },

  getMessages: async (conversationId: number): Promise<Message[]> => {
    const res = await webClient.get(
      `/billy-ai/conversations/${conversationId}`
    )
    return res.data.data
  },

  deleteConversation: async (conversationId: number): Promise<void> => {
    await webClient.delete(`/billy-ai/conversations/${conversationId}`)
  },

  updateTitle: async (
    conversationId: number,
    title: string
  ): Promise<void> => {
    await webClient.put(`/billy-ai/conversations/${conversationId}/title`, {
      title,
    })
  },

  /**
   * Stream chat via SSE. Returns an AbortController to cancel.
   */
  streamChat: (
    params: {
      message: string
      conversation_id?: number | null
      provider: string
      model: string
    },
    onChunk: (content: string) => void,
    onError: (error: string) => void,
    onDone: (conversationId: number | null) => void,
    onToolStatus?: (status: string) => void
  ): AbortController => {
    const controller = new AbortController()

    // We need to use fetch directly for SSE streaming (not axios)
    const url = `${import.meta.env.VITE_API_URL || ''}/billy-ai/chat`

    // Get CSRF token first, then make the streaming request
    fetch('/auth/csrf-token', { credentials: 'include' })
      .then((res) => res.json())
      .then((csrfData) => {
        return fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfData.csrf_token || '',
          },
          body: JSON.stringify(params),
          credentials: 'include',
          signal: controller.signal,
        })
      })
      .then(async (response) => {
        if (!response.ok) {
          onError(`Server error: ${response.status}`)
          onDone(null)
          return
        }

        const convId = response.headers.get('X-Conversation-Id')
        const reader = response.body?.getReader()
        if (!reader) {
          onError('No response stream')
          onDone(convId ? Number.parseInt(convId) : null)
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6).trim()
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)
              if (parsed.error) {
                onError(parsed.error)
              } else if (parsed.tool_status) {
                onToolStatus?.(parsed.tool_status)
              } else if (parsed.content) {
                onChunk(parsed.content)
              }
            } catch {
              // skip malformed chunks
            }
          }
        }

        onDone(convId ? Number.parseInt(convId) : null)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err.message || 'Network error')
          onDone(null)
        }
      })

    return controller
  },
}
