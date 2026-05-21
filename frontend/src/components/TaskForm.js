import React, { useState, useEffect } from 'react';
import { Zap } from 'lucide-react';
import { createTask, fetchTaskTypes } from '../services/api';

const TaskForm = ({ onTaskCreated }) => {
  const [taskTypes, setTaskTypes] = useState([]);
  const [taskType, setTaskType] = useState('');
  const [priority, setPriority] = useState('medium');
  const [formValues, setFormValues] = useState({});
  const [dependencies, setDependencies] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTaskTypes = async () => {
      try {
        const data = await fetchTaskTypes();
        setTaskTypes(data);
        if (data.length > 0) {
          setTaskType(data[0].type);
          const initialValues = {};
          data[0].frontend_fields.forEach(field => {
            initialValues[field.name] = '';
          });
          setFormValues(initialValues);
        }
      } catch (err) {
        console.error('Failed to load task types:', err);
      }
    };
    loadTaskTypes();
  }, []);

  const handleTypeChange = (selectedType) => {
    setTaskType(selectedType);
    const selectedSchema = taskTypes.find(t => t.type === selectedType);
    if (selectedSchema) {
      const initialValues = {};
      selectedSchema.frontend_fields.forEach(field => {
        initialValues[field.name] = '';
      });
      setFormValues(initialValues);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFormValues(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const selectedSchema = taskTypes.find(t => t.type === taskType);
    const cleanedData = {};
    if (selectedSchema) {
      selectedSchema.frontend_fields.forEach(field => {
        const value = formValues[field.name];
        const strVal = typeof value === 'string' ? value.trim() : value;
        if (strVal !== undefined && strVal !== null && strVal !== '') {
          cleanedData[field.name] = strVal;
        }
      });
    }

    const deps = dependencies.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    try {
      await createTask({ 
        type: taskType, 
        data: cleanedData, 
        priority, 
        dependencies: deps.length > 0 ? deps : undefined 
      });
      
      const resetValues = {};
      if (selectedSchema) {
        selectedSchema.frontend_fields.forEach(field => {
          resetValues[field.name] = '';
        });
      }
      setFormValues(resetValues);
      setDependencies('');
      setPriority('medium');
      if (onTaskCreated) onTaskCreated();
    } catch (err) {
      setError(err.response?.data?.error || 'Error creating task');
    }
  };

  const selectedSchema = taskTypes.find(t => t.type === taskType);

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
            <select value={taskType} onChange={(e) => handleTypeChange(e.target.value)}>
              {taskTypes.map((typeObj) => (
                <option key={typeObj.type} value={typeObj.type}>
                  {typeObj.label}
                </option>
              ))}
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

        {selectedSchema && selectedSchema.frontend_fields.map((field) => {
          const isRequired = selectedSchema.required_fields.includes(field.name);
          return (
            <div className="form-field" key={field.name}>
              <label>
                {field.label} {isRequired && <span style={{ color: '#ef4444' }}>*</span>}
              </label>
              {field.type === 'textarea' ? (
                <textarea
                  value={formValues[field.name] || ''}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  placeholder={field.placeholder}
                  required={isRequired}
                  rows={3}
                />
              ) : (
                <input
                  type={field.type === 'email' ? 'email' : 'text'}
                  value={formValues[field.name] || ''}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  placeholder={field.placeholder}
                  required={isRequired}
                />
              )}
            </div>
          );
        })}

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
