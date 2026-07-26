import React from 'react';
import { Cpu, Database, Server } from 'lucide-react';

export const RuntimeMetrics = ({ queuePosition, workerId, pipelineId, taskId, cpu, ram, retries, currentStage, duration, eta, redisQueue, coordinator }) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-14)',
        padding: 'var(--spacing-20)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--spacing-16)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <h3 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-primary)', margin: 0 }}>
        Pipeline Runtime Metrics
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        
        {/* Resource Allocation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            <Cpu size={14} style={{ color: 'var(--color-accent)' }} />
            <span>CPU / RAM Alloc</span>
          </div>
          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
            {cpu || '0.2'} cores / {ram || '1.8'} GB
          </span>
        </div>

        {/* Redis & Broker Queue details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            <Database size={14} style={{ color: 'var(--color-success)' }} />
            <span>Redis Queue Size</span>
          </div>
          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
            {redisQueue || '0'} tasks queued
          </span>
        </div>

        {/* Active Stage & Worker ID */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            <Server size={14} style={{ color: 'var(--color-accent)' }} />
            <span>Broker Coordinator</span>
          </div>
          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'bold', fontFamily: 'var(--font-mono)', color: coordinator === 'Healthy' ? 'var(--color-success)' : 'var(--text-primary)' }}>
            {coordinator || 'Active'}
          </span>
        </div>

        {/* retries */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            <ActivityIcon size={14} />
            <span>Pipeline Failures</span>
          </div>
          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'bold', fontFamily: 'var(--font-mono)', color: retries > 0 ? 'var(--color-failure)' : 'var(--text-primary)' }}>
            {retries || 0} retries
          </span>
        </div>

      </div>
    </div>
  );
};

const ActivityIcon = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </svg>
);

export default RuntimeMetrics;
