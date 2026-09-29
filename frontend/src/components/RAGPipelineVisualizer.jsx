import React, { useMemo } from 'react';
import { CheckCircle, Clock, Server, Layers, Search, FileText, Activity, AlertTriangle, PlayCircle } from 'lucide-react';
import './RAGPipelineVisualizer.css';

const RAG_STAGES = [
  { id: 'parse_document', label: 'Document Parsing', icon: FileText, description: 'Extracting raw text & metadata' },
  { id: 'layout_analysis', label: 'Layout Analysis', icon: Layers, description: 'Detecting tables, headers & sections' },
  { id: 'chunk_text', label: 'Semantic Chunking', icon: Activity, description: 'Splitting into context-aware chunks' },
  { id: 'generate_embeddings', label: 'Vector Embeddings', icon: Server, description: 'Converting text to dense vectors' },
  { id: 'summarize_document', label: 'Knowledge Indexing', icon: Search, description: 'Finalizing retrieval indexes' }
];

const RAGPipelineVisualizer = ({ pipelineData }) => {
  const { pipeline, tasks } = pipelineData || {};

  // Group tasks by their type to map them to the linear RAG stages
  const taskMap = useMemo(() => {
    if (!tasks) return {};
    const map = {};
    tasks.forEach(t => {
      map[t.task_type] = t;
    });
    return map;
  }, [tasks]);

  if (!pipeline) {
    return <div className="rag-empty-state">No pipeline selected.</div>;
  }

  // Calculate overall pipeline progress
  const totalStages = RAG_STAGES.length;
  let completedStages = 0;
  let activeStageId = null;

  RAG_STAGES.forEach(stage => {
    const task = taskMap[stage.id];
    if (task?.status === 'completed') {
      completedStages++;
    } else if (task?.status === 'running' || task?.status === 'pending' || task?.status === 'failed' || task?.status === 'blocked') {
      if (!activeStageId) activeStageId = stage.id;
    }
  });

  const progressPercent = Math.round((completedStages / totalStages) * 100);

  return (
    <div className="rag-visualizer-container">
      <div className="rag-header-panel">
        <div className="rag-header-content">
          <h2 className="rag-title">
            Document Ingestion Journey
            <span className={`rag-status-badge ${pipeline.status}`}>{pipeline.status}</span>
          </h2>
          <p className="rag-subtitle">Tracking vector embedding & semantic chunking</p>
        </div>
        <div className="rag-progress-circle">
          <svg viewBox="0 0 36 36" className="circular-chart">
            <path className="circle-bg"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path className="circle"
              strokeDasharray={`${progressPercent}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <text x="18" y="20.35" className="percentage">{progressPercent}%</text>
          </svg>
        </div>
      </div>

      <div className="rag-timeline-wrapper">
        <div className="rag-timeline-track"></div>
        {RAG_STAGES.map((stage, index) => {
          const task = taskMap[stage.id];
          const isCompleted = task?.status === 'completed';
          const isRunning = task?.status === 'running';
          const isFailed = task?.status === 'failed' || task?.status === 'blocked';
          const isPending = !task || task.status === 'pending';
          const isNextPending = activeStageId === stage.id && !isRunning;

          let nodeClass = 'rag-node ';
          if (isCompleted) nodeClass += 'completed';
          else if (isRunning) nodeClass += 'running pulse-glow';
          else if (isFailed) nodeClass += 'failed';
          else if (isNextPending) nodeClass += 'next-pending';
          else nodeClass += 'pending';

          const Icon = stage.icon;

          return (
            <div key={stage.id} className="rag-timeline-item">
              <div className="rag-connection-line">
                <div className={`rag-connection-fill ${isCompleted ? 'filled' : (isRunning ? 'filling' : '')}`}></div>
              </div>
              
              <div className={nodeClass}>
                <div className="rag-node-icon">
                  {isCompleted ? <CheckCircle size={24} /> : (isFailed ? <AlertTriangle size={24} /> : <Icon size={24} />)}
                </div>
                
                <div className="rag-node-content">
                  <h4 className="rag-node-title">{stage.label}</h4>
                  <p className="rag-node-desc">{stage.description}</p>
                  
                  {task && (
                    <div className="rag-node-metrics">
                      {isRunning && <span className="rag-running-text"><PlayCircle size={12} className="spin" /> Processing...</span>}
                      {task.execution_duration > 0 && <span className="rag-time"><Clock size={12} /> {task.execution_duration}s</span>}
                      {task.assigned_worker_id && <span className="rag-worker"><Server size={12} /> {task.assigned_worker_id.split('-').pop()}</span>}
                    </div>
                  )}
                  {isFailed && <div className="rag-error-msg">{task?.error_message || task?.blocked_reason || 'Task Blocked'}</div>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RAGPipelineVisualizer;
