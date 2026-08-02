import React from 'react';

/**
 * Reusable horizontal/vertical progress tracker.
 * Steps: Upload, OCR / VLM, Layout Graph, Chunking, Embedding, Indexing, Ready
 */
export const PipelineStepper = ({ 
  steps = [
    { id: 'upload', label: 'Upload', status: 'completed' },
    { id: 'ocr', label: 'OCR / VLM', status: 'completed' },
    { id: 'layout', label: 'Layout Graph', status: 'running' },
    { id: 'chunking', label: 'Chunking', status: 'pending' },
    { id: 'embedding', label: 'Embedding', status: 'pending' },
    { id: 'indexing', label: 'Indexing', status: 'pending' },
    { id: 'ready', label: 'Ready', status: 'pending' }
  ] 
}) => {
  return (
    <div className="pipeline-stepper-container" role="progressbar" aria-label="Pipeline Steps Status">
      {steps.map((step, idx) => (
        <div 
          key={step.id} 
          className={`pipeline-stepper-step ${step.status}`}
          aria-current={step.status === 'running' ? 'step' : undefined}
        >
          <div className="pipeline-stepper-node" title={`${step.label}: ${step.status}`}>
            {step.status === 'completed' && '✓'}
            {step.status === 'running' && '●'}
            {step.status === 'failed' && '✕'}
            {step.status === 'pending' && idx + 1}
          </div>
          <span className="pipeline-stepper-label">{step.label}</span>
        </div>
      ))}
    </div>
  );
};

export default PipelineStepper;
