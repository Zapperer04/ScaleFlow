import React from 'react';
import { Cpu, Server, Database, RefreshCw, AlertTriangle, ShieldAlert } from 'lucide-react';
import { useTelemetry } from '../services/telemetryStore';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

export const SystemInfrastructure = () => {
  const workers = useTelemetry(s => s.workers);
  const queueStats = useTelemetry(s => s.queueStats);
  const redisStatus = useTelemetry(s => s.redisStatus);
  const dbStatus = useTelemetry(s => s.dbStatus);
  const qdrantStatus = useTelemetry(s => s.qdrantStatus);
  const leaderId = useTelemetry(s => s.leaderId);

  const activeWorkers = workers.filter(w => w.status !== 'offline');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>System Infrastructure Operations</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Monitor task queues, Redis brokers, database connections, and active worker node registers.</p>
      </div>

      {/* Database/Broker States */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '220px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Database size={32} style={{ color: 'var(--color-accent)' }} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>REDIS BROKER</div>
            <div style={{ fontWeight: 'bold', fontSize: '1rem', marginTop: '2px' }}>{redisStatus ? 'Connected' : 'Offline'}</div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Port: 6379</span>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '220px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Database size={32} style={{ color: 'var(--color-accent)' }} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>POSTGRES METADATA</div>
            <div style={{ fontWeight: 'bold', fontSize: '1rem', marginTop: '2px' }}>{dbStatus ? 'Connected' : 'Offline'}</div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Port: 5432</span>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '220px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Database size={32} style={{ color: 'var(--color-accent)' }} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>QDRANT VECTOR STORE</div>
            <div style={{ fontWeight: 'bold', fontSize: '1rem', marginTop: '2px' }}>{qdrantStatus ? 'Connected' : 'Offline'}</div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Port: 6333</span>
          </div>
        </div>
      </div>

      {/* Workers and backpressure */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        
        {/* Workers Panel */}
        <div style={{ flex: 2, minWidth: '320px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)' }}>Active Workers ({activeWorkers.length})</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {workers.map((worker, idx) => (
              <div 
                key={idx}
                style={{
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Server size={16} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{worker.id}</span>
                    <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Tasks: {worker.current_task_type || 'Idle'}</span>
                  </div>
                </div>
                <Badge variant={worker.status === 'offline' ? 'failure' : 'success'}>
                  {worker.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Queue Backpressure */}
        <div style={{ flex: 1, minWidth: '220px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)' }}>Queue Backlog</h3>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Tasks waiting in Redis priority lanes.</p>
          </div>

          <div style={{ margin: '20px 0', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-accent)' }}>
              {queueStats.total || 0}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-disabled)' }}>Total Queued Tasks</span>
          </div>

          <div style={{ fontSize: '0.7rem', color: 'var(--text-disabled)', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
            Leader Orchestrator ID: <code style={{ color: 'var(--text-primary)' }}>{leaderId || 'orchestrator_1'}</code>
          </div>
        </div>

      </div>

    </div>
  );
};

export default SystemInfrastructure;
