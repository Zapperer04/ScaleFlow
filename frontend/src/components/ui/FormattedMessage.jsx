import React from 'react';

/**
 * FormattedMessage Component
 * Converts markdown text, bullet points, headers, bold styling (**text**),
 * and raw citation tags ([chunk_xyz]) into rich, interactive React elements.
 */
export const FormattedMessage = ({ content, onCitationClick }) => {
  if (!content) return null;

  // Normalize inline bullet lists (e.g., "includes: * **Item 1** * **Item 2**") into line breaks
  let normalized = content.replace(/([^\n])\s+(\*|-|•)\s+/g, '$1\n* ');

  // Split into lines
  const lines = normalized.split('\n');
  const elements = [];
  let currentList = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul
          key={`list-${elements.length}`}
          style={{
            margin: '8px 0',
            paddingLeft: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            listStyleType: 'disc',
          }}
        >
          {currentList.map((item, i) => (
            <li key={i} style={{ lineHeight: '1.5', color: '#e2e8f0' }}>
              {parseInlineMarkdown(item, onCitationClick)}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    // Check for bullet list item (* item, - item, • item, 1. item)
    const bulletMatch = trimmed.match(/^([*\-•]|\d+\.)\s+(.*)$/);
    if (bulletMatch) {
      currentList.push(bulletMatch[2]);
    } else {
      flushList();
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h4
            key={lineIdx}
            style={{
              margin: '10px 0 4px 0',
              fontSize: '0.9rem',
              fontWeight: 700,
              color: 'var(--color-accent)',
            }}
          >
            {parseInlineMarkdown(trimmed.slice(4), onCitationClick)}
          </h4>
        );
      } else if (trimmed.startsWith('## ')) {
        elements.push(
          <h3
            key={lineIdx}
            style={{
              margin: '12px 0 6px 0',
              fontSize: '0.95rem',
              fontWeight: 700,
              color: '#ffffff',
            }}
          >
            {parseInlineMarkdown(trimmed.slice(3), onCitationClick)}
          </h3>
        );
      } else {
        elements.push(
          <p
            key={lineIdx}
            style={{
              margin: '4px 0',
              lineHeight: '1.6',
              color: '#f1f5f9',
            }}
          >
            {parseInlineMarkdown(trimmed, onCitationClick)}
          </p>
        );
      }
    }
  });

  flushList();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      {elements}
    </div>
  );
};

/**
 * Parses inline bold **text**, inline `code`, and citation tokens ([chunk_xyz] or [hex_id]).
 */
const parseInlineMarkdown = (str, onCitationClick) => {
  if (!str) return null;

  // Split by bold (**...**), inline code (`...`), or citation tags ([chunk_...] or [hex_id])
  const parts = str.split(/(\*\*.*?\*\*|`.*?`|\[chunk_[a-zA-Z0-9_-]+\]|\[[a-fA-F0-9]{8,64}\])/g);

  return parts.map((part, index) => {
    if (!part) return null;

    // Bold text **example**
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={index} style={{ color: '#ffffff', fontWeight: 600 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Inline code `example`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={index}
          style={{
            background: 'rgba(255,255,255,0.08)',
            border: '1px solid rgba(255,255,255,0.1)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.82em',
            fontFamily: 'monospace',
            color: '#38bdf8',
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Citation pill [chunk_abc123...] or [d766bc7f...]
    const isChunkCitation = part.startsWith('[chunk_') && part.endsWith(']');
    const isHexCitation = /^\[[a-fA-F0-9]{8,64}\]$/.test(part);

    if (isChunkCitation || isHexCitation) {
      const rawId = part.slice(1, -1);
      const cleanId = rawId.replace('chunk_', '');
      
      return (
        <span
          key={index}
          onClick={() => onCitationClick && onCitationClick(rawId)}
          title={`Jump to source context (ID: ${cleanId.slice(0, 8)})`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            background: 'rgba(59, 130, 246, 0.15)',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            color: '#60a5fa',
            borderRadius: '4px',
            padding: '1px 7px',
            fontSize: '0.72rem',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontWeight: 600,
            cursor: 'pointer',
            marginLeft: '4px',
            marginRight: '2px',
            userSelect: 'none',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)';
            e.currentTarget.style.borderColor = '#60a5fa';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)';
            e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.35)';
          }}
        >
          📌 Source
        </span>
      );
    }

    return part;
  });
};

export default FormattedMessage;
