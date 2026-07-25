import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
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
  // Parallax Hero Effect State
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Hero Product Simulation Stateful Cycle
  // 0: Upload, 1: Parse, 2: Graph, 3: Query, 4: Grounded Answer
  const [simStep, setSimStep] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

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
            <Button className="btn-primary" variant="primary" style={{ padding: '0 var(--spacing-24)', height: '42px' }} onClick={() => (window.location.href = '/register')}>
              Get Started
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
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', height: '280px', backgroundColor: 'var(--bg-primary)' }}>
              
              {/* Mini Left Sidebar */}
              <div style={{ borderRight: '1px solid var(--border-subtle)', padding: 'var(--spacing-12) 8px', display: 'flex', flexDirection: 'column', gap: '12px', backgroundColor: 'var(--bg-panel)' }}>
                <div style={{ width: '100%', height: '14px', backgroundColor: 'var(--color-accent-glow)', border: '1px solid var(--color-accent)', borderRadius: '3px' }} />
                <div style={{ width: '80%', height: '10px', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '2px' }} />
                <div style={{ width: '70%', height: '10px', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '2px' }} />
                <div style={{ width: '90%', height: '10px', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '2px' }} />
              </div>

              {/* Main Workspace Frame */}
              <div style={{ padding: 'var(--spacing-16)', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)', overflow: 'hidden' }}>
                
                {/* Interactive Mockup Tabs */}
                <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px' }}>
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
                        backgroundColor: simStep === tab.step ? 'rgba(79, 70, 229, 0.08)' : 'transparent',
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
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 'var(--spacing-12)', height: '100%' }}>
                  
                  {/* Left: Document Vision Parse Pane */}
                  <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-6)', padding: 'var(--spacing-8)', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--bg-panel)', position: 'relative' }}>
                    <div style={{ width: '85%', height: '6px', backgroundColor: 'var(--text-disabled)', borderRadius: '1px' }} />
                    <div style={{ width: '95%', height: '6px', backgroundColor: 'var(--text-disabled)', borderRadius: '1px' }} />
                    <div style={{ width: '60%', height: '6px', backgroundColor: 'var(--text-disabled)', borderRadius: '1px' }} />
                    
                    {/* Bounding box scanning/highlighting based on state */}
                    {simStep === 0 && (
                      <div style={{ position: 'absolute', top: '24px', left: '8px', right: '8px', bottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.4)', borderRadius: '4px' }}>
                        <span style={{ fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>Uploading 82%</span>
                      </div>
                    )}

                    {simStep === 1 && (
                      <div style={{ position: 'absolute', top: '16px', left: '4px', right: '4px', height: '24px', border: '1.5px solid var(--color-success)', backgroundColor: 'rgba(16, 185, 129, 0.08)', borderRadius: '3px' }}>
                        <div style={{ width: '100%', height: '1.5px', backgroundColor: 'var(--color-success)', position: 'absolute', top: '0', animation: 'scan 1s infinite alternate' }} />
                      </div>
                    )}

                    {simStep >= 2 && (
                      <div style={{ position: 'absolute', top: '16px', left: '4px', right: '4px', height: '24px', border: '1.5px solid var(--color-accent)', backgroundColor: 'rgba(79, 70, 229, 0.06)', borderRadius: '3px' }}>
                        <span style={{ position: 'absolute', top: '-10px', left: '2px', fontSize: '7px', fontFamily: 'var(--font-mono)', color: 'var(--color-accent)', fontWeight: 'bold' }}>ANNEX_B</span>
                      </div>
                    )}

                    <div style={{ marginTop: 'auto', fontSize: '7px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      spatial_ref: [248, 14, 520, 18]
                    </div>
                  </div>

                  {/* Right: Knowledge Graph Canvas or Chat Answer generation */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    
                    {simStep < 3 ? (
                      /* Graph Canvas simulator */
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-6)', position: 'relative', overflow: 'hidden', backgroundColor: 'rgba(0,0,0,0.1)' }}>
                        <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
                          <path d="M 30 30 L 110 80 L 50 130" stroke="var(--color-accent)" strokeWidth="1.2" fill="none" opacity={simStep >= 2 ? 0.6 : 0.1} />
                        </svg>
                        <circle cx="30" cy="30" r={simStep >= 2 ? '4' : '2'} fill={simStep >= 2 ? 'var(--color-accent)' : 'var(--text-disabled)'} />
                        <circle cx="110" cy="80" r={simStep >= 2 ? '4' : '2'} fill={simStep >= 2 ? 'var(--color-success)' : 'var(--text-disabled)'} />
                        <circle cx="50" cy="130" r={simStep >= 2 ? '4' : '2'} fill={simStep >= 2 ? 'var(--color-accent)' : 'var(--text-disabled)'} />
                        <span style={{ position: 'absolute', bottom: '4px', left: '4px', fontSize: '7px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {simStep >= 2 ? 'Nodes synced' : 'Empty Graph'}
                        </span>
                      </div>
                    ) : (
                      /* Chat Answers simulator */
                      <div style={{ flex: 1, border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-6)', padding: 'var(--spacing-8)', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--bg-panel)', fontFamily: 'var(--font-mono)', fontSize: '8px' }}>
                        <div style={{ color: 'var(--color-accent)', fontWeight: 'bold' }}>Q: interest fallback?</div>
                        <div style={{ color: 'var(--text-primary)', display: 'flex', flexWrap: 'wrap', gap: '2px' }}>
                          <span>Fallback rate is SOFR + 0.125%</span>
                          {simStep === 4 && (
                            <span style={{ display: 'inline-block', padding: '1px 3px', backgroundColor: 'rgba(16,185,129,0.15)', border: '1px solid var(--color-success)', borderRadius: '2px', color: 'var(--color-success)', fontSize: '7px' }}>
                              [Annex B]
                            </span>
                          )}
                        </div>
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

        {/* Feature Grid: 3 columns desktop, 2 columns tablet, 1 column mobile */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 'var(--spacing-24)',
          }}
        >
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
