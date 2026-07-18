import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, Zap, Play, Terminal, RefreshCw, AlertTriangle, CheckCircle, 
  Database, Cpu, Activity, PlayCircle, ToggleLeft, Server, AlertCircle, ArrowRight, Search
} from 'lucide-react';
import { 
  fetchValidationStatus, killWorker, startWorker, pauseQueue, resumeQueue, 
  fetchPausedQueues, triggerLeaseExpiry, triggerManualRecovery, injectBurstLoad, 
  triggerBackpressure, triggerOrchestratorFailover, runSubprocessTest, 
  fetchSubprocessTestStatus, createPipeline
} from '../services/api';

export default function ValidationLab() {
  const [activeTab, setActiveTab] = useState('center'); // 'center', 'chaos', 'templates', 'results'
  
  // Validation Center States
  const [validationItems, setValidationItems] = useState({});
  const [loadingValidation, setLoadingValidation] = useState(false);

  // Chaos Lab States
  const [selectedWorker, setSelectedWorker] = useState('worker-1');
  const [selectedQueue, setSelectedQueue] = useState('task_queue_medium');
  const [pausedQueues, setPausedQueues] = useState([]);
  const [backpressureForced, setBackpressureForced] = useState(false);
  const [chaosLog, setChaosLog] = useState([]);

  // Subprocess Test Runner States
  const [selectedTest, setSelectedTest] = useState('validation'); // 'validation', 'stress', 'ha'
  const [testStatus, setTestStatus] = useState('idle');
  const [testLogs, setTestLogs] = useState([]);
  const [isRunningTest, setIsRunningTest] = useState(false);
  
  const terminalEndRef = useRef(null);

  // Load Initial Validation and Paused Queues
  const loadValidation = async () => {
    setLoadingValidation(true);
    try {
      const data = await fetchValidationStatus();
      setValidationItems(data);
    } catch (err) {
      console.error('Failed to fetch validation check:', err);
    } finally {
      setLoadingValidation(false);
    }
  };

  const loadPausedQueues = async () => {
    try {
      const data = await fetchPausedQueues();
      setPausedQueues(data);
    } catch (err) {
      console.error('Failed to load paused queues:', err);
    }
  };

  useEffect(() => {
    loadValidation();
    loadPausedQueues();
  }, []);

  // Poll Test status when running
  useEffect(() => {
    let intervalId;
    if (isRunningTest) {
      const pollTest = async () => {
        try {
          const data = await fetchSubprocessTestStatus(selectedTest);
          setTestStatus(data.status);
          setTestLogs(data.logs || []);
          if (data.status !== 'running') {
            setIsRunningTest(false);
            loadValidation(); // reload system status after test runs
          }
        } catch (err) {
          console.error('Error polling test status:', err);
        }
      };
      
      intervalId = setInterval(pollTest, 2000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRunningTest, selectedTest]);

  // Scroll terminal logs to bottom
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [testLogs]);

  // Helper to add log to Chaos Console
  const addChaosLog = (msg) => {
    const timestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setChaosLog(prev => [`[${timestamp}] ${msg}`, ...prev].slice(0, 50));
  };

  // Chaos Actions
  const handleKillWorker = async () => {
    try {
      addChaosLog(`Killing container for worker node '${selectedWorker}'...`);
      await killWorker(selectedWorker);
      addChaosLog(`SUCCESS: Stopped worker '${selectedWorker}'.`);
      setTimeout(loadValidation, 2000);
    } catch (err) {
      addChaosLog(`ERROR: Failed to stop worker: ${err.message}`);
    }
  };

  const handleStartWorker = async () => {
    try {
      addChaosLog(`Rebooting container for worker node '${selectedWorker}'...`);
      await startWorker(selectedWorker);
      addChaosLog(`SUCCESS: Started worker '${selectedWorker}'.`);
      setTimeout(loadValidation, 2000);
    } catch (err) {
      addChaosLog(`ERROR: Failed to start worker: ${err.message}`);
    }
  };

  const handlePauseQueue = async () => {
    try {
      addChaosLog(`Pausing task polling on queue '${selectedQueue}'...`);
      await pauseQueue(selectedQueue);
      addChaosLog(`SUCCESS: Paused queue '${selectedQueue}'.`);
      loadPausedQueues();
    } catch (err) {
      addChaosLog(`ERROR: Failed to pause queue: ${err.message}`);
    }
  };

  const handleResumeQueue = async (queue) => {
    try {
      addChaosLog(`Resuming task polling on queue '${queue}'...`);
      await resumeQueue(queue);
      addChaosLog(`SUCCESS: Resumed queue '${queue}'.`);
      loadPausedQueues();
    } catch (err) {
      addChaosLog(`ERROR: Failed to resume queue: ${err.message}`);
    }
  };

  const handleExpireLease = async () => {
    try {
      addChaosLog(`Simulating active task lease expiry (expired oldest lease)...`);
      const res = await triggerLeaseExpiry();
      addChaosLog(`SUCCESS: Expired lease for Task #${res.task_id}.`);
      setTimeout(loadValidation, 1000);
    } catch (err) {
      addChaosLog(`WARNING: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleTriggerRecovery = async () => {
    try {
      addChaosLog(`Triggering immediate lease recovery scanner and queue reconciliation pass...`);
      await triggerManualRecovery();
      addChaosLog(`SUCCESS: System recovery and queue reconciliation executed.`);
      setTimeout(loadValidation, 1000);
    } catch (err) {
      addChaosLog(`ERROR: ${err.message}`);
    }
  };

  const handleInjectBurst = async () => {
    try {
      addChaosLog(`Injecting high-burst load of 30 tasks into low/medium queues...`);
      await injectBurstLoad(30);
      addChaosLog(`SUCCESS: Enqueued 30 tasks.`);
      setTimeout(loadValidation, 1000);
    } catch (err) {
      addChaosLog(`ERROR: ${err.message}`);
    }
  };

  const handleToggleBackpressure = async () => {
    const newState = !backpressureForced;
    try {
      addChaosLog(`${newState ? 'Forcing' : 'Releasing'} system backpressure overload protection override...`);
      await triggerBackpressure(newState);
      setBackpressureForced(newState);
      addChaosLog(`SUCCESS: Backpressure override set to ${newState ? 'ACTIVE' : 'DORMANT'}.`);
      setTimeout(loadValidation, 1000);
    } catch (err) {
      addChaosLog(`ERROR: ${err.message}`);
    }
  };

  const handleTriggerFailover = async () => {
    try {
      addChaosLog(`Releasing HA Leader Lock and expiring owner leases to force orchestrator failover...`);
      await triggerOrchestratorFailover();
      addChaosLog(`SUCCESS: Failover event dispatched. Standby replicas are acquiring leadership.`);
      setTimeout(loadValidation, 1000);
    } catch (err) {
      addChaosLog(`ERROR: ${err.message}`);
    }
  };

  // Pipeline Templates Execution
  const runTemplate = async (templateName, initialPayload = {}) => {
    try {
      addChaosLog(`Launching pipeline template: '${templateName}'...`);
      const payload = {
        name: `${templateName} (UI Demo)`,
        pipeline_type: templateName,
        initial_payload: initialPayload
      };
      const res = await createPipeline(payload);
      addChaosLog(`SUCCESS: Started pipeline #${res.pipeline_id} with ${res.tasks?.length} tasks.`);
    } catch (err) {
      addChaosLog(`ERROR: Failed to run template: ${err.response?.data?.error || err.message}`);
    }
  };

  // Subprocess Test Execution
  const triggerTestRun = async () => {
    setIsRunningTest(true);
    setTestStatus('running');
    setTestLogs(['Initializing test execution...', 'Spawning host subprocess...']);
    try {
      await runSubprocessTest(selectedTest);
      addChaosLog(`Subprocess test suite '${selectedTest}' initiated.`);
    } catch (err) {
      setTestStatus('failed');
      setTestLogs(prev => [...prev, `FAIL: Failed to run subprocess: ${err.message}`]);
      setIsRunningTest(false);
    }
  };

  // Icons mapper for Validation Items
  const getValidationIcon = (title) => {
    if (title.includes('PostgreSQL') || title.includes('Database')) return <Database size={18} />;
    if (title.includes('Redis')) return <Activity size={18} />;
    if (title.includes('Qdrant')) return <Search size={18} />;
    if (title.includes('Worker')) return <Server size={18} />;
    if (title.includes('Queue')) return <Shield size={18} />;
    if (title.includes('Replay')) return <RefreshCw size={18} />;
    if (title.includes('DAG')) return <Cpu size={18} />;
    if (title.includes('Lease')) return <Activity size={18} />;
    if (title.includes('Recovery')) return <Zap size={18} />;
    return <Shield size={18} />;
  };

  return (
    <div className="validation-lab-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Sub Tabs Navigation */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border-subtle)',
        gap: '24px',
        paddingBottom: '2px'
      }}>
        <button 
          className={`tab-btn ${activeTab === 'center' ? 'active' : ''}`}
          onClick={() => setActiveTab('center')}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === 'center' ? 'var(--color-accent)' : 'var(--text-muted)',
            fontWeight: '700',
            fontSize: '0.9rem',
            padding: '8px 12px',
            borderBottom: activeTab === 'center' ? '2px solid var(--color-accent)' : '2px solid transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Shield size={16} />
          System Validation Center
        </button>
        <button 
          className={`tab-btn ${activeTab === 'chaos' ? 'active' : ''}`}
          onClick={() => setActiveTab('chaos')}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === 'chaos' ? 'var(--color-accent)' : 'var(--text-muted)',
            fontWeight: '700',
            fontSize: '0.9rem',
            padding: '8px 12px',
            borderBottom: activeTab === 'chaos' ? '2px solid var(--color-accent)' : '2px solid transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Zap size={16} />
          Chaos & Recovery Lab
        </button>
        <button 
          className={`tab-btn ${activeTab === 'templates' ? 'active' : ''}`}
          onClick={() => setActiveTab('templates')}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === 'templates' ? 'var(--color-accent)' : 'var(--text-muted)',
            fontWeight: '700',
            fontSize: '0.9rem',
            padding: '8px 12px',
            borderBottom: activeTab === 'templates' ? '2px solid var(--color-accent)' : '2px solid transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <PlayCircle size={16} />
          Pipeline Templates
        </button>
        <button 
          className={`tab-btn ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === 'results' ? 'var(--color-accent)' : 'var(--text-muted)',
            fontWeight: '700',
            fontSize: '0.9rem',
            padding: '8px 12px',
            borderBottom: activeTab === 'results' ? '2px solid var(--color-accent)' : '2px solid transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Terminal size={16} />
          Subprocess Test Results
        </button>
      </div>

      {/* VIEWPORT AREA */}
      <div className="tab-viewport">
        
        {/* ==================== 1. SYSTEM VALIDATION CENTER ==================== */}
        {activeTab === 'center' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Continuous Platform Integrity Status</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Real-time health check verification metrics across the orchestration stack.</span>
              </div>
              <button 
                onClick={loadValidation} 
                disabled={loadingValidation}
                className="btn btn-secondary" 
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', fontSize: '0.8rem' }}
              >
                <RefreshCw size={14} className={loadingValidation ? "animate-spin" : ""} />
                Re-Run Diagnostics
              </button>
            </div>

            {/* Validation Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: '16px',
              marginTop: '8px'
            }}>
              {Object.keys(validationItems).map((key) => {
                const item = validationItems[key];
                const isPass = item.status === 'PASS';
                const isFail = item.status === 'FAIL';
                const isWarn = item.status === 'WARNING';
                
                let cardBorder = '1px solid var(--border-subtle)';
                let statusBg = 'var(--border-subtle)';
                let statusColor = 'var(--text-muted)';
                
                if (isPass) {
                  cardBorder = '1px solid rgba(16, 185, 129, 0.15)';
                  statusBg = 'rgba(16, 185, 129, 0.1)';
                  statusColor = '#10B981';
                } else if (isFail) {
                  cardBorder = '1px solid rgba(239, 68, 68, 0.2)';
                  statusBg = 'rgba(239, 68, 68, 0.1)';
                  statusColor = '#EF4444';
                } else if (isWarn) {
                  cardBorder = '1px solid rgba(245, 158, 11, 0.2)';
                  statusBg = 'rgba(245, 158, 11, 0.1)';
                  statusColor = '#F59E0B';
                }

                return (
                  <div key={key} style={{
                    background: 'var(--bg-panel)',
                    border: cardBorder,
                    borderRadius: '4px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    transition: 'transform 0.2s',
                    boxShadow: 'none'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ color: statusColor, display: 'flex', alignItems: 'center' }}>
                        {getValidationIcon(key)}
                      </div>
                      <span style={{
                        background: statusBg,
                        color: statusColor,
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontSize: '0.65rem',
                        fontWeight: 'bold',
                        letterSpacing: '0.5px'
                      }}>
                        {item.status}
                      </span>
                    </div>

                    <div>
                      <div style={{ fontWeight: '700', fontSize: '0.9rem', marginBottom: '4px' }}>{key}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        {item.message}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ==================== 2. CHAOS & RECOVERY LAB ==================== */}
        {activeTab === 'chaos' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '24px' }}>
            
            {/* Control Dashboard */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Fault Injection & Orchestration Control Panel</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Simulate network, instance, and queue failure models to verify platform safety guarantees.</span>
              </div>

              {/* Actions Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '16px'
              }}>
                
                {/* 1. Worker Controller */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <Server size={16} style={{ color: 'var(--color-accent)' }} />
                    Worker Node Chaos
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Shutdown a worker's docker container or boot it back up to test heartbeat timeouts and lease transfers.
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <select 
                      value={selectedWorker} 
                      onChange={e => setSelectedWorker(e.target.value)}
                      style={{
                        flex: 1,
                        background: '#090d16',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        color: '#fff',
                        padding: '6px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <option value="worker-1">worker-1</option>
                      <option value="worker-2">worker-2</option>
                      <option value="worker-3">worker-3</option>
                    </select>
                    <button onClick={handleKillWorker} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem', background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}>
                      Kill
                    </button>
                    <button onClick={handleStartWorker} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                      Reboot
                    </button>
                  </div>
                </div>

                {/* 2. Queue Controller */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <Activity size={16} style={{ color: 'var(--color-accent)' }} />
                    Queue Polling Regulator
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Freeze polling on a queue so tasks build up in Redis. Pause checks are executed atomically by workers.
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <select 
                      value={selectedQueue} 
                      onChange={e => setSelectedQueue(e.target.value)}
                      style={{
                        flex: 1,
                        background: '#090d16',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        color: '#fff',
                        padding: '6px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <option value="task_queue_high">High Queue</option>
                      <option value="task_queue_medium">Medium Queue</option>
                      <option value="task_queue_low">Low Queue</option>
                      <option value="task_queue_test_high">Test High Queue</option>
                      <option value="task_queue_test_medium">Test Medium Queue</option>
                      <option value="task_queue_test_low">Test Low Queue</option>
                    </select>
                    <button onClick={handlePauseQueue} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem', background: 'rgba(245,158,11,0.1)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.2)' }}>
                      Pause
                    </button>
                  </div>
                  {pausedQueues.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', width: '100%' }}>Currently Paused:</span>
                      {pausedQueues.map(q => (
                        <span key={q} onClick={() => handleResumeQueue(q)} style={{
                          background: 'rgba(245,158,11,0.1)',
                          color: '#F59E0B',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '0.65rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          cursor: 'pointer'
                        }}>
                          {q.replace('task_queue_', '')} ✕
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* 3. Lease Expiration Controller */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <Cpu size={16} style={{ color: 'var(--color-accent)' }} />
                    Lease Expiry Simulation
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Artificially expire the lease of the oldest running task in SQL database to force a recovery sweep event.
                  </div>
                  <button onClick={handleExpireLease} className="btn btn-secondary" style={{ width: '100%', fontSize: '0.8rem', padding: '6px' }}>
                    Force Lease Expiry
                  </button>
                </div>

                {/* 4. Leader Lock Failover */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <ToggleLeft size={16} style={{ color: 'var(--color-accent)' }} />
                    Orchestrator Failover Chaos
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Release the leader lock and expire leases to simulate full leader coordinator node crash.
                  </div>
                  <button onClick={handleTriggerFailover} className="btn btn-secondary" style={{ width: '100%', fontSize: '0.8rem', padding: '6px', background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}>
                    Trigger Failover Crash
                  </button>
                </div>

                {/* 5. Load & Overload Controllers */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <Zap size={16} style={{ color: 'var(--color-accent)' }} />
                    Load Overload Controls
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Inject massive loads or manually toggle backpressure to check deferred task routing.
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={handleInjectBurst} className="btn btn-secondary" style={{ flex: 1, fontSize: '0.75rem', padding: '6px' }}>
                      Inject 30 Tasks
                    </button>
                    <button onClick={handleToggleBackpressure} className="btn btn-secondary" style={{ 
                      flex: 1, 
                      fontSize: '0.75rem', 
                      padding: '6px',
                      background: backpressureForced ? 'rgba(239, 68, 68, 0.1)' : '',
                      color: backpressureForced ? '#EF4444' : '',
                      border: backpressureForced ? '1px solid rgba(239, 68, 68, 0.2)' : ''
                    }}>
                      {backpressureForced ? 'Release BP' : 'Force BP'}
                    </button>
                  </div>
                </div>

                {/* 6. Manual Recovery Sweep */}
                <div style={{
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem' }}>
                    <Shield size={16} style={{ color: 'var(--color-accent)' }} />
                    Reconciliation Recovery
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Force manual execution of the queue reconciliation scanner to fix database/Redis discrepancies immediately.
                  </div>
                  <button onClick={handleTriggerRecovery} className="btn btn-primary" style={{ width: '100%', fontSize: '0.8rem', padding: '6px' }}>
                    Trigger Recovery Scan
                  </button>
                </div>

              </div>
            </div>

            {/* Live Chaos Console */}
            <div style={{
              background: '#090d16',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(100vh - 280px)',
              minHeight: '400px',
              boxShadow: 'none'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '12px' }}>
                <Terminal size={16} style={{ color: 'var(--color-accent)' }} />
                Chaos Lab Log Console
              </div>
              <div style={{
                flex: 1,
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                lineHeight: 1.6,
                display: 'flex',
                flexDirection: 'column-reverse',
                gap: '8px',
                color: '#94a3b8'
              }}>
                {chaosLog.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', margin: 'auto' }}>
                    Ready. Trigger chaos actions to see logs here.
                  </div>
                ) : (
                  chaosLog.map((log, i) => {
                    let color = '#94a3b8';
                    if (log.includes('SUCCESS:')) color = '#10B981';
                    if (log.includes('ERROR:')) color = '#EF4444';
                    if (log.includes('WARNING:')) color = '#F59E0B';
                    return (
                      <div key={i} style={{ color, wordBreak: 'break-all' }}>
                        {log}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </div>
        )}

        {/* ==================== 3. PIPELINE TEMPLATES ==================== */}
        {activeTab === 'templates' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>One-Click Execution Templates</h3>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Deploy pre-configured pipeline DAGs to demonstrate specific platform capabilities.</span>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '20px'
            }}>
              
              {/* 1. PDF RAG Template */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '240px',
                boxShadow: 'none'
              }}>
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '700' }}>PDF RAG Pipeline</h4>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    Runs text parsing, chunking, real semantic embedding generation, vector ingestion to Qdrant collection, and extractive summarization.
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Qdrant</span>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Embeddings</span>
                  </div>
                </div>
                <button 
                  onClick={() => runTemplate('document_processing_demo', {
                    "source_text": "ScaleFlow is a distributed orchestration control plane designed by Google DeepMind developers. It utilizes Qdrant for semantic search indexing and features native backpressure."
                  })}
                  className="btn btn-primary" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.8rem' }}
                >
                  <Play size={14} /> Run Template
                </button>
              </div>

              {/* 2. Log Analysis Template */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '240px',
                boxShadow: 'none'
              }}>
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '700' }}>Log Analysis Pipeline</h4>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    Processes system log outputs, isolates critical failures/warnings, generates vector indexes, and creates a consolidated log anomaly final report.
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Anomalies</span>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Aggregation</span>
                  </div>
                </div>
                <button 
                  onClick={() => runTemplate('log_analysis_demo', {
                    "source_text": "2026-05-25 INFO Init service\n2026-05-25 WARN Disk load at 85%\n2026-05-25 ERROR Connection timed out to DB broker\n2026-05-25 CRITICAL Out of memory crash triggered"
                  })}
                  className="btn btn-primary" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.8rem' }}
                >
                  <Play size={14} /> Run Template
                </button>
              </div>

              {/* 3. Recovery Demonstration */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '240px',
                boxShadow: 'none'
              }}>
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '700' }}>Lease Recovery Demo</h4>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    Triggers a task that hangs for 45s. While hanging, you can manually expire its lease and watch the system automatically reassign it to a healthy worker.
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Orphan Recovery</span>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Lease Expiry</span>
                  </div>
                </div>
                <button 
                  onClick={() => runTemplate('recovery_demo')}
                  className="btn btn-primary" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.8rem' }}
                >
                  <Play size={14} /> Run Template
                </button>
              </div>

              {/* 4. Replay Demonstration */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '240px',
                boxShadow: 'none'
              }}>
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '700' }}>Replay Demonstration</h4>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    Launches a simple 2-node pipeline to generate clear event logs. Perfect for showcasing the "Replay Engine" (Time Travel) in the sidebar.
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Time Travel</span>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Event Log</span>
                  </div>
                </div>
                <button 
                  onClick={() => runTemplate('replay_demo')}
                  className="btn btn-primary" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.8rem' }}
                >
                  <Play size={14} /> Run Template
                </button>
              </div>

              {/* 5. High Load Simulation */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '240px',
                boxShadow: 'none'
              }}>
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: '700' }}>High Load Simulation</h4>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    Spawns 10 parallel email tasks simultaneously upon parent completion. Floods the queue to showcase backpressure triggers and worker routing.
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Concurrency</span>
                    <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>Backpressure</span>
                  </div>
                </div>
                <button 
                  onClick={() => runTemplate('high_load_demo')}
                  className="btn btn-primary" 
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.8rem' }}
                >
                  <Play size={14} /> Run Template
                </button>
              </div>

            </div>
          </div>
        )}

        {/* ==================== 4. SUBPROCESS TEST RESULTS ==================== */}
        {activeTab === 'results' && (
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '24px' }}>
            
            {/* Test Selection Panel */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Host Test Suite Runner</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Execute underlying integration tests asynchronously via host subprocess.</span>
              </div>

              {/* Test selector list */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <button 
                  onClick={() => setSelectedTest('validation')} 
                  disabled={isRunningTest}
                  style={{
                    background: selectedTest === 'validation' ? 'rgba(91,140,255,0.1)' : 'var(--bg-panel)',
                    border: selectedTest === 'validation' ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '12px',
                    textAlign: 'left',
                    color: '#fff',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontWeight: '700', fontSize: '0.85rem' }}>API Endpoint Validation</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>test_validation.py</span>
                </button>

                <button 
                  onClick={() => setSelectedTest('stress')} 
                  disabled={isRunningTest}
                  style={{
                    background: selectedTest === 'stress' ? 'rgba(91,140,255,0.1)' : 'var(--bg-panel)',
                    border: selectedTest === 'stress' ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '12px',
                    textAlign: 'left',
                    color: '#fff',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontWeight: '700', fontSize: '0.85rem' }}>Backpressure & Recovery Stress</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>stress_simulation.py</span>
                </button>

                <button 
                  onClick={() => setSelectedTest('ha')} 
                  disabled={isRunningTest}
                  style={{
                    background: selectedTest === 'ha' ? 'rgba(91,140,255,0.1)' : 'var(--bg-panel)',
                    border: selectedTest === 'ha' ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '12px',
                    textAlign: 'left',
                    color: '#fff',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontWeight: '700', fontSize: '0.85rem' }}>HA Chaos & Reliability Simulation</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>stress_simulation_ha.py</span>
                </button>
              </div>

              {/* Action Button */}
              <button 
                onClick={triggerTestRun} 
                disabled={isRunningTest}
                className="btn btn-primary" 
                style={{
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  gap: '8px', 
                  padding: '12px', 
                  fontWeight: 'bold',
                  background: isRunningTest ? 'rgba(91, 140, 255, 0.2)' : ''
                }}
              >
                {isRunningTest ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {isRunningTest ? 'Running Test...' : 'Run Selected Suite'}
              </button>

              {/* Status card */}
              <div style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Run Status:</span>
                <span style={{
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                  fontSize: '0.85rem',
                  color: testStatus === 'success' ? '#10B981' : testStatus === 'failed' ? '#EF4444' : testStatus === 'running' ? '#F59E0B' : 'var(--text-muted)'
                }}>
                  {testStatus}
                </span>
              </div>
            </div>

            {/* Test Logging Terminal */}
            <div style={{
              background: '#090d16',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(100vh - 280px)',
              minHeight: '400px',
              boxShadow: 'none'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: '0.9rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '12px' }}>
                <Terminal size={16} style={{ color: 'var(--color-accent)' }} />
                Subprocess Output Console (Real-time Stream)
              </div>
              <div style={{
                flex: 1,
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                lineHeight: 1.6,
                color: '#e2e8f0',
                padding: '4px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}>
                {testLogs.map((log, index) => {
                  let color = '#e2e8f0';
                  if (log.includes('--- Test') || log.includes('Scenario')) color = 'var(--color-accent)';
                  if (log.includes('SUCCESS') || log.includes('PASSED') || log.includes('passed')) color = '#10B981';
                  if (log.includes('FAILED') || log.includes('ERROR') || log.includes('error')) color = '#EF4444';
                  if (log.includes('WARNING') || log.includes('Warning')) color = '#F59E0B';
                  return (
                    <div key={index} style={{ color, whiteSpace: 'pre-wrap' }}>
                      {log}
                    </div>
                  );
                })}
                <div ref={terminalEndRef} />
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
}
