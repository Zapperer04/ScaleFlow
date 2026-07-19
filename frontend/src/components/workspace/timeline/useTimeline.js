import { useState, useEffect } from 'react';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { fetchPipelineEvents } from '../../../services/api';

/**
 * Custom hook to poll pipeline trace events and normalize them.
 */
export const useTimeline = () => {
  const { selectedDocId } = useWorkspace();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!selectedDocId) {
      setEvents([]);
      return;
    }

    setLoading(true);
    let timer;

    const getEvents = async () => {
      try {
        const data = await fetchPipelineEvents(selectedDocId);
        
        // Normalize logs to consistent schema
        const normalized = (data || []).map((e, idx) => ({
          id: e.id || `${selectedDocId}-event-${idx}`,
          type: e.event_type || 'info',
          severity: e.severity || 'info',
          timestamp: e.created_at || new Date().toISOString(),
          title: e.event_name || 'Log Trace Ingested',
          description: e.message || ''
        }));

        setEvents(normalized);
        setError(null);
      } catch (err) {
        console.error('Failed to load timeline events:', err);
        setError('Failed to load trace events.');
      } finally {
        setLoading(false);
      }
    };

    getEvents();
    timer = setInterval(getEvents, 3000);

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [selectedDocId]);

  return {
    events,
    loading,
    error
  };
};
export default useTimeline;
