import { MessageCircle, X } from 'lucide-react'
import { useBillyStore } from '@/stores/billyStore'

export function BillyButton() {
  const { isOpen, toggle } = useBillyStore()

  return (
    <button
      onClick={toggle}
      className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-amber-500 hover:bg-amber-600 text-white shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center group"
      title={isOpen ? 'Close Billy' : 'Open Billy - AI Trading Assistant'}
    >
      {isOpen ? (
        <X className="w-6 h-6" />
      ) : (
        <>
          <MessageCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-background border-2 border-amber-500 flex items-center justify-center text-[9px] font-bold text-amber-500">
            B
          </span>
        </>
      )}
    </button>
  )
}
