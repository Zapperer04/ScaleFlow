import { useState } from 'react';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { createRetrievalPipeline, fetchRetrievalPipelineAnswer } from '../../../services/api';

/**
 * Custom hook to execute RAG retrieval search queries and poll for synthesis results.
 */
export const useSearch = () => {
  const { selectedDocId } = useWorkspace();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [results, setResults] = useState([]);

  const executeSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    setResults([]);

    try {
      const payload = { query: query.trim(), top_k: 8 };
      if (selectedDocId) {
        payload.pipeline_id = selectedDocId;
      }

      // 1. Create retrieval pipeline
      const res = await createRetrievalPipeline(payload);
      const queryPipelineId = res.pipeline_id;
      const startTime = Date.now();

      // 2. Poll answer (up to 180 seconds)
      let attempts = 0;
      let data = null;
      while (attempts < 180) {
        await new Promise(r => setTimeout(r, 1000));
        data = await fetchRetrievalPipelineAnswer(queryPipelineId);
        
        const hasAnswer = data?.final_answer?.answer || data?.answer;
        if (data && (hasAnswer || data.status === 'failed')) {
          break;
        }
        attempts++;
      }

      if (data && data.status === 'failed') {
        throw new Error(data.error || 'RAG generation failed.');
      }

      // 3. Normalize answer data schema
      const fa = data?.final_answer;
      const normalizedAnswer = {
        answer: fa?.answer || data?.answer || 'No answer could be generated.',
        confidence: fa?.confidence || data?.confidence || 'low',
        citations: fa?.citations || fa?.sources || data?.sources || [],
        pipeline_id: data?.pipeline_id,
        elapsed_seconds: (Date.now() - startTime) / 1000
      };

      setAnswer(normalizedAnswer);
      setResults(data?.retrieved_context?.results || data?.retrieved_chunks || []);
    } catch (err) {
      console.error('RAG query failed:', err);
      setError(err.message || 'Retrieval failed. Please verify cluster connection.');
    } finally {
      setLoading(false);
    }
  };

  return {
    query,
    setQuery,
    loading,
    error,
    answer,
    results,
    executeSearch
  };
};
export default useSearch;
