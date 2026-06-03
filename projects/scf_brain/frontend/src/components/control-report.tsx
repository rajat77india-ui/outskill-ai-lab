import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'

interface ControlReportProps {
  content: string
  isStreaming?: boolean
  className?: string
}

export function ControlReport({ content, isStreaming, className }: ControlReportProps) {
  if (!content && !isStreaming) return null

  return (
    <div className={cn('rounded-lg border border-border bg-card p-6', className)}>
      {!content && isStreaming && (
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-primary/60"
                style={{
                  animation: 'pulse-dot 1.4s ease-in-out infinite',
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </div>
          <span className="text-sm">Agents are analyzing compliance...</span>
        </div>
      )}

      {content && (
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              h1: ({ children }) => (
                <h1 className="text-xl font-bold text-foreground border-b border-border pb-2 mb-4">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-base font-semibold text-foreground mt-6 mb-3">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-foreground/90 mt-4 mb-2">{children}</h3>
              ),
              p: ({ children }) => (
                <p className="text-sm text-foreground/80 leading-relaxed mb-3">{children}</p>
              ),
              ul: ({ children }) => (
                <ul className="space-y-1 mb-3 pl-4">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="space-y-1 mb-3 pl-4 list-decimal">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="text-sm text-foreground/80 flex gap-2">
                  <span className="text-primary mt-1 shrink-0">•</span>
                  <span>{children}</span>
                </li>
              ),
              code: ({ children, className }) => {
                const isBlock = className?.includes('language-')
                return isBlock ? (
                  <code className="block bg-muted rounded p-3 text-xs font-mono text-foreground/80 overflow-x-auto mb-3">
                    {children}
                  </code>
                ) : (
                  <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono text-primary">
                    {children}
                  </code>
                )
              },
              table: ({ children }) => (
                <div className="overflow-x-auto mb-4">
                  <table className="w-full text-xs border-collapse border border-border rounded">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-muted/50">{children}</thead>
              ),
              th: ({ children }) => (
                <th className="border border-border px-3 py-2 text-left font-medium text-muted-foreground">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-border px-3 py-2 text-foreground/80">{children}</td>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">{children}</strong>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-primary/40 pl-4 text-muted-foreground italic mb-3">
                  {children}
                </blockquote>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary animate-blink" />
          )}
        </div>
      )}
    </div>
  )
}
