/* eslint-disable no-unused-vars */
import React, { useState } from 'react';
import { Settings, Save, Sparkles, Sliders, Shield, Database } from 'lucide-react';
import Button from '../components/ui/Button';

export const SettingsPage = () => {
  // Model Configs
  const [embeddingModel, setEmbeddingModel] = useState('BAAI/bge-base-en-v1.5');
  const [llmModel, setLlmModel] = useState('google/gemini-2.5-flash');
  const [retrieverType, setRetrieverType] = useState('hybrid'); // 'semantic' | 'graph' | 'bm25' | 'hybrid'
  const [rerankerType, setRerankerType] = useState('cross-encoder');
  
  // Chunker Configs
  const [chunkSize, setChunkSize] = useState(500);
  const [overlapSize, setOverlapSize] = useState(55);
  
  // Hyperparameters
  const [topK, setTopK] = useState(5);
  const [graphDepth, setGraphDepth] = useState(2);
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(1024);
  
  // Cache / Feature Toggles
  const [cachingEnabled, setCachingEnabled] = useState(true);
  const [streamingEnabled, setStreamingEnabled] = useState(true);

  const handleSave = () => {
    alert("Configuration saved successfully!");
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Configuration & Settings</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Configure document intelligence parameters, LLM experts, and resource governance limits.</p>
      </div>

      {/* Settings Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', maxWidth: '1200px' }}>
        
        {/* Panel 1: RAG Architecture & Models */}
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} style={{ color: 'var(--color-accent)' }} />
            Models & Retrievers
          </h2>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>PRIMARY LLM EXPERT MODEL</label>
            <select value={llmModel} onChange={(e) => setLlmModel(e.target.value)} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
              <option value="google/gemini-2.5-flash">Gemini 2.5 Flash (Production Standard)</option>
              <option value="google/gemini-2.0-flash">Gemini 2.0 Flash</option>
              <option value="openai-gpt-4o">OpenAI GPT-4o Fallback</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>EMBEDDING MODEL</label>
            <select value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
              <option value="BAAI/bge-base-en-v1.5">BAAI bge-base-en-v1.5 (768-dim)</option>
              <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2 (384-dim)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>RETRIEVAL TYPE</label>
            <select value={retrieverType} onChange={(e) => setRetrieverType(e.target.value)} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
              <option value="hybrid">Hybrid (Keyword + Semantic + Graph)</option>
              <option value="graph">Hierarchical Graph Only</option>
              <option value="semantic">Vector Semantic Search Only</option>
              <option value="bm25">BM25 Keyword Search Only</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>RERANKER MODEL</label>
            <select value={rerankerType} onChange={(e) => setRerankerType(e.target.value)} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
              <option value="cross-encoder">Cross-Encoder (High Precision)</option>
              <option value="none">No Reranking</option>
            </select>
          </div>
        </div>

        {/* Panel 2: Chunker & Hyperparameters */}
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={16} style={{ color: 'var(--color-accent)' }} />
            Ingestion & Hyperparameters
          </h2>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>CHUNK SIZE (WORDS)</label>
              <input type="number" value={chunkSize} onChange={(e) => setChunkSize(parseInt(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>CHUNK OVERLAP</label>
              <input type="number" value={overlapSize} onChange={(e) => setOverlapSize(parseInt(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>RETRIEVAL TOP-K</label>
              <input type="number" value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>GRAPH DEPTH</label>
              <input type="number" value={graphDepth} onChange={(e) => setGraphDepth(parseInt(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>TEMPERATURE</label>
              <input type="number" step="0.1" min="0.0" max="1.0" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>MAX TOKENS</label>
              <input type="number" value={maxTokens} onChange={(e) => setMaxTokens(parseInt(e.target.value))} style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', color: 'var(--text-primary)', fontSize: '0.85rem' }} />
            </div>
          </div>

          {/* Toggles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Enable Enterprise Caching</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Caches vector queries, forecast states, and scheduler advice.</div>
              </div>
              <input type="checkbox" checked={cachingEnabled} onChange={(e) => setCachingEnabled(e.target.checked)} style={{ width: '18px', height: '18px', cursor: 'pointer' }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Streaming SSE Generation</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Streams answer tokens using Server Sent Events (SSE).</div>
              </div>
              <input type="checkbox" checked={streamingEnabled} onChange={(e) => setStreamingEnabled(e.target.checked)} style={{ width: '18px', height: '18px', cursor: 'pointer' }} />
            </div>
          </div>

          {/* Save button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <Button variant="primary" onClick={handleSave} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Save size={14} />
              Save Configuration
            </Button>
          </div>

        </div>

      </div>

    </div>
  );
};

export default SettingsPage;
