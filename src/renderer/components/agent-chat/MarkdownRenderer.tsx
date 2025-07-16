import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

interface CodeProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
  [key: string]: any;
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`prose dark:prose-invert max-w-none text-sm leading-snug ${className}`}>
      <ReactMarkdown
        rehypePlugins={[rehypeHighlight]}
        // Highlighting and text for code elements
        components={{
            code({ node, inline, className, children, ...props }: CodeProps) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                <code className={className} {...props}>
                    {children}
                </code>
                ) : (
                <code 
                    className="bg-gray-100/30 text-gray-900 dark:bg-gray-800/30 dark:text-gray-100 rounded px-1 py-0.5 text-sm" 
                    {...props}
                >
                    {children}
                </code>
                );
            }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}