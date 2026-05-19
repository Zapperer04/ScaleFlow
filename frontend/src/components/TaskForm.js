import React, { useState } from 'react';
import { Zap } from 'lucide-react';
import { createTask } from '../services/api';

const TaskForm = ({ onTaskCreated }) => {
  const [taskType, setTaskType] = useState('send_email');
  const [priority, setPriority] = useState('medium');
  const [inputValue, setInputValue] = useState('');
  const [dependencies, setDependencies] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    let data = {};
    switch (taskType) {
      case 'send_email': data = { to: inputValue }; break;
      case 'process_video': data = { file: inputValue }; break;
      case 'generate_report': data = { report_type: inputValue }; break;
      case 'data_backup': data = { database: inputValue }; break;
      case 'image_processing': data = { image_path: inputValue }; break;
      case 'send_notification': data = { user_id: inputValue }; break;
      case 'run_ml_model': data = { model_name: inputValue }; break;
      case 'webhook_trigger': data = { url: inputValue }; break;
      default: data = { input: inputValue };
    }

    const deps = dependencies.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    try {
      await createTask({ type: taskType, data, priority, dependencies: deps.length > 0 ? deps : undefined });
      setInputValue('');
      setDependencies('');
      setPriority('medium');
      if (onTaskCreated) onTaskCreated();
    } catch (err) {
      setError(err.response?.data?.error || 'Error creating task');
    }
  };

  const getInputPlaceholder = () => {
    switch (taskType) {
      case 'send_email': return 'user@domain.com';
      case 'process_video': return 'media/video_1080p.mp4';
      case 'generate_report': return 'Monthly Sales Report';
      case 'data_backup': return 'production_db';
      case 'image_processing': return 'uploads/photo.jpg';
      case 'send_notification': return 'user_12345';
      case 'run_ml_model': return 'sentiment_analysis_v2';
      case 'webhook_trigger': return 'https://api.example.com/webhook';
      default: return '';
    }
  };

  const getInputLabel = () => {
    switch (taskType) {
      case 'send_email': return 'Recipient Address';
      case 'process_video': return 'Video File Path';
      case 'generate_report': return 'Report Type';
      case 'data_backup': return 'Database Name';
      case 'image_processing': return 'Image Path';
      case 'send_notification': return 'User ID';
      case 'run_ml_model': return 'Model Name';
      case 'webhook_trigger': return 'Webhook URL';
      default: return 'Input';
    }
  };

  return (
    <div className="panel create-panel">
      <div className="panel-header">
        <h2>Dispatch New Task</h2>
        <span className="panel-subtitle">Submit to distributed queue</span>
      </div>
      <form onSubmit={handleSubmit} className="create-form">
        <div className="form-row">
          <div className="form-field">
            <label>Task Type</label>
            <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
              <option value="send_email">Email Delivery</option>
              <option value="process_video">Video Processing</option>
              <option value="generate_report">Generate Report</option>
              <option value="data_backup">Database Backup</option>
              <option value="image_processing">Image Processing</option>
              <option value="send_notification">Send Notification</option>
              <option value="run_ml_model">Run ML Model</option>
              <option value="webhook_trigger">Webhook Trigger</option>
            </select>
          </div>
          <div className="form-field">
            <label>Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="high">🔴 High Priority</option>
              <option value="medium">🟡 Medium Priority</option>
              <option value="low">🟢 Low Priority</option>
            </select>
          </div>
        </div>
        <div className="form-field">
          <label>{getInputLabel()}</label>
          <input type={taskType === 'webhook_trigger' ? 'url' : taskType === 'send_email' ? 'email' : 'text'} value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder={getInputPlaceholder()} required />
        </div>
        <div className="form-field">
          <label>Dependencies (Optional)</label>
          <input type="text" value={dependencies} onChange={(e) => setDependencies(e.target.value)} placeholder="Task IDs (e.g., 1,2,3)" />
          <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px', display: 'block' }}>Comma-separated task IDs that must complete first</span>
        </div>
        {error && <div style={{ color: '#ef4444', marginBottom: '1rem', fontSize: '0.875rem' }}>{error}</div>}
        <button type="submit" className="submit-btn"><Zap size={18} /> Enqueue Task</button>
      </form>
    </div>
  );
};

export default TaskForm;
