import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, Cpu, Database, Zap, TrendingUp, Layers, Server, Clock } from 'lucide-react';
import { fetchTasks, fetchWorkers, getQueueStats, runIntegrationTests } from './services/api';
import MetricCard from './components/MetricCard';
import TaskForm from './components/TaskForm';
import TaskLog from './components/TaskLog';
import WorkerStatus from './components/WorkerStatus';
import QueueStats from './components/QueueStats';
import TaskModal from './components/TaskModal';
import { ThroughputChart, WorkerLoadChart } from './components/Charts';
import PipelineDashboard from './components/PipelineDashboard';
import './App.css';

const POLL_INTERVAL = parseInt(process.env.REACT_APP_POLL_INTERVAL_MS || "3000");

function App() {
  const [tasks, setTasks] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [queueStats, setQueueStats] = useState({});
  const [stats, setStats] = useState({ total: 0, pending: 0, running: 0, completed: 0 });
  const [throughput, setThroughput] = useState([]);
  const [workerDistribution, setWorkerDistribution] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const queueStuckSinceRef = useRef(null);
  const [showStuckWarning, setShowStuckWarning] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [testing, setTesting] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testResults, setTestResults] = useState(null);

  const handleRunTests = async () => {
    setTesting(true);
    setTestResults(null);
    setShowTestModal(false);
    try {
      const data = await runIntegrationTests();
      setTestResults(data);
      setShowTestModal(true);
      loadData();
    } catch (err) {
      setTestResults({
        status: 'failed',
        logs: ['Integration test execution failed.'],
        error: err.response?.data || err.message
      });
      setShowTestModal(true);
    } finally {
      setTesting(false);
    }
  };

  const loadData = useCallback(async () => {
    try {
      const page1Data = await fetchTasks(1, 50);
      const page1Tasks = page1Data.tasks || [];
      const metadata = page1Data.metadata || { total_tasks: 0, total_pages: 1 };
      
      let logTasks = page1Tasks;
      let logTotalPages = metadata.total_pages || 1;
      
      if (page > 1) {
        const currentPageData = await fetchTasks(page, 50);
        logTasks = currentPageData.tasks || [];
        logTotalPages = currentPageData.metadata?.total_pages || 1;
      }
      
      setTasks(logTasks);
      setTotalPages(logTotalPages);

      if (page > logTotalPages && logTotalPages > 0) {
        setPage(logTotalPages);
      }

      const workersData = await fetchWorkers();
      const defaultWorkerIds = ['worker-1', 'worker-2', 'worker-3'];
      const mergedWorkers = defaultWorkerIds.map(id => {
        const active = workersData.find(w => w.worker_id === id);
        if (active) {
          const secondsSinceLastSeen = (Date.now() - new Date(active.last_seen)) / 1000;
          const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : active.status;
          return { ...active, status: computedStatus };
        }
        return {
          worker_id: id,
          status: 'offline',
          last_seen: null,
          tasks_completed: 0,
          tasks_failed: 0,
          last_action: 'Offline'
        };
      });
      
      workersData.forEach(w => {
        if (!defaultWorkerIds.includes(w.worker_id)) {
          const secondsSinceLastSeen = (Date.now() - new Date(w.last_seen)) / 1000;
          const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : w.status;
          mergedWorkers.push({ ...w, status: computedStatus });
        }
      });
      setWorkers(mergedWorkers);

      const qs = await getQueueStats();
      setQueueStats(qs);

      // Check if queue is stuck
      const totalQueued = qs.total || 0;
      const allWorkersIdle = mergedWorkers.length > 0 && mergedWorkers.every(w => w.status === 'idle' || w.status === 'offline');
      
      if (totalQueued > 0 && allWorkersIdle) {
        if (queueStuckSinceRef.current === null) {
          queueStuckSinceRef.current = Date.now();
        } else if (Date.now() - queueStuckSinceRef.current > 10000) {
          setShowStuckWarning(true);
        }
      } else {
        queueStuckSinceRef.current = null;
        setShowStuckWarning(false);
      }

      setStats({
        total: metadata.total_tasks,
        pending: page1Tasks.filter(t => t.status === 'pending').length,
        running: page1Tasks.filter(t => t.status === 'running').length,
        completed: page1Tasks.filter(t => t.status === 'completed').length
      });

      const throughputData = page1Tasks.slice(0, 20).reverse().reduce((acc, task, idx) => {
        const bucket = Math.floor(idx / 4);
        if (!acc[bucket]) acc[bucket] = { name: `T${bucket}`, count: 0 };
        if (task.status === 'completed') acc[bucket].count++;
        return acc;
      }, []).filter(Boolean);
      setThroughput(throughputData);

      setWorkerDistribution([
        { name: 'Worker 1', value: page1Tasks.filter((t, i) => i % 3 === 0 && t.status === 'completed').length },
        { name: 'Worker 2', value: page1Tasks.filter((t, i) => i % 3 === 1 && t.status === 'completed').length },
        { name: 'Worker 3', value: page1Tasks.filter((t, i) => i % 3 === 2 && t.status === 'completed').length },
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }, [page]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [loadData]);

  const getActivityText = () => {
    if (showStuckWarning) {
      return "Queue has tasks but no worker has picked them";
    }
    const busyWorker = workers.find(w => w.status === 'busy');
    if (busyWorker) {
      return `${busyWorker.worker_id} processing task #${busyWorker.current_task_id}`;
    }
    if (workers.some(w => w.status === 'idle')) {
      return "Workers are waiting for tasks";
    }
    return "All workers are offline";
  };

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-content">
          <div className="nav-brand">
            <div className="brand-icon">
              <Layers size={28} strokeWidth={2.5} />
            </div>
            <div className="brand-text">
              <span className="brand-name">ScaleFlow</span>
              <span className="brand-tagline">Distributed Task Execution Engine</span>
            </div>
          </div>
          <div className="nav-stats">
            <div className="nav-stat">
              <Server size={16} />
              <span>{workers.filter(w => w.status !== 'offline').length} Workers Active</span>
            </div>
            <div className="nav-stat">
              <Database size={16} />
              <span>PostgreSQL</span>
            </div>
            <div className="nav-stat">
              <Zap size={16} />
              <span>Redis Queue</span>
            </div>
          </div>
          <button 
            onClick={handleRunTests}
            disabled={testing}
            style={{
              background: testing ? 'rgba(59, 130, 246, 0.2)' : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: testing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)',
              transition: 'all 0.2s ease',
              marginLeft: '16px'
            }}
          >
            {testing ? 'Running Tests...' : 'Run System Tests'}
          </button>
        </div>
      </nav>

      <div className="container">
        {showStuckWarning && (
          <div className="alert-banner warning">
            <span className="alert-icon">⚠</span>
            <span className="alert-message">Tasks are queued but no worker is processing them. Check worker logs or Redis consumer loop.</span>
          </div>
        )}

        <div className="activity-banner">
          <div className={`activity-pulse ${workers.some(w => w.status === 'busy') ? 'busy' : showStuckWarning ? 'stuck' : workers.some(w => w.status === 'idle') ? 'idle' : 'offline'}`} />
          <span className="activity-text">{getActivityText()}</span>
        </div>

        <div className="metrics-grid">
          <MetricCard icon={Activity} label="Total Tasks" value={stats.total} trend={stats.total > 0 ? 12 : 0} color="rgba(139, 92, 246, 0.2)" gradient="linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)" />
          <MetricCard icon={Clock} label="Recent Pending" value={stats.pending} color="rgba(251, 191, 36, 0.2)" gradient="linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(251, 191, 36, 0.05) 100%)" />
          <MetricCard icon={Cpu} label="Recent Executing" value={stats.running} color="rgba(59, 130, 246, 0.2)" gradient="linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%)" />
          <MetricCard icon={TrendingUp} label="Recent Completed" value={stats.completed} trend={stats.completed > 0 ? 8 : 0} color="rgba(16, 185, 129, 0.2)" gradient="linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%)" />
        </div>

        <div className="dashboard-grid">
          <QueueStats stats={queueStats} />
          <WorkerStatus workers={workers} />
          <ThroughputChart throughput={throughput} />
          <WorkerLoadChart workerDistribution={workerDistribution} />
          <TaskForm onTaskCreated={loadData} />
          <TaskLog 
            tasks={tasks} 
            workers={workers} 
            onTaskClick={setSelectedTaskId} 
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
        <PipelineDashboard />
      </div>
      
      <TaskModal 
        taskId={selectedTaskId} 
        onClose={() => setSelectedTaskId(null)} 
        onActionComplete={loadData} 
      />

      {showTestModal && testResults && (
        <div className="modal-overlay" onClick={() => setShowTestModal(false)} style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '16px',
            width: '90%',
            maxWidth: '650px',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4)',
            color: '#f8fafc'
          }}>
            <div className="modal-header" style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              borderBottom: '1px solid #334155'
            }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  background: testResults.status === 'success' ? '#10b981' : '#ef4444',
                  color: '#ffffff',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  fontWeight: 'bold'
                }}>
                  {testResults.status}
                </span>
                System Integration Test Results
              </h2>
              <button 
                onClick={() => setShowTestModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '1.25rem',
                  lineHeight: '1',
                  padding: '4px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body" style={{
              padding: '24px',
              overflowY: 'auto',
              flex: 1,
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              background: '#0f172a'
            }}>
              {testResults.logs && testResults.logs.map((log, index) => {
                let color = '#cbd5e1';
                if (log.includes('--- Test')) color = '#3b82f6';
                if (log.includes('successfully') || log.includes('passed')) color = '#10b981';
                if (log.includes('Failed') || log.includes('rejected') || log.includes('error')) color = '#fb7185';
                
                return (
                  <div key={index} style={{ color, marginBottom: '6px', whiteSpace: 'pre-wrap' }}>
                    {log}
                  </div>
                );
              })}
              {testResults.error && (
                <div style={{ color: '#ef4444', marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <strong>Error:</strong> {JSON.stringify(testResults.error, null, 2)}
                </div>
              )}
            </div>
            <div className="modal-footer" style={{
              padding: '16px 24px',
              borderTop: '1px solid #334155',
              display: 'flex',
              justifyContent: 'flex-end'
            }}>
              <button 
                onClick={() => setShowTestModal(false)}
                style={{
                  background: '#334155',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 20px',
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;