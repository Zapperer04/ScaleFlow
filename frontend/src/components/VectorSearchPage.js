import React, { useState, useEffect } from 'react';
import { Database, Search, Cpu, FileText, Loader2, Sparkles, Trash2 } from 'lucide-react';
import { searchVectors, fetchVectorStats, fetchPipelines, createRetrievalPipeline, fetchRetrievalPipelineAnswer } from '../services/api';

const VectorSearchPage = () => {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [stats, setStats] = useState(null);
  const [results, setResults] = useState([]);
  const [ragAnswer, setRagAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ragLoading, setRagLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(null); // 'input', 'embed', 'search', 'synthesize', 'done'
  const [error, setError] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState('');

  const loadStats = async () => {
    try {
      const data = await fetchVectorStats();
      setStats(data);
    } catch (err) {
      console.error('Error fetching vector stats:', err);
    }
  };

  const loadPipelines = async () => {
    try {
      const data = await fetchPipelines();
      // Only keep document processing pipelines that are completed
      const docPipelines = (data || []).filter(p =>
        (p.pipeline_type === 'document_processing_demo' || p.pipeline_type === 'system_stability_pipeline') &&
        p.status === 'completed'
      );
      setPipelines(docPipelines);
      if (docPipelines.length > 0 && !selectedPipelineId) {
        setSelectedPipelineId(String(docPipelines[0].id));
      }
    } catch (err) {
      console.error('Error fetching pipelines:', err);
    }
  };

  useEffect(() => {
    loadStats();
    loadPipelines();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleVectorSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResults([]);
    setRagAnswer(null);
    setError(null);

    try {
      // Step-by-step query pipeline animation
      setCurrentStep('embed');
      await new Promise(r => setTimeout(r, 600));

      setCurrentStep('search');
      const searchData = await searchVectors(query, topK);
      setResults(searchData);
      
      await new Promise(r => setTimeout(r, 400));
      setCurrentStep('done');
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      setCurrentStep(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRagQuery = async () => {
    if (!query.trim()) return;

    setRagLoading(true);
    setRagAnswer(null);
    setResults([]);
    setError(null);

    try {
      // RAG Synthesizer execution sequence
      setCurrentStep('embed');
      // Create a query pipeline with pipeline_id_filter
      const payload = { query: query, top_k: 8 };
      if (selectedPipelineId) {
        payload.pipeline_id_filter = parseInt(selectedPipelineId);
      }
      if (!selectedPipelineId) {
        throw new Error('Please select an ingested document pipeline before running RAG. Use the dropdown above.');
      }
      const pipeline = await createRetrievalPipeline(payload);
      const pipelineId = pipeline.pipeline_id;

      setCurrentStep('search');
      await new Promise(r => setTimeout(r, 1200)); // wait for database retrieval and inference simulation

      setCurrentStep('synthesize');
      // Pull answer
      let attempts = 0;
      let answerData = null;
      while (attempts < 180) {
        await new Promise(r => setTimeout(r, 1000));
        answerData = await fetchRetrievalPipelineAnswer(pipelineId);
        if (answerData && ((answerData.final_answer && answerData.final_answer.answer) || answerData.answer || answerData.status === 'completed' || answerData.status === 'failed')) {
          break;
        }
        attempts++;
      }

      if (answerData && answerData.status === 'failed') {
        throw new Error(answerData.error || 'RAG generation failed.');
      }

      setRagAnswer(answerData);
      if (answerData?.retrieved_context?.results) {
        setResults(answerData.retrieved_context.results);
      } else if (answerData?.retrieved_chunks) {
        setResults(answerData.retrieved_chunks);
      }
      
      setCurrentStep('done');
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      setCurrentStep(null);
    } finally {
      setRagLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Header and Stats */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: '#fff' }}>Vector Search & RAG Control Plane</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '4px' }}>Query distributed vector indices and inspect retrieval relevance</p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Pipeline Selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Active Document Pipeline (for RAG)</label>
            <select
              value={selectedPipelineId}
              onChange={(e) => setSelectedPipelineId(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(91, 140, 255, 0.3)',
                color: '#fff',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                outline: 'none',
                minWidth: '240px'
              }}
            >
              <option value="">— Select completed ingestion pipeline —</option>
              {pipelines.map(p => (
                <option key={p.id} value={String(p.id)}>
                  #{p.id} {p.name} ({p.pipeline_type === 'document_processing_demo' ? 'doc' : 'stability'})
                </option>
              ))}
            </select>
          </div>

          {stats && (
            <div style={{ display: 'flex', gap: '16px' }}>
              <div className="panel" style={{ margin: 0, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Database size={18} style={{ color: '#5B8CFF' }} />
                <div>
                  <span style={{ display: 'block', fontSize: '0.65rem', color: '#94a3b8' }}>QDRANT COLLECTION</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>{stats.collection}</span>
                </div>
              </div>
              <div className="panel" style={{ margin: 0, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Cpu size={18} style={{ color: '#10B981' }} />
                <div>
                  <span style={{ display: 'block', fontSize: '0.65rem', color: '#94a3b8' }}>TOTAL VECTOR POINTS</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>{stats.points_count}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Large Premium Search Control */}
      <div className="panel" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center' }}>
        <form onSubmit={handleVectorSearch} style={{ width: '100%', maxWidth: '750px', display: 'flex', gap: '12px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={20} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input 
              type="text" 
              placeholder="Query vectorized document corpus (e.g. What is our retry budget or backpressure rules?)..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading || ragLoading}
              style={{
                width: '100%',
                padding: '16px 16px 16px 48px',
                borderRadius: '4px',
                border: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.02)',
                color: '#fff',
                fontSize: '1rem',
                outline: 'none',
                boxShadow: 'none',
                transition: 'all 0.2s ease',
              }}
              className="search-input-focus"
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              type="submit" 
              disabled={loading || ragLoading || !query.trim()}
              className="btn btn-primary"
              style={{
                borderRadius: '4px',
                padding: '0 24px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--color-accent)',
                boxShadow: 'none'
              }}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              Search Vectors
            </button>

            <button 
              type="button"
              onClick={handleRagQuery}
              disabled={loading || ragLoading || !query.trim()}
              className="btn"
              style={{
                borderRadius: '4px',
                padding: '0 24px',
                fontWeight: 700,
                color: '#fff',
                background: 'linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%)',
                boxShadow: 'none',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: (loading || ragLoading || !query.trim()) ? 'not-allowed' : 'pointer'
              }}
            >
              {ragLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Execute RAG
            </button>
          </div>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#cbd5e1' }}>
          <span>Limit Results (Top K):</span>
          <select 
            value={topK} 
            onChange={(e) => setTopK(Number(e.target.value))}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#fff',
              padding: '4px 8px',
              borderRadius: '6px',
              outline: 'none'
            }}
          >
            <option value={3}>3 Chunks</option>
            <option value={5}>5 Chunks</option>
            <option value={10}>10 Chunks</option>
          </select>
        </div>
      </div>

      {/* Interactive Query Execution Flowchart */}
      <div className="panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1rem', margin: '0 0 16px 0', color: '#fff' }}>Vector Query Execution Path</h2>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <div className={`flow-step-node ${currentStep ? 'completed' : ''}`} style={{ flex: 1, minWidth: '130px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>STAGE 1</div>
            <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 700, marginTop: '4px' }}>Query Ingestion</div>
          </div>
          
          <div style={{ color: '#475569', fontSize: '1.25rem' }}>→</div>

          <div className={`flow-step-node ${currentStep === 'embed' ? 'active' : ['search', 'synthesize', 'done'].includes(currentStep) ? 'completed' : ''}`} style={{ flex: 1, minWidth: '130px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>STAGE 2</div>
            <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 700, marginTop: '4px' }}>Dense Embedding</div>
          </div>

          <div style={{ color: '#475569', fontSize: '1.25rem' }}>→</div>

          <div className={`flow-step-node ${currentStep === 'search' ? 'active' : ['synthesize', 'done'].includes(currentStep) ? 'completed' : ''}`} style={{ flex: 1, minWidth: '130px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>STAGE 3</div>
            <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 700, marginTop: '4px' }}>Qdrant Vector Scan</div>
          </div>

          <div style={{ color: '#475569', fontSize: '1.25rem' }}>→</div>

          <div className={`flow-step-node ${currentStep === 'synthesize' ? 'active' : currentStep === 'done' && ragAnswer ? 'completed' : ''}`} style={{ flex: 1, minWidth: '130px', textAlign: 'center', opacity: ragLoading || ragAnswer ? 1 : 0.4 }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>STAGE 4</div>
            <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 700, marginTop: '4px' }}>RAG Synthesis</div>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert-banner error" style={{ margin: 0 }}>
          <span>❌ Error running vector query: {error}</span>
        </div>
      )}

      {/* RAG Synthesis Result Card */}
      {ragAnswer && (
        <div className="panel" style={{ borderLeft: '4px solid #a78bfa', background: 'rgba(167, 139, 250, 0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Sparkles size={20} style={{ color: '#a78bfa' }} />
            <h2 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700, color: '#fff' }}>Synthesized RAG Answer</h2>
          </div>
          <div style={{ fontSize: '1rem', color: '#cbd5e1', lineHeight: 1.6, whiteSpace: 'pre-wrap', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.04)' }}>
            {ragAnswer.final_answer?.answer || ragAnswer.answer}
          </div>
          <div style={{ display: 'flex', gap: '16px', marginTop: '12px', fontSize: '0.75rem', color: '#94a3b8' }}>
            <span>Pipeline: #{ragAnswer.pipeline_id}</span>
            <span>Status: {ragAnswer.status}</span>
            <span>Duration: {ragAnswer.elapsed_seconds ? `${ragAnswer.elapsed_seconds.toFixed(2)}s` : 'N/A'}</span>
          </div>
        </div>
      )}

      {/* Results Section */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px', color: '#fff' }}>
          {results.length > 0 ? `Vector Search Match Results (${results.length})` : 'Search Match Results'}
        </h2>

        {results.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }} className="panel">
            {loading || ragLoading ? 'Executing query against indices...' : 'Enter a search query or run a RAG execution to display matched document chunks.'}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {results.map((hit, idx) => {
              // Similarity score in percentage
              const similarityPct = Math.round((hit.score || 0) * 100);

              return (
                <div key={idx} className="panel" style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  
                  {/* Top Header info */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <FileText size={16} style={{ color: '#5B8CFF' }} />
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>
                        {hit.original_filename || 'Unknown Document Citation'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {hit.rerank_score !== undefined && hit.rerank_score !== null && (
                        <>
                          <span style={{ fontSize: '0.75rem', color: '#a78bfa', fontWeight: 600 }}>Rerank Score:</span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#a78bfa', marginRight: '12px' }}>
                            {typeof hit.rerank_score === 'number' ? hit.rerank_score.toFixed(4) : hit.rerank_score}
                          </span>
                        </>
                      )}
                      <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>Similarity Score:</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div className="progress-bar-outer" style={{ width: '80px', height: '6px', margin: 0 }}>
                          <div 
                            className="progress-bar-inner" 
                            style={{ 
                              width: `${similarityPct}%`, 
                              backgroundColor: similarityPct > 80 ? '#10B981' : similarityPct > 60 ? '#5B8CFF' : '#F59E0B',
                              height: '6px'
                            }} 
                          />
                        </div>
                        <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>{similarityPct}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Chunk text content */}
                  <div style={{ 
                    fontSize: '0.85rem', 
                    color: '#94a3b8', 
                    background: 'rgba(0,0,0,0.2)', 
                    padding: '12px', 
                    borderRadius: '6px', 
                    border: '1px solid rgba(255,255,255,0.03)',
                    lineHeight: 1.5,
                    fontFamily: 'monospace'
                  }}>
                    {hit.chunk_text}
                  </div>

                  {/* Footer metadata */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '0.7rem', color: '#64748b', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '8px' }}>
                    <span>Pipeline ID: #{hit.pipeline_id}</span>
                    <span>Task ID: #{hit.task_id}</span>
                    <span>Chunk Index: {hit.chunk_index}</span>
                  </div>

                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
};

export default VectorSearchPage;
