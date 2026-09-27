import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { useAuth } from '../contexts/AuthContext';
import {
  Search,
  CheckCircle,
  XCircle,
  FileText,
  GitMerge,
  HelpCircle,
  Terminal,
  Activity,
  Sparkles,
  Layers,
  Check
} from 'lucide-react';

export const LandingPage = () => {
  const { token, login } = useAuth();
  // Parallax Hero Effect State
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleLaunchWorkspace = async () => {
    if (token) {
      window.location.href = '/workspace';
    } else {
      try {
        await login('admin', 'password', true);
        window.location.href = '/workspace';
      } catch (e) {
        window.location.href = '/login';
      }
    }
  };

  // Hero Product Simulation Stateful Cycle
  // 0: Upload, 1: Parse, 2: Graph, 3: Query, 4: Grounded Answer
  const [simStep, setSimStep] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Fast 1-second 0-100% upload progress animation when entering Step 0
  useEffect(() => {
    if (simStep === 0) {
      setUploadProgress(0);
      const start = Date.now();
      const duration = 1000; // 1 second duration
      const interval = setInterval(() => {
        const elapsed = Date.now() - start;
        const p = Math.min(100, Math.floor((elapsed / duration) * 100));
        setUploadProgress(p);
        if (p >= 100) {
          clearInterval(interval);
        }
      }, 20);
      return () => clearInterval(interval);
    }
  }, [simStep]);

  // Stateful Walkthrough (Section 2)
  const [walkthroughStep, setWalkthroughStep] = useState(0);
  const [paneAnimationKey, setPaneAnimationKey] = useState(0);

  const handleMouseMove = (e) => {
    const { clientX, clientY } = e;
    const x = (clientX - window.innerWidth / 2) / 60;
    const y = (clientY - window.innerHeight / 2) / 60;
    setMousePos({ x, y });
  };

  // Autoplay Hero Product Simulation
  useEffect(() => {
    if (!isAutoPlaying) return;
    const timer = setInterval(() => {
      setSimStep((prev) => (prev + 1) % 5);
    }, 4000);
    return () => clearInterval(timer);
  }, [isAutoPlaying]);

  // Handle manual tab selection on Hero Mockup
  const handleHeroTabClick = (stepIdx) => {
    setIsAutoPlaying(false); // Stop autoplay when user manually interacts
    setSimStep(stepIdx);
  };

  // Handle Walkthrough manual step selection + force animation trigger
  const handleWalkthroughStepChange = (idx) => {
    setWalkthroughStep(idx);
    setPaneAnimationKey(prev => prev + 1);
  };

  // Autoplay Walkthrough (Section 2)
  useEffect(() => {
    const timer = setInterval(() => {
      setWalkthroughStep((prev) => {
        const next = (prev + 1) % 5;
        setPaneAnimationKey(k => k + 1);
        return next;
      });
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      onMouseMove={handleMouseMove}
      style={{
        width: '100%',
        overflowX: 'hidden',
        backgroundColor: 'var(--bg-primary)',
      }}
    >
      {/* 1. HERO SECTION */}
      <section
        id="hero"
        style={{
          maxWidth: 'var(--max-width-landing)',
          margin: '0 auto',
          padding: 'var(--spacing-48) var(--spacing-32) var(--spacing-32) var(--spacing-32)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: 'var(--spacing-48)',
          alignItems: 'center',
          minHeight: '82vh',
        }}
      >
        {/* Left Copy */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-20)' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--spacing-8)',
              backgroundColor: 'rgba(79, 70, 229, 0.06)',
              border: '1px solid rgba(79, 70, 229, 0.15)',
              borderRadius: 'var(--radius-18)',
              padding: '4px 12px',
              width: 'fit-content',
            }}
          >
            <Sparkles size={12} style={{ color: 'var(--color-accent)' }} />
            <span style={{ fontSize: '10px', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-accent)', letterSpacing: '0.08em' }}>
              LAYOUT-AWARE MR-RAG
            </span>
          </div>

          <h1
            style={{
              fontSize: 'clamp(2.25rem, 5.5vw, 3.65rem)',
              lineHeight: 1.12,
              fontWeight: 'var(--font-weight-bold)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)',
              letterSpacing: 'var(--ls-tight)',
            }}
          >
            Understand complex documents the way humans do.
          </h1>

          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '1.05rem',
              lineHeight: 'var(--lh-relaxed)',
              maxWidth: '520px',
              margin: 0,
            }}
          >
            Parse layouts, build knowledge graphs, retrieve evidence, and generate grounded answers with spatial citations.
          </p>

          <div style={{ display: 'flex', gap: 'var(--spacing-12)', flexWrap: 'wrap', marginTop: 'var(--spacing-8)' }}>
            <Button className="btn-primary" variant="primary" style={{ padding: '0 var(--spacing-24)', height: '42px' }} onClick={handleLaunchWorkspace}>
              Launch Workspace
            </Button>
            <Button className="btn-secondary" variant="secondary" style={{ padding: '0 var(--spacing-24)', height: '42px' }} onClick={() => {
              const element = document.getElementById('how-it-works');
              if (element) element.scrollIntoView({ behavior: 'smooth' });
            }}>
              View Demo
            </Button>
          </div>
        </div>

        {/* Right Product Simulator (Interactive Mockup) */}
        <div
          style={{
            transform: `translate(${mousePos.x}px, ${mousePos.y}px)`,
            transition: 'transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1)',
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '540px',
              backgroundColor: 'var(--bg-panel)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-14)',
              boxShadow: 'var(--shadow-lg)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Window bar */}
            <div
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                padding: 'var(--spacing-12) var(--spacing-24)',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ff5f56' }} />
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ffbd2e' }} />
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#27c93f' }} />
              </div>
              <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                ScaleFlow Workspace &bull; Ingestion Active
              </div>
            </div>

            {/* Miniature App Layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '105px 1fr', height: '290px', backgroundColor: 'var(--bg-primary)' }}>
              
              {/* Mini Left Sidebar */}
              <div style={{ borderRight: '1px solid var(--border-subtle)', padding: '8px 6px', display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: 'var(--bg-panel)' }}>
                <div style={{ fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontWeight: 'bold', padding: '0 4px', letterSpacing: '0.05em' }}>
                  DOCUMENTS
                </div>
                <div style={{ width: '100%', padding: '4px 6px', backgroundColor: 'rgba(79, 70, 229, 0.12)', border: '1px solid var(--color-accent)', borderRadius: '4px', fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  📄 credit_v2.pdf
                </div>
                <div style={{ width: '100%', padding: '4px 6px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '4px', fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  📊 q4_report.pdf
                </div>
                <div style={{ width: '100%', padding: '4px 6px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '4px', fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  📜 deal_terms.pdf
                </div>
              </div>

              {/* Main Workspace Frame */}
              <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px', overflow: 'hidden' }}>
                
                {/* Interactive Mockup Tabs */}
                <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px', alignItems: 'center' }}>
                  {[
                    { label: 'Upload', step: 0 },
                    { label: 'Parse', step: 1 },
                    { label: 'Graph', step: 2 },
                    { label: 'Retrieve', step: 3 },
                    { label: 'Cite', step: 4 }
                  ].map((tab) => (
                    <button
                      key={tab.label}
                      onClick={() => handleHeroTabClick(tab.step)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: simStep === tab.step ? 'var(--color-accent)' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '9px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-6)',
                        backgroundColor: simStep === tab.step ? 'rgba(79, 70, 229, 0.12)' : 'transparent',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {tab.label.toUpperCase()}
                    </button>
                  ))}
                  {/* Auto Play status indicator */}
                  {!isAutoPlaying && (
                    <button
                      onClick={() => setIsAutoPlaying(true)}
                      style={{
                        marginLeft: 'auto',
                        background: 'none',
                        border: 'none',
                        color: 'var(--color-success)',
                        fontSize: '8px',
                        fontFamily: 'var(--font-mono)',
                        cursor: 'pointer',
                      }}
                    >
                      PLAY AUTO
                    </button>
                  )}
                </div>

                {/* Main simulation content split */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px', height: '100%', minHeight: 0 }}>
                  
                  {/* Left: Document Vision Parse Pane */}
                  <div style={{ border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--bg-panel)', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--color-accent)', fontWeight: 'bold', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '3px' }}>
                      CREDIT_AGREEMENT.PDF &bull; P.4
                    </div>
                    
                    {/* Clause Block wrapped inside dynamic Bounding Box container */}
                    <div style={{
                      position: 'relative',
                      padding: '6px',
                      marginTop: '4px',
                      borderRadius: '4px',
                      border: simStep >= 2
                        ? '1.5px solid var(--color-accent)'
                        : simStep === 1
                        ? '1.5px solid var(--color-success)'
                        : '1px solid transparent',
                      backgroundColor: simStep >= 2
                        ? 'rgba(79, 70, 229, 0.08)'
                        : simStep === 1
                        ? 'rgba(16, 185, 129, 0.06)'
                        : 'transparent',
                      transition: 'all 0.2s ease',
                    }}>
                      {/* Bounding Box Label Badge */}
                      {simStep >= 2 && (
                        <span style={{
                          position: 'absolute',
                          top: '-7px',
                          right: '6px',
                          fontSize: '6px',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--color-accent)',
                          fontWeight: 'bold',
                          backgroundColor: 'var(--bg-panel)',
                          border: '1px solid var(--color-accent)',
                          padding: '0 4px',
                          borderRadius: '2px',
                          lineHeight: '1.2',
                        }}>
                          BOUNDING BOX #12.4
                        </span>
                      )}
                      {simStep === 1 && (
                        <span style={{
                          position: 'absolute',
                          top: '-7px',
                          right: '6px',
                          fontSize: '6px',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--color-success)',
                          fontWeight: 'bold',
                          backgroundColor: 'var(--bg-panel)',
                          border: '1px solid var(--color-success)',
                          padding: '0 4px',
                          borderRadius: '2px',
                          lineHeight: '1.2',
                        }}>
                          VLM SCANNING
                        </span>
                      )}

                      <div style={{ fontSize: '8px', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '3px' }}>
                        Sec 4.2 Interest Rate Fallback
                      </div>
                      <div style={{ fontSize: '7.5px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                        If SOFR Benchmark is unavailable, rate is <strong style={{ color: 'var(--color-accent)' }}>Daily SOFR + 0.125%</strong>.
                      </div>
                    </div>

                    <div style={{ fontSize: '6.5px', color: 'var(--text-muted)', paddingLeft: '4px' }}>
                      Clause 12.4 &bull; Annex B Schedule
                    </div>

                    {/* Upload progress overlay (1-second 0-100% animation) */}
                    {simStep === 0 && (
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        backgroundColor: 'rgba(11, 15, 25, 0.88)',
                        backdropFilter: 'blur(3px)',
                        padding: '0 16px',
                        zIndex: 10
                      }}>
                        <div style={{
                          fontSize: '8.5px',
                          fontFamily: 'var(--font-mono)',
                          color: uploadProgress < 100 ? 'var(--color-accent)' : 'var(--color-success)',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}>
                          {uploadProgress < 100 ? (
                            <>Uploading credit_v2.pdf... {uploadProgress}%</>
                          ) : (
                            <>✓ Upload Complete (100%)</>
                          )}
                        </div>
                        <div style={{
                          width: '100%',
                          maxWidth: '140px',
                          height: '4px',
                          backgroundColor: 'rgba(255, 255, 255, 0.1)',
                          borderRadius: '2px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${uploadProgress}%`,
                            backgroundColor: uploadProgress < 100 ? 'var(--color-accent)' : 'var(--color-success)',
                            borderRadius: '2px',
                            transition: 'width 0.05s linear'
                          }} />
                        </div>
                      </div>
                    )}

                    <div style={{ marginTop: 'auto', fontSize: '6.5px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      spatial_ref: [p.4, 248, 14, 520, 18]
                    </div>
                  </div>

                  {/* Right: Context-aware step view */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '100%' }}>
                    
                    {/* Step 0: Upload Ingestion Queue */}
                    {simStep === 0 && (
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: '6px', backgroundColor: 'var(--bg-panel)', padding: '8px', display: 'flex', flexDirection: 'column', gap: '6px', fontFamily: 'var(--font-mono)' }}>
                        <div style={{ fontSize: '7.5px', color: 'var(--color-accent)', fontWeight: 'bold', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '3px' }}>
                          INGESTION QUEUE
                        </div>
                        <div style={{ fontSize: '7.5px', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div>File: <strong>credit_v2.pdf</strong> (1.4 MB)</div>
                          <div>Engine: <strong>ScaleFlow MR-RAG</strong></div>
                          <div>Target: <strong>Qdrant + SQLite Graph</strong></div>
                        </div>
                        <div style={{ marginTop: 'auto', fontSize: '7px', color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          🟢 Worker Node #1 Allocated
                        </div>
                      </div>
                    )}

                    {/* Step 1: VLM Layout Parser */}
                    {simStep === 1 && (
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: '6px', backgroundColor: 'var(--bg-panel)', padding: '8px', display: 'flex', flexDirection: 'column', gap: '5px', fontFamily: 'var(--font-mono)' }}>
                        <div style={{ fontSize: '7.5px', color: 'var(--color-success)', fontWeight: 'bold', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '3px' }}>
                          VLM LAYOUT PARSER
                        </div>
                        <div style={{ fontSize: '7px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                          <div>✓ 4 Layout Blocks Detected</div>
                          <div>✓ Table Grid Recognized</div>
                          <div>✓ OCR Confidence: 99.1%</div>
                        </div>
                        <div style={{ marginTop: 'auto', fontSize: '7px', color: 'var(--color-success)' }}>
                          ⚡ Building Canonical Normalizer
                        </div>
                      </div>
                    )}

                    {/* Step 2: Knowledge Graph Construction */}
                    {simStep === 2 && (
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: '6px', position: 'relative', overflow: 'hidden', backgroundColor: 'rgba(0,0,0,0.25)', padding: '6px', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ fontSize: '7.5px', fontFamily: 'var(--font-mono)', color: 'var(--color-accent)', fontWeight: 'bold', marginBottom: '4px' }}>
                          KNOWLEDGE GRAPH
                        </div>
                        <svg style={{ width: '100%', height: '75px' }}>
                          <line x1="20" y1="20" x2="90" y2="20" stroke="var(--color-accent)" strokeWidth="1.5" />
                          <line x1="90" y1="20" x2="55" y2="60" stroke="var(--color-success)" strokeWidth="1.5" />
                          
                          <circle cx="20" cy="20" r="5" fill="var(--color-accent)" />
                          <circle cx="90" cy="20" r="5" fill="var(--color-accent)" />
                          <circle cx="55" cy="60" r="5" fill="var(--color-success)" />
                          
                          <text x="5" y="32" fill="var(--text-secondary)" fontSize="6.5" fontFamily="sans-serif">Credit Doc</text>
                          <text x="75" y="32" fill="var(--text-secondary)" fontSize="6.5" fontFamily="sans-serif">Sec 4.2</text>
                          <text x="35" y="72" fill="var(--color-success)" fontSize="6.5" fontWeight="bold" fontFamily="sans-serif">SOFR+0.125%</text>
                        </svg>
                        <div style={{ marginTop: 'auto', fontSize: '7px', fontFamily: 'var(--font-mono)', color: 'var(--color-success)' }}>
                          🟢 3 Nodes & 2 Edges Synced
                        </div>
                      </div>
                    )}

                    {/* Step 3 & 4: Retrieval and Grounded Citation Answer */}
                    {simStep >= 3 && (
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '6px', display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'var(--bg-panel)', fontFamily: 'var(--font-mono)', fontSize: '7.5px' }}>
                        <div style={{ color: 'var(--color-accent)', fontWeight: 'bold', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '3px' }}>
                          {simStep === 3 ? 'HYBRID RETRIEVAL' : 'GROUNDED ANSWER'}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '7px' }}>
                          Q: What is interest fallback?
                        </div>
                        <div style={{ color: 'var(--text-primary)', fontSize: '7.5px', lineHeight: 1.3 }}>
                          Per Sec 4.2, rate is <strong>SOFR + 0.125%</strong> per annum.
                        </div>
                        {simStep === 4 && (
                          <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                            <span style={{ padding: '1px 4px', backgroundColor: 'rgba(16,185,129,0.15)', border: '1px solid var(--color-success)', borderRadius: '3px', color: 'var(--color-success)', fontSize: '6.5px', fontWeight: 'bold' }}>
                              📍 Annex B, Clause 12.4
                            </span>
                            <span style={{ color: 'var(--color-success)', fontSize: '6.5px' }}>
                              ✓ 99.4% Grounded
                            </span>
                          </div>
                        )}
                        {simStep === 3 && (
                          <div style={{ marginTop: 'auto', color: 'var(--text-muted)', fontSize: '6.5px' }}>
                            ⚡ P95 Latency: 18.2ms
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. STATEFUL PROCESS WALKTHROUGH */}
      <section
        id="how-it-works"
        style={{
          borderTop: '1px solid var(--border-divider)',
          backgroundColor: 'rgba(0, 0, 0, 0.15)',
          padding: 'var(--spacing-48) 0',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-48)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Stateful Ingestion Journey
            </span>
            <h2 style={{ fontSize: 'var(--font-size-3xl)', fontFamily: 'var(--font-display)', marginTop: 'var(--spacing-8)', marginBottom: 'var(--spacing-16)' }}>
              From Document to Grounded Answer
            </h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
              Interact with the stateful timeline to track document ingestion, metadata indexing, layout parsing, and relational graph RAG lookup.
            </p>
          </div>

          {/* Unified Timeline & Visualizer Container */}
          <div
            style={{
              backgroundColor: 'var(--bg-panel)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-14)',
              padding: 'var(--spacing-32)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--spacing-32)',
              boxShadow: 'var(--shadow-md)',
            }}
          >
            {/* Timeline Progress Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative', overflow: 'visible' }}>
              
              {/* Back line progress */}
              <div style={{ position: 'absolute', top: '16px', left: '20px', right: '20px', height: '2px', backgroundColor: 'var(--border-subtle)', zIndex: 1 }} />
              <div style={{ position: 'absolute', top: '16px', left: '20px', width: `${walkthroughStep * 25}%`, height: '2px', backgroundColor: 'var(--color-accent)', transition: 'width 0.3s ease', zIndex: 1 }} />

              {['Upload', 'Parse', 'Graph', 'Retrieve', 'Grounded Answer'].map((step, idx) => (
                <button
                  key={step}
                  onClick={() => handleWalkthroughStepChange(idx)}
                  style={{
                    background: 'none',
                    border: 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    cursor: 'pointer',
                    zIndex: 2,
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '50%',
                      backgroundColor: walkthroughStep >= idx ? 'var(--color-accent)' : 'var(--bg-primary)',
                      border: '2px solid',
                      borderColor: walkthroughStep >= idx ? 'var(--color-accent)' : 'var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: walkthroughStep >= idx ? 'var(--text-white)' : 'var(--text-secondary)',
                      fontWeight: 'bold',
                      fontSize: 'var(--font-size-xs)',
                      transition: 'all var(--transition-normal)',
                    }}
                  >
                    {idx + 1}
                  </div>
                  <span
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      marginTop: '8px',
                      color: walkthroughStep === idx ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontWeight: walkthroughStep === idx ? 600 : 400,
                      transition: 'color var(--transition-normal)',
                    }}
                  >
                    {step}
                  </span>
                </button>
              ))}
            </div>

            {/* Display Pane with dynamic transition animation */}
            <div
              key={paneAnimationKey}
              className="walkthrough-pane-active"
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                borderRadius: 'var(--radius-10)',
                border: '1px solid var(--border-subtle)',
                padding: 'var(--spacing-24)',
                minHeight: '160px',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-24)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', borderRadius: 'var(--radius-6)', backgroundColor: 'var(--color-accent-glow)', color: 'var(--color-accent)', flexShrink: 0 }}>
                {walkthroughStep === 0 && <FileText size={24} />}
                {walkthroughStep === 1 && <Layers size={24} />}
                {walkthroughStep === 2 && <GitMerge size={24} />}
                {walkthroughStep === 3 && <Search size={24} />}
                {walkthroughStep === 4 && <CheckCircle size={24} />}
              </div>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: '6px' }}>
                  {walkthroughStep === 0 && 'Step 1: Document Upload & Preprocessing'}
                  {walkthroughStep === 1 && 'Step 2: Vision-based Layout Parsing'}
                  {walkthroughStep === 2 && 'Step 3: Relationship Knowledge Graph Construction'}
                  {walkthroughStep === 3 && 'Step 4: Lexical & Graph-aware Retrieval'}
                  {walkthroughStep === 4 && 'Step 5: Grounded Response with Citation Overlay'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                  {walkthroughStep === 0 && 'The file is split, processed, and sanitized. We extract basic bounding coordinate scales to prepare for multi-column structural visual layouts.'}
                  {walkthroughStep === 1 && 'Our parser identifies grids, tables, flowcharts, and titles to map exactly where concepts sit relative to each other on the page.'}
                  {walkthroughStep === 2 && 'Extracted legal/financial entities, clauses, and definitions are connected dynamically into a cross-referenced knowledge graph.'}
                  {walkthroughStep === 3 && 'We combine semantic search queries with logical graph traversal paths to fetch chunks containing direct facts and surrounding dependencies.'}
                  {walkthroughStep === 4 && 'ScaleFlow generates the final text response citing coordinates. Clickable reference boxes highlight the evidence overlay in real-time.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. FEATURES GRID SECTION */}
      <section
        id="features"
        style={{
          maxWidth: 'var(--max-width-landing)',
          margin: '0 auto',
          padding: 'var(--spacing-48) var(--spacing-32)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-48)' }}>
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Core Capabilities
          </span>
          <h2 style={{ fontSize: 'var(--font-size-3xl)', fontFamily: 'var(--font-display)', marginTop: 'var(--spacing-8)', marginBottom: 'var(--spacing-16)' }}>
            Engineered for Precision Search
          </h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
            ScaleFlow bridges the gap between raw document databases and explainable, fact-checked RAG pipelines.
          </p>
        </div>

        {/* Feature Grid: 3 columns desktop (3x2 grid), 2 columns tablet, 1 column mobile */}
        <div className="core-capabilities-grid">
          {/* Card 1 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <GitMerge size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Graph-aware Retrieval</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Traverse document hierarchies, sections, and linked concepts natively without missing critical fallback conditions.
              </p>
            </div>
          </Card>

          {/* Card 2 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <FileText size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Visual Document Parsing</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Analyze layout structures, tables, and nested diagrams directly to retain visual structural hierarchy.
              </p>
            </div>
          </Card>

          {/* Card 3 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <HelpCircle size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Explainable Answers</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Review step-by-step reasoning steps of the LLM pipeline, detailing exact nodes and vectors used.
              </p>
            </div>
          </Card>

          {/* Card 4 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <CheckCircle size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Citation Highlighting</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Inspect source text segments with spatial bounding boxes overlaid on the parsed PDF files.
              </p>
            </div>
          </Card>

          {/* Card 5 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <Search size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Hybrid Search</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Combine semantic dense embeddings with precise lexical keyword indices for optimal lookup sensitivity.
              </p>
            </div>
          </Card>

          {/* Card 6 */}
          <Card className="feature-hover-card" style={{ transition: 'all var(--transition-normal)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <Activity size={20} style={{ color: 'var(--color-accent)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Streaming Responses</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                Receive immediate word-by-word streaming generation while the agent processes citations in the background.
              </p>
            </div>
          </Card>
        </div>
      </section>

      {/* 4. WHY SCALEFLOW: COMPARISON TABLE (EMPHASIZED) */}
      <section
        style={{
          borderTop: '1px solid var(--border-divider)',
          backgroundColor: 'rgba(0, 0, 0, 0.1)',
          padding: 'var(--spacing-48) 0',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-48)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Comparison
            </span>
            <h2 style={{ fontSize: 'var(--font-size-3xl)', fontFamily: 'var(--font-display)', marginTop: 'var(--spacing-8)', marginBottom: 'var(--spacing-16)' }}>
              Next-generation Retrieval Performance
            </h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
              A comparison showing why layout-aware RAG pipelines deliver unmatched evidence grounding.
            </p>
          </div>

          <div
            style={{
              overflowX: 'auto',
              borderRadius: 'var(--radius-14)',
              border: '1px solid var(--border-subtle)',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--font-size-sm)',
                textAlign: 'left',
                backgroundColor: 'var(--bg-panel)',
              }}
            >
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-divider)', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                  <th style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-primary)', fontWeight: 600 }}>Capability</th>
                  <th style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-secondary)', fontWeight: 500 }}>Traditional RAG</th>
                  <th
                    style={{
                      padding: 'var(--spacing-16) var(--spacing-24)',
                      color: 'var(--text-white)',
                      fontWeight: 700,
                      backgroundColor: 'rgba(79, 70, 229, 0.1)',
                      borderLeft: '2px solid var(--color-accent)',
                      borderRight: '2px solid var(--color-accent)',
                      position: 'relative',
                    }}
                  >
                    {/* RECOMMENDED BADGE */}
                    <div
                      style={{
                        position: 'absolute',
                        top: '-10px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        backgroundColor: 'var(--color-accent)',
                        color: 'var(--text-white)',
                        fontSize: '8px',
                        fontWeight: 'bold',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-6)',
                        letterSpacing: '0.05em',
                      }}
                    >
                      RECOMMENDED
                    </div>
                    ScaleFlow
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid var(--border-divider)' }}>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', fontWeight: 600 }}>Ingestion Strategy</td>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={14} style={{ color: 'var(--color-failure)' }} /> Flat Text Chunks
                    </div>
                  </td>
                  <td
                    style={{
                      padding: 'var(--spacing-16) var(--spacing-24)',
                      color: 'var(--text-primary)',
                      fontWeight: 'bold',
                      backgroundColor: 'rgba(79, 70, 229, 0.06)',
                      borderLeft: '2px solid var(--color-accent)',
                      borderRight: '2px solid var(--color-accent)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Check size={18} style={{ color: 'var(--color-success)' }} /> Layout-aware Vision parsing
                    </div>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid var(--border-divider)' }}>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', fontWeight: 600 }}>Citations</td>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={14} style={{ color: 'var(--color-failure)' }} /> Simple file name match
                    </div>
                  </td>
                  <td
                    style={{
                      padding: 'var(--spacing-16) var(--spacing-24)',
                      color: 'var(--text-primary)',
                      fontWeight: 'bold',
                      backgroundColor: 'rgba(79, 70, 229, 0.06)',
                      borderLeft: '2px solid var(--color-accent)',
                      borderRight: '2px solid var(--color-accent)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Check size={18} style={{ color: 'var(--color-success)' }} /> Spatial page coordinate bounding boxes
                    </div>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid var(--border-divider)' }}>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', fontWeight: 600 }}>Search Index</td>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={14} style={{ color: 'var(--color-failure)' }} /> Semantic vector database only
                    </div>
                  </td>
                  <td
                    style={{
                      padding: 'var(--spacing-16) var(--spacing-24)',
                      color: 'var(--text-primary)',
                      fontWeight: 'bold',
                      backgroundColor: 'rgba(79, 70, 229, 0.06)',
                      borderLeft: '2px solid var(--color-accent)',
                      borderRight: '2px solid var(--color-accent)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Check size={18} style={{ color: 'var(--color-success)' }} /> Hybrid Lexical + Vector + relational graph maps
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', fontWeight: 600 }}>Explainable Path</td>
                  <td style={{ padding: 'var(--spacing-16) var(--spacing-24)', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={14} style={{ color: 'var(--color-failure)' }} /> Hidden black-box outputs
                    </div>
                  </td>
                  <td
                    style={{
                      padding: 'var(--spacing-16) var(--spacing-24)',
                      color: 'var(--text-primary)',
                      fontWeight: 'bold',
                      backgroundColor: 'rgba(79, 70, 229, 0.06)',
                      borderLeft: '2px solid var(--color-accent)',
                      borderRight: '2px solid var(--color-accent)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Check size={18} style={{ color: 'var(--color-success)' }} /> Full traversal logic tracking inspector
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 5. ARCHITECTURE */}
      <section
        style={{
          borderTop: '1px solid var(--border-divider)',
          padding: 'var(--spacing-48) 0',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-48)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Architecture
            </span>
            <h2 style={{ fontSize: 'var(--font-size-3xl)', fontFamily: 'var(--font-display)', marginTop: 'var(--spacing-8)', marginBottom: 'var(--spacing-16)' }}>
              Modular Data Indexing Pipeline
            </h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
              A clean visualization of document parsing, knowledge graph ingestion, and LLM coordinator components.
            </p>
          </div>

          <div
            style={{
              backgroundColor: 'var(--bg-panel)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-14)',
              padding: 'var(--spacing-32)',
              display: 'flex',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-md)',
            }}
          >
            {/* Inline SVG Blueprint Diagram with animated dashed lines */}
            <svg viewBox="0 0 800 240" style={{ width: '100%', maxWidth: '720px', height: 'auto' }}>
              <rect x="20" y="60" width="160" height="100" rx="8" fill="rgba(255,255,255,0.02)" stroke="var(--border-subtle)" strokeWidth="1.5" />
              <text x="100" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="13" fontWeight="600" fontFamily="var(--font-display)">1. Vision Parser</text>
              <text x="100" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="11" fontFamily="sans-serif">Table & Outline</text>
              <text x="100" y="132" textAnchor="middle" fill="var(--text-muted)" fontSize="10" fontFamily="sans-serif">Extraction</text>

              <path className="bp-arrow-path" d="M 180 110 L 240 110" stroke="var(--color-accent)" strokeWidth="2" fill="none" markerEnd="url(#bp-arrow)" />

              <rect x="250" y="50" width="220" height="120" rx="8" fill="rgba(79, 70, 229, 0.04)" stroke="var(--color-accent)" strokeWidth="1.5" />
              <text x="360" y="85" textAnchor="middle" fill="var(--text-primary)" fontSize="13" fontWeight="600" fontFamily="var(--font-display)">2. Hybrid Knowledge Index</text>
              <text x="360" y="105" textAnchor="middle" fill="var(--text-secondary)" fontSize="11" fontFamily="sans-serif">Dense Vector + Lexical</text>
              <text x="360" y="125" textAnchor="middle" fill="var(--text-secondary)" fontSize="11" fontFamily="sans-serif">+ Graph Relationships</text>
              <rect x="300" y="138" width="120" height="18" rx="4" fill="rgba(16, 185, 129, 0.1)" stroke="var(--color-success)" strokeWidth="1" />
              <text x="360" y="151" textAnchor="middle" fill="var(--color-success)" fontSize="9" fontWeight="bold" fontFamily="var(--font-mono)">REALTIME SYNC</text>

              <path className="bp-arrow-path" d="M 470 110 L 530 110" stroke="var(--color-accent)" strokeWidth="2" fill="none" markerEnd="url(#bp-arrow)" />

              <rect x="540" y="60" width="160" height="100" rx="8" fill="rgba(255,255,255,0.02)" stroke="var(--border-subtle)" strokeWidth="1.5" />
              <text x="620" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="13" fontWeight="600" fontFamily="var(--font-display)">3. LLM Coordinator</text>
              <text x="620" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="11" fontFamily="sans-serif">Explainable Path</text>
              <text x="620" y="132" textAnchor="middle" fill="var(--text-muted)" fontSize="10" fontFamily="sans-serif">Evidence Grounding</text>

              <defs>
                <marker id="bp-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-accent)" />
                </marker>
              </defs>
            </svg>
          </div>
        </div>
      </section>

      {/* 6. DEVELOPER FRIENDLY (EXPANDED BADGES) */}
      <section
        style={{
          borderTop: '1px solid var(--border-divider)',
          backgroundColor: 'rgba(0, 0, 0, 0.1)',
          padding: 'var(--spacing-48) 0',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--spacing-48)', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Developer Friendly
              </span>
              <h2 style={{ fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-display)', margin: 0 }}>Built for automated integration pipelines.</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
                ScaleFlow exposes fully documented OpenAPI endpoints and streaming APIs to trigger ingestion and search programmatically.
              </p>
              
              {/* Capability Badges Grid */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: 'var(--spacing-8)' }}>
                {['REST API', 'SSE Streaming', 'Docker Ingest', 'OpenAPI Specs', 'Graph Retrieval', 'Spatial Citations'].map((badge) => (
                  <span
                    key={badge}
                    style={{
                      padding: '4px 10px',
                      fontSize: '10px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-6)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {badge}
                  </span>
                ))}
              </div>
            </div>

            <Card style={{ padding: 0 }}>
              <div
                style={{
                  backgroundColor: 'var(--bg-panel)',
                  padding: 'var(--spacing-16)',
                  borderRadius: 'var(--radius-10)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px', color: 'var(--text-muted)' }}>
                  <Terminal size={14} />
                  <span>terminal_api.sh</span>
                </div>
                <div style={{ color: 'var(--text-muted)' }}># Query the Graph RAG engine</div>
                <div>
                  <span style={{ color: 'var(--color-accent)' }}>curl</span> -X POST <span style={{ color: 'var(--color-success)' }}>"https://api.scaleflow.ai/v1/query"</span> \
                </div>
                <div style={{ paddingLeft: '16px' }}>
                  -H <span style={{ color: 'var(--color-success)' }}>"Authorization: Bearer $SF_TOKEN"</span> \
                </div>
                <div style={{ paddingLeft: '16px' }}>
                  -d <span style={{ color: 'var(--color-success)' }}>{"'{\"query\": \"Retrieve interest fallback clause\"}'"}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* 8. CTA SECTION */}
      <section
        style={{
          borderTop: '1px solid var(--border-divider)',
          padding: 'var(--spacing-48) var(--spacing-24)',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-reading)',
            margin: '0 auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--spacing-16)',
            alignItems: 'center',
          }}
        >
          <h2 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.5rem)', fontFamily: 'var(--font-display)', fontWeight: 'var(--font-weight-bold)' }}>
            Start building with ScaleFlow today.
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-base)', lineHeight: 'var(--lh-relaxed)', margin: 0 }}>
            Unlock layout-aware document retrieval and production-grade knowledge graphs with ease.
          </p>
          <div style={{ display: 'flex', gap: 'var(--spacing-16)', marginTop: 'var(--spacing-8)' }}>
            <Button className="btn-primary" variant="primary" onClick={() => (window.location.href = '/register')}>
              Get Started
            </Button>
            <Button className="btn-secondary" variant="secondary" onClick={() => {
              const element = document.getElementById('how-it-works');
              if (element) element.scrollIntoView({ behavior: 'smooth' });
            }}>
              View Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Micro-interaction Styles Override */}
      <style>{`
        @keyframes scan {
          from { top: 0; }
          to { top: 100%; }
        }
        @keyframes fade-slide-in {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .walkthrough-pane-active {
          animation: fade-slide-in 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        .feature-hover-card {
          transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease !important;
        }
        .feature-hover-card:hover {
          border-color: var(--color-accent) !important;
          box-shadow: 0 4px 20px rgba(79, 70, 229, 0.15) !important;
          transform: translateY(-2px);
        }
        .btn-primary {
          transition: transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease !important;
        }
        .btn-primary:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
        }
        .btn-secondary {
          transition: transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease !important;
        }
        .btn-secondary:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(255, 255, 255, 0.05) !important;
        }
        @keyframes pulse-dash {
          to {
            stroke-dashoffset: -20;
          }
        }
        .bp-arrow-path {
          stroke-dasharray: 5;
          animation: pulse-dash 2.5s linear infinite;
        }

        .core-capabilities-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: var(--spacing-24);
        }
        @media (max-width: 992px) {
          .core-capabilities-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        @media (max-width: 600px) {
          .core-capabilities-grid {
            grid-template-columns: 1fr;
          }
        }

        /* Reduced Motion Media Query */
        @media (prefers-reduced-motion: reduce) {
          .bp-arrow-path,
          .walkthrough-pane-active,
          .feature-hover-card,
          .btn-primary,
          .btn-secondary {
            animation: none !important;
            transition: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};
export default LandingPage;
