import React, { useState } from 'react';
import { Database, FileJson, ChevronDown, ChevronRight, Download, Terminal } from 'lucide-react';
import Button from '../components/ui/Button';

export const ArtifactsExplorer = () => {
  const [selectedFile, setSelectedFile] = useState('graph.json');
  const [explorerOpen, setExplorerOpen] = useState(true);

  const mockPayloads = {
    'graph.json': `{
  "nodes": [
    {"id": "node_0", "type": "header", "text": "1. Ingestion Protocol"},
    {"id": "node_1", "type": "paragraph", "text": "ScaleFlow implements parallel workers leasing queues."}
  ],
  "edges": [
    {"source": "node_0", "target": "node_1", "type": "hierarchy"}
  ],
  "metadata": {
    "total_nodes": 2,
    "total_edges": 1,
    "version": "1.0.0"
  }
}`,
    'chunks.json': `[
  {
    "chunk_id": "chunk_p1_n0",
    "text": "ScaleFlow: Distributed AI Document Orchestration Runtime (MR-RAG v1.0)",
    "page_index": 0,
    "char_start": 0,
    "char_end": 70,
    "embedding_checksum": "sha256_82f1b802aef"
  },
  {
    "chunk_id": "chunk_p1_n1",
    "text": "This platform features deterministic worker execution, multi-stage PDF fallback...",
    "page_index": 0,
    "char_start": 72,
    "char_end": 154,
    "embedding_checksum": "sha256_91ef230a10c"
  }
]`,
    'entities.json': `{
  "entities": [
    {
      "name": "Kaustav Kumar",
      "type": "person",
      "occurrences": [
        {"page": 1, "context": "Built by Kaustav Kumar"}
      ]
    },
    {
      "name": "ScaleFlow",
      "type": "organization",
      "occurrences": [
        {"page": 1, "context": "ScaleFlow is a distributed..."}
      ]
    }
  ]
}`,
    'tables.json': `[
  {
    "table_id": "table_p1_t1",
    "caption": "Table 1: System Qualification Gates",
    "headers": ["Metric", "Baseline", "ScaleFlow"],
    "rows": [
      ["Recall@5", ">= 0.90", "0.95"],
      ["MRR", ">= 0.88", "0.92"]
    ],
    "page": 1
  }
]`
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflow: 'hidden' }}>
      
      {/* Sidebar Explorer */}
      <div 
        style={{ 
          width: explorerOpen ? '250px' : '0px', 
          borderRight: '1px solid var(--border-subtle)', 
          background: 'var(--bg-panel)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.2s',
          overflow: 'hidden',
          flexShrink: 0
        }}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
          <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={16} />
            WORKSPACE EXPLORER
          </h3>
        </div>

        <div style={{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <ChevronDown size={14} />
            <span>📁 artifacts/</span>
          </div>

          {Object.keys(mockPayloads).map(filename => {
            const isSelected = selectedFile === filename;
            return (
              <button
                key={filename}
                onClick={() => setSelectedFile(filename)}
                style={{
                  background: isSelected ? 'rgba(255,255,255,0.04)' : 'transparent',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '8px 12px',
                  color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontWeight: isSelected ? 600 : 400
                }}
              >
                <FileJson size={14} style={{ color: isSelected ? 'var(--color-accent)' : 'var(--text-muted)' }} />
                {filename}
              </button>
            );
          })}
        </div>
      </div>

      {/* Editor stage */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        
        {/* Editor tabs */}
        <div style={{ display: 'flex', background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-subtle)', padding: '0 16px', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex' }}>
            <span style={{ padding: '12px 20px', background: 'var(--bg-primary)', borderRight: '1px solid var(--border-subtle)', borderTop: '2px solid var(--color-accent)', fontWeight: 600, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FileJson size={12} />
              {selectedFile}
            </span>
          </div>

          <Button variant="secondary" size="small" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Download size={12} />
            Download Artifact
          </Button>
        </div>

        {/* Code Content */}
        <div style={{ flex: 1, padding: '20px', overflow: 'auto', background: '#090d16', fontFamily: 'monospace', fontSize: '0.8rem', lineHeight: 1.6 }}>
          <pre style={{ margin: 0, color: '#f8fafc' }}>
            <code>{mockPayloads[selectedFile]}</code>
          </pre>
        </div>
      </div>

    </div>
  );
};

export default ArtifactsExplorer;
