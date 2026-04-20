import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface BillyMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: string[]
  timestamp: string
  isStreaming?: boolean
}

interface BillyStore {
  isOpen: boolean
  messages: BillyMessage[]
  isStreaming: boolean
  toggle: () => void
  open: () => void
  close: () => void
  addMessage: (msg: Omit<BillyMessage, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<BillyMessage>) => void
  clearMessages: () => void
}

export const useBillyStore = create<BillyStore>()(
  persist(
    (set) => ({
      isOpen: false,
      messages: [],
      isStreaming: false,

      toggle: () => set((s) => ({ isOpen: !s.isOpen })),
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),

      addMessage: (msg) => {
        const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`
        const message: BillyMessage = {
          ...msg,
          id,
          timestamp: new Date().toISOString(),
        }
        set((s) => ({ messages: [...s.messages, message] }))
        return id
      },

      updateMessage: (id, updates) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
        })),

      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: 'billy-chat',
      partialize: (s) => ({ messages: s.messages.slice(-30) }), // persist last 30 messages
    }
  )
)
