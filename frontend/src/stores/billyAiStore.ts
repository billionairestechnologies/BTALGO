import { create } from 'zustand'
import type { Conversation, Message, Provider } from '@/api/billy-ai'
import { billyAiApi } from '@/api/billy-ai'

interface BillyAiState {
  // Data
  providers: Provider[]
  conversations: Conversation[]
  currentConversationId: number | null
  messages: Message[]
  streamingContent: string
  toolStatus: string | null
  isStreaming: boolean
  isLoading: boolean
  error: string | null

  // Selected provider/model
  selectedProvider: string
  selectedModel: string

  // Sidebar
  sidebarOpen: boolean

  // Actions
  setSidebarOpen: (open: boolean) => void
  setSelectedProvider: (provider: string) => void
  setSelectedModel: (model: string) => void
  loadProviders: () => Promise<void>
  loadConversations: () => Promise<void>
  loadMessages: (conversationId: number) => Promise<void>
  selectConversation: (conversationId: number) => Promise<void>
  newChat: () => void
  deleteConversation: (conversationId: number) => Promise<void>
  sendMessage: (message: string) => void
  stopStreaming: () => void
  clearError: () => void

  // Internal
  _abortController: AbortController | null
}

export const useBillyAiStore = create<BillyAiState>((set, get) => ({
  providers: [],
  conversations: [],
  currentConversationId: null,
  messages: [],
  streamingContent: '',
  toolStatus: null,
  isStreaming: false,
  isLoading: false,
  error: null,
  selectedProvider: 'nexos',
  selectedModel: '',
  sidebarOpen: true,
  _abortController: null,

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setSelectedProvider: (provider) => {
    const state = get()
    const p = state.providers.find((pr) => pr.id === provider)
    const firstModel = p?.models?.[0]?.id || ''
    set({ selectedProvider: provider, selectedModel: firstModel })
  },

  setSelectedModel: (model) => set({ selectedModel: model }),

  loadProviders: async () => {
    try {
      const providers = await billyAiApi.getProviders()
      const firstAvailable = providers.find((p) => p.available)
      set({
        providers,
        selectedProvider: firstAvailable?.id || 'nexos',
        selectedModel: firstAvailable?.models?.[0]?.id || '',
      })
    } catch {
      // Providers will be empty, UI handles it
    }
  },

  loadConversations: async () => {
    try {
      const conversations = await billyAiApi.getConversations()
      set({ conversations })
    } catch {
      // silent fail
    }
  },

  loadMessages: async (conversationId) => {
    set({ isLoading: true })
    try {
      const messages = await billyAiApi.getMessages(conversationId)
      set({ messages, currentConversationId: conversationId, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  selectConversation: async (conversationId) => {
    set({ currentConversationId: conversationId, messages: [], streamingContent: '' })
    await get().loadMessages(conversationId)
  },

  newChat: () => {
    const state = get()
    if (state._abortController) {
      state._abortController.abort()
    }
    set({
      currentConversationId: null,
      messages: [],
      streamingContent: '',
      toolStatus: null,
      isStreaming: false,
      error: null,
      _abortController: null,
    })
  },

  deleteConversation: async (conversationId) => {
    try {
      await billyAiApi.deleteConversation(conversationId)
      const state = get()
      const updated = state.conversations.filter((c) => c.id !== conversationId)
      if (state.currentConversationId === conversationId) {
        set({
          conversations: updated,
          currentConversationId: null,
          messages: [],
          streamingContent: '',
        })
      } else {
        set({ conversations: updated })
      }
    } catch {
      // silent fail
    }
  },

  sendMessage: (message) => {
    const state = get()
    if (state.isStreaming) return

    // Optimistic: add user message to UI
    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: message,
      provider: null,
      model: null,
      created_at: new Date().toISOString(),
    }

    set({
      messages: [...state.messages, userMsg],
      streamingContent: '',
      toolStatus: null,
      isStreaming: true,
      error: null,
    })

    const abortController = billyAiApi.streamChat(
      {
        message,
        conversation_id: state.currentConversationId,
        provider: state.selectedProvider,
        model: state.selectedModel,
      },
      // onChunk
      (content) => {
        set((s) => ({ streamingContent: s.streamingContent + content, toolStatus: null }))
      },
      // onError
      (error) => {
        set({ error, isStreaming: false, toolStatus: null })
      },
      // onDone
      (conversationId) => {
        set((s) => {
          const newMessages: Message[] = []
          if (s.streamingContent) {
            newMessages.push({
              id: Date.now() + 1,
              role: 'assistant',
              content: s.streamingContent,
              provider: state.selectedProvider,
              model: state.selectedModel,
              created_at: new Date().toISOString(),
            })
          }
          return {
            messages: [...s.messages, ...newMessages],
            streamingContent: '',
            isStreaming: false,
            currentConversationId: conversationId || s.currentConversationId,
          }
        })
        if (conversationId) {
          get().loadConversations()
        }
      },
      // onToolStatus
      (status) => {
        set({ toolStatus: status })
      }
    )

    set({ _abortController: abortController })
  },

  stopStreaming: () => {
    const state = get()
    if (state._abortController) {
      state._abortController.abort()
    }
    set({ isStreaming: false, _abortController: null })
  },

  clearError: () => set({ error: null }),
}))
