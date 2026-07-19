import { useTelemetry } from '../../../services/telemetryStore';

/**
 * Custom hook to aggregate system and cluster telemetry metrics.
 */
export const useMetrics = () => {
  const workers = useTelemetry(s => s.workers);
  const queueStats = useTelemetry(s => s.queueStats);
  const redisStatus = useTelemetry(s => s.redisStatus);
  const dbStatus = useTelemetry(s => s.dbStatus);
  const qdrantStatus = useTelemetry(s => s.qdrantStatus);
  const leaderId = useTelemetry(s => s.leaderId);
  const orchestratorCount = useTelemetry(s => s.orchestratorCount);

  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;
  
  const totalQueueSize = queueStats.total || 0;
  const backpressureLimit = 50;
  const queuePressure = Math.min(100, Math.round((totalQueueSize / backpressureLimit) * 100));

  return {
    redisStatus,
    dbStatus,
    qdrantStatus,
    leaderId,
    orchestratorCount,
    activeWorkersCount,
    totalQueueSize,
    queuePressure
  };
};
export default useMetrics;
