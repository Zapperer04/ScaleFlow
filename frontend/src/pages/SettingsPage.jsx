/* eslint-disable no-unused-vars */
import React, { useState } from 'react';
import { Settings, Save, AlertTriangle, ToggleLeft, Shield } from 'lucide-react';
import Button from '../components/ui/Button';

export const SettingsPage = () => {
  const [governanceLimit, setGovernanceLimit] = useState(1500);
  const [modelType, setModelType] = useState('gemini-1.5-flash');
  const [tesseractOcr, setTesseractOcr] = useState(true);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Configuration & settings</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Configure document intelligence parameters, LLM experts, and resource governance limits.</p>
      </div>

      {/* Settings Grid */}
      <div style={{ maxWidth: '650px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Model choice */}
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>PRIMARY LLM EXPERT MODEL</label>
          <select 
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '10px 14px',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          >
            <option value="gemini-1.5-flash">Gemini 1.5 Flash (Default)</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
            <option value="openai-gpt-4o">OpenAI GPT-4o Fallback</option>
          </select>
        </div>

        {/* Governance Limits */}
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>GOVERNANCE LIMIT (MAX CHUNKS)</label>
          <input 
            type="number"
            value={governanceLimit}
            onChange={(e) => setGovernanceLimit(parseInt(e.target.value))}
            style={{
              width: '100%',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '10px 14px',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          />
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)', marginTop: '4px', display: 'block' }}>
            Protects worker process memory bounds (aborts if limits are reached).
          </span>
        </div>

        {/* Fallbacks */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Tesseract OCR Fallback Ingestion</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Trigger local OCR indexing if text density falls below threshold limits.</div>
          </div>
          <input 
            type="checkbox" 
            checked={tesseractOcr}
            onChange={(e) => setTesseractOcr(e.target.checked)}
            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
          />
        </div>

        {/* Save button */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Save size={14} />
            Save Configuration
          </Button>
        </div>

      </div>

    </div>
  );
};

export default SettingsPage;
