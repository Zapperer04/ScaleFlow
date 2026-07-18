/**
 * timeUtils.js - Shared time formatting utilities
 * All DB timestamps are stored in UTC without timezone suffix.
 */

const toUtcString = (str) => {
  if (!str) return null;
  if (str.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(str)) return str;
  return `${str}Z`;
};

export const formatTimeIST = (timeStr) => {
  if (!timeStr) return 'N/A';
  const utc = toUtcString(timeStr);
  const d = new Date(utc);
  if (isNaN(d.getTime())) return 'N/A';
  return d.toLocaleTimeString('en-IN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Kolkata',
  });
};

export const formatDurationHMS = (sec) => {
  if (sec === null || sec === undefined) return 'N/A';
  const s = parseFloat(sec);
  if (isNaN(s)) return 'N/A';
  const hrs  = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = Math.floor(s % 60);
  const pad  = (n) => String(n).padStart(2, '0');
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
};

export const wallClockSeconds = (startStr, endStr) => {
  if (!startStr || !endStr) return null;
  const startMs = new Date(toUtcString(startStr)).getTime();
  const endMs   = new Date(toUtcString(endStr)).getTime();
  if (isNaN(startMs) || isNaN(endMs)) return null;
  const diff = (endMs - startMs) / 1000;
  return diff > 0 ? diff : null;
};

export const computeTaskDuration = (task) => {
  if (!task) return 'N/A';
  const reported = task.execution_duration !== null && task.execution_duration !== undefined
    ? parseFloat(task.execution_duration) : null;
  const wall = wallClockSeconds(task.started_at, task.completed_at);
  if (wall !== null && !isNaN(wall)) {
    const best = reported !== null && !isNaN(reported) ? Math.max(reported, wall) : wall;
    return formatDurationHMS(best);
  }
  if (reported !== null && !isNaN(reported)) return formatDurationHMS(reported);
  return task.status === 'running' ? 'Active' : 'N/A';
};

export const pipelineElapsedHMS = (pipeline) => {
  if (!pipeline) return '00:00:00';
  const startStr = pipeline.started_at || pipeline.created_at;
  const endStr   = pipeline.completed_at;
  const startMs  = new Date(toUtcString(startStr)).getTime();
  const endMs    = endStr ? new Date(toUtcString(endStr)).getTime() : Date.now();
  const diffSec  = Math.max(0, Math.round((endMs - startMs) / 1000));
  const hrs  = Math.floor(diffSec / 3600);
  const mins = Math.floor((diffSec % 3600) / 60);
  const secs = diffSec % 60;
  const pad  = (n) => String(n).padStart(2, '0');
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
};
