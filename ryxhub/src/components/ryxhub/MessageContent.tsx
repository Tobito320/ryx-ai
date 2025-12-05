import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import 'highlight.js/styles/github-dark.css';

interface MessageContentProps {
  content: string;
  role: 'user' | 'assistant';
}

export function MessageContent({ content, role }: MessageContentProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopyCode = async (code: string, id: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // For user messages, just show plain text
  if (role === 'user') {
    return <div className="whitespace-pre-wrap">{content}</div>;
  }

  // For assistant messages, render markdown with syntax highlighting
  return (
    <ReactMarkdown
      className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-muted/50 prose-pre:border prose-pre:border-border"
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight, rehypeRaw]}
      components={{
        pre: ({ node, children, ...props }) => {
          // Extract code content
          const codeElement = children?.[0] as any;
          const codeContent = codeElement?.props?.children?.[0] || '';
          const codeId = `code-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          
          return (
            <div className="relative group">
              <pre {...props} className="!pr-12">
                {children}
              </pre>
              <Button
                size="icon"
                variant="ghost"
                className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => handleCopyCode(codeContent, codeId)}
              >
                {copiedCode === codeId ? (
                  <Check className="w-3 h-3 text-green-500" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
              </Button>
            </div>
          );
        },
        code: ({ node, inline, className, children, ...props }) => {
          if (inline) {
            return (
              <code className={cn('px-1 py-0.5 rounded bg-muted text-xs', className)} {...props}>
                {children}
              </code>
            );
          }
          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        a: ({ node, children, ...props }) => (
          <a
            {...props}
            className="text-primary underline hover:text-primary/80"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
