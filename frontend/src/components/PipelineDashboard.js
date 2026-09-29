import React, { useEffect, useState } from 'react';
import { usePipeline } from '../contexts/PipelineContext';
import PipelineVisualizer from './workspace/pipeline/PipelineVisualizer';
import { fetchPipelineDetails } from '../services/pipelines';
import { getPipelineMetrics } from '../services/diagnostics';
import { Loader2 } from 'lucide-react';

const PipelineDashboard = () => {
  const { selectedPipelineId, onRetryTask } = usePipeline();
  const [pipelineData, setPipelineData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedPipelineId) return;
    setPipelineData(null);
    setMetricsData(null);
    
    let isMounted = true;
    let timerId = null;
    
    const load = async () => {
      setLoading(true);
      let currentStatus = 'running';
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        let metrics = null;
        try {
          metrics = await getPipelineMetrics(selectedPipelineId);
        } catch (e) {
          console.warn('Failed to load metrics', e);
        }
        if (isMounted) {
          setPipelineData(details);
          setMetricsData(metrics);
          currentStatus = details?.pipeline?.status || 'running';
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
      
      // Stop polling if completed or failed
      if (isMounted && currentStatus !== 'completed' && currentStatus !== 'failed') {
        timerId = setTimeout(load, 3000);
      }
    };
    
    load();
    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [selectedPipelineId]);

  if (loading && !pipelineData) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100%', alignItems: 'center', justifyContent: 'center', background: '#0a0a0f', color: '#64748b' }}>
        <Loader2 className="animate-spin" size={24} style={{ marginRight: '8px' }} />
        Loading pipeline details...
      </div>
    );
  }

  if (!selectedPipelineId || !pipelineData) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100%', alignItems: 'center', justifyContent: 'center', background: '#0a0a0f', color: '#64748b' }}>
        Select a pipeline from the dashboard to inspect.
      </div>
    );
  }

  return <PipelineVisualizer tasks={pipelineData.tasks} pipelineStatus={pipelineData.pipeline?.status} metrics={metricsData} onRetryTask={onRetryTask} />;
};

export default PipelineDashboard;
