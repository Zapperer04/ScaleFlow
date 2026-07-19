import { useState, useEffect } from 'react';

// Centralised telemetry state
let telemetryState = {
  workers: [],
  queueStats: {},
  redisStatus: 'checking',
  dbStatus: 'checking',
  qdrantStatus: 'checking',
  leaderId: 'Checking...',
  orchestratorCount: 0,
  stats: { total: 0, pending: 0, running: 0, completed: 0 }
};

const listeners = new Set();

const subscribe = (listener) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

const getState = () => telemetryState;

const setState = (nextState) => {
  telemetryState = {
    ...telemetryState,
    ...nextState
  };
  listeners.forEach(listener => listener(telemetryState));
};

export const telemetryStore = {
  subscribe,
  getState,
  setState
};

// Custom hook to subscribe to specific telemetry sub-states with change detection
export function useTelemetry(selector = (s) => s) {
  const [value, setValue] = useState(() => selector(telemetryState));

  useEffect(() => {
    const unsubscribe = subscribe((nextState) => {
      const nextValue = selector(nextState);
      setValue(prev => {
        if (typeof nextValue === 'object' && nextValue !== null) {
          // Compare objects using JSON stringify to avoid reference mismatches
          return JSON.stringify(prev) === JSON.stringify(nextValue) ? prev : nextValue;
        }
        return prev === nextValue ? prev : nextValue;
      });
    });

    return unsubscribe;
  }, [selector]);

  return value;
}
