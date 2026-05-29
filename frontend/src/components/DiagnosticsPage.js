import React, { useState, useEffect } from 'react';
import { AlertTriangle, Activity, Database, Loader2, RefreshCw } from 'lucide-react';
import { fetchTasks } from '../services/api';

const DiagnosticsPage = () => {
  const [diagnostics, setDiagnostics] = useState(null);
  const [dlqTasks, setDlqTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      setRefreshing(true);
      // Fetch diagnostics from API
      // Since it's a new endpoint, we use raw fetch for simplicity
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const API_KEY = process.env.REACT_APP_API_KEY || 'dev_secret_api_key';
      
      const diagRes = await fetch(`${API_URL}/diagnostics`, {
        headers: { 'X-API-Key': API_KEY }
      });
      if (diagRes.ok) {
        setDiagnostics(await diagRes.json());
      }
      
      const tasksData = await fetchTasks(1, 100);
      if (tasksData && tasksData.tasks) {
        setDlqTasks(tasksData.tasks.filter(t => t.status === 'failed'));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <Loader2 className="spinning" size={48} style={{ color: '#5B8CFF', marginBottom: '20px' }} />
        <h3>Loading Diagnostics...</h3>
      </div>
    );
  }

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>System Diagnostics & DLQ</h2>
          <p>Real-time metrics and Dead-Letter Queue (quarantined tasks).</p>
        </div>
        <button className="primary-btn" onClick={loadData} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spinning" : ""} /> Refresh
        </button>
      </div>

      <div className="overview-hero" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="hero-metric-card">
          <span className="hero-metric-label">CPU Utilization</span>
          <span className="hero-metric-value">{diagnostics?.cpu_utilization_percent || 0}%</span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">RAM Utilization</span>
          <span className="hero-metric-value">{diagnostics?.ram_utilization_percent || 0}%</span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Active Workers</span>
          <span className="hero-metric-value">{diagnostics?.active_workers || 0}</span>
        </div>
        <div className="hero-metric-card" style={{ borderLeft: '4px solid #F87171' }}>
          <span className="hero-metric-label">Dead-Letter Queue</span>
          <span className="hero-metric-value" style={{ color: '#F87171' }}>{diagnostics?.dlq_count || 0}</span>
        </div>
      </div>

      <div className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-header">
          <h3><AlertTriangle size={18} color="#F87171" style={{ marginRight: '8px', verticalAlign: 'text-bottom' }}/> Dead-Letter Queue Tasks</h3>
        </div>
        <div className="panel-content">
          {dlqTasks.length === 0 ? (
            <div className="empty-state" style={{ padding: '40px 0' }}>
              <div style={{ color: '#10B981', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Activity size={48} style={{ marginBottom: '16px' }} />
                <h3>DLQ is Empty</h3>
                <p>No failed tasks detected.</p>
              </div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Task ID</th>
                  <th>Type</th>
                  <th>Priority</th>
                  <th>Error Traceback</th>
                  <th>Created At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {dlqTasks.map(task => (
                  <tr key={task.id}>
                    <td>#{task.id}</td>
                    <td>{task.type}</td>
                    <td><span className={`badge ${task.priority}`}>{task.priority}</span></td>
                    <td style={{ maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#F87171', fontFamily: 'monospace' }}>
                      {task.error_message || 'Unknown Error'}
                    </td>
                    <td>{new Date(task.created_at).toLocaleString([], { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                    <td>
                      <span className="badge failed">Quarantined</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      {diagnostics?.queue_depths && (
        <div className="panel" style={{ marginTop: '24px' }}>
          <div className="panel-header">
            <h3><Database size={18} style={{ marginRight: '8px', verticalAlign: 'text-bottom' }}/> Queue Depths (Redis)</h3>
          </div>
          <div className="panel-content">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {Object.entries(diagnostics.queue_depths).map(([q, depth]) => (
                <div key={q} style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px', wordBreak: 'break-all' }}>{q}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: '600', color: depth > 0 ? '#3b82f6' : '#94a3b8' }}>{depth}</div>
                </div>
              ))}
              {Object.keys(diagnostics.queue_depths).length === 0 && (
                <div style={{ color: '#64748b' }}>No active queues found via /diagnostics.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DiagnosticsPage;