import React, { useState, useEffect } from 'react';
import { Activity, Cpu, Database, Zap, TrendingUp, Layers, Server, Clock } from 'lucide-react';
import { fetchTasks, fetchWorkers, getQueueStats } from './services/api';
import MetricCard from './components/MetricCard';
import TaskForm from './components/TaskForm';
import TaskLog from './components/TaskLog';
import WorkerStatus from './components/WorkerStatus';
import QueueStats from './components/QueueStats';
import TaskModal from './components/TaskModal';
import { ThroughputChart, WorkerLoadChart } from './components/Charts';
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
  const [queueStuckSince, setQueueStuckSince] = useState(null);
  const [showStuckWarning, setShowStuckWarning] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const tasksData = await fetchTasks(1, 50);
      const taskList = tasksData.tasks || [];
      const metadata = tasksData.metadata || { total_tasks: 0 };
      
      setTasks(taskList);

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
        setQueueStuckSince(prev => {
          const now = Date.now();
          const start = prev || now;
          if (now - start > 10000) {
            setShowStuckWarning(true);
          }
          return start;
        });
      } else {
        setQueueStuckSince(null);
        setShowStuckWarning(false);
      }

      setStats({
        total: metadata.total_tasks,
        pending: taskList.filter(t => t.status === 'pending').length,
        running: taskList.filter(t => t.status === 'running').length,
        completed: taskList.filter(t => t.status === 'completed').length
      });

      const throughputData = taskList.slice(0, 20).reverse().reduce((acc, task, idx) => {
        const bucket = Math.floor(idx / 4);
        if (!acc[bucket]) acc[bucket] = { name: `T${bucket}`, count: 0 };
        if (task.status === 'completed') acc[bucket].count++;
        return acc;
      }, []).filter(Boolean);
      setThroughput(throughputData);

      setWorkerDistribution([
        { name: 'Worker 1', value: taskList.filter((t, i) => i % 3 === 0 && t.status === 'completed').length },
        { name: 'Worker 2', value: taskList.filter((t, i) => i % 3 === 1 && t.status === 'completed').length },
        { name: 'Worker 3', value: taskList.filter((t, i) => i % 3 === 2 && t.status === 'completed').length },
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

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
          <MetricCard icon={Activity} label="Total Tasks Processed" value={stats.total} trend={stats.total > 0 ? 12 : 0} color="rgba(139, 92, 246, 0.2)" gradient="linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)" />
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
          <TaskLog tasks={tasks} workers={workers} onTaskClick={setSelectedTaskId} />
        </div>
      </div>
      
      <TaskModal 
        taskId={selectedTaskId} 
        onClose={() => setSelectedTaskId(null)} 
        onActionComplete={loadData} 
      />
    </div>
  );
}

export default App;