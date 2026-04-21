import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function BillyMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ node, ...props }) => <h1 className="text-xl font-bold mt-4 mb-2" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-lg font-semibold mt-3 mb-2" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-base font-semibold mt-2 mb-1" {...props} />,
        p: ({ node, ...props }) => <p className="mb-2 text-sm leading-relaxed" {...props} />,
        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2 space-y-1 text-sm" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2 space-y-1 text-sm" {...props} />,
        li: ({ node, ...props }) => <li className="text-sm" {...props} />,
        code: ({ node, className, children, ...props }: any) =>
          !className ? (
            <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
          ) : (
            <code className={`block bg-muted p-3 rounded text-xs font-mono overflow-x-auto mb-2 ${className}`} {...props}>{children}</code>
          ),
        pre: ({ node, ...props }) => <pre className="bg-muted p-3 rounded text-xs font-mono overflow-x-auto mb-2" {...props} />,
        table: ({ node, ...props }) => <table className="border-collapse border border-muted text-sm mb-2" {...props} />,
        thead: ({ node, ...props }) => <thead className="bg-muted" {...props} />,
        th: ({ node, ...props }) => <th className="border border-muted p-2 text-left font-semibold" {...props} />,
        td: ({ node, ...props }) => <td className="border border-muted p-2" {...props} />,
        a: ({ node, ...props }) => <a className="text-primary underline hover:no-underline" {...props} />,
        blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-muted pl-3 italic text-muted-foreground mb-2 text-sm" {...props} />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
