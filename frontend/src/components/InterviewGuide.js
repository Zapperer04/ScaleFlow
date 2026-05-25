import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, Shield, Activity, Database, Zap, Cpu, Award } from 'lucide-react';

const INTERVIEW_TOPICS = [
  {
    id: "choice",
    title: "Why use a Redis + PostgreSQL Hybrid model?",
    icon: Database,
    color: "#10b981",
    summary: "Balances high-speed atomic queue popping with durable, consistent ACID state records.",
    detail: "Standard databases use row-locks and indexes that are slow for high-frequency queuing operations, causing bottleneck issues at scale. Redis operates in memory and handles pop actions (`rpop`, `brpop`) atomically, ensuring a task is never delivered twice. We combine this with PostgreSQL, which stores the append-only recovery ledger and transactional pipeline state. If Redis goes down, PostgreSQL stores the source of truth, allowing the coordinator to reconcile queues without state loss."
  },
  {
    id: "recovery",
    title: "How does the system handle stuck task lease recoveries?",
    icon: Shield,
    color: "#ef4444",
    summary: "Automatic stuck-task reaping via heartbeats, TTLs, and recovery sweeps.",
    detail: "When a worker claims a task, it receives a lease token and duration (e.g. 30s). The worker starts a background LeaseRenewer thread that calls `/renew-lease` periodically. If the worker crashes, the lease expires. The Orchestrator's background Recovery Scanner thread (runs every 10s on the leader instance) sweeps for running tasks with expired leases. It increments the task's recovery count and retry count, marks it pending, and pushes it back to Redis. If maximum retries are exceeded, the task is marked failed and downstream DAG blocks are triggered."
  },
  {
    id: "fencing",
    title: "How does the system prevent split-brain issues during failover?",
    icon: Shield,
    color: "#f59e0b",
    summary: "Fencing tokens built on a monotonic pipeline ownership version counter.",
    detail: "Suppose an orchestrator holding a pipeline lease undergoes a long garbage collection (GC) pause. Its lease expires, and a second orchestrator takes over the pipeline, incrementing the database `ownership_version` fencing token from 1 to 2. When the first orchestrator wakes up and attempts to update a task completion or release dependencies, it checks its local cached token (1) against the database token (2). The database immediately rejects the write with an HTTP 409 Conflict. The stale orchestrator evicts the pipeline from its memory and halts execution."
  },
  {
    id: "replay",
    title: "What is Replay Sandboxing, and how is it deterministic?",
    icon: Activity,
    color: "#8b5cf6",
    summary: "Reconstructs in-memory DAG state by applying historical event logs without executing side-effects.",
    detail: "To debug a failed or complex pipeline, operators can scrub back in time. The Replay Engine fetches the append-only PostgreSQL event log for that pipeline and sequentially applies state updates to an in-memory state representation. Crucially, Replay is completely sandboxed: it does not enqueue tasks to Redis, trigger worker execution, update live database tables, or generate vector embeddings. It uses incremental snapshots at event watermarks to ensure reconstruction is O(K) where K is the snapshot window."
  },
  {
    id: "backpressure",
    title: "How does Pipeline Backpressure prevent worker saturation?",
    icon: Zap,
    color: "#ec4899",
    summary: "Prevents downstream queue growth by blocking upstream task releases and aging priority.",
    detail: "When a capability-specific queue (e.g., GPU summaries) exceeds a threshold (e.g., 10 tasks), the resolver marks the capability congested. When a parent task completes, instead of releasing child tasks to Redis, the Orchestrator marks them as `'blocked'` with the reason `'Upstream congestion: throttled'`. The unblock scanner releases them once queue load drops below 10. To prevent starvation of throttled tasks, we apply priority aging: if a deferred task waits over 60s, it is escalated to high priority and admitted immediately."
  },
  {
    id: "starvation",
    title: "How does Weighted Round-Robin (WRR) prevent queue starvation?",
    icon: Cpu,
    color: "#3b82f6",
    summary: "Workers poll priority queues using a strict allocation ratio rather than absolute priority.",
    detail: "If workers always popped from High priority first, Medium and Low tasks would experience starvation under heavy burst loads. ScaleFlow implements a Weighted Round-Robin sequence: `[6 High : 3 Medium : 1 Low]` in a 10-step cycle. An atomic Redis pointer increments on every pop. The worker polls matching capability queues (e.g. CPU) corresponding to the target priority of that step. If the target queue is empty, the worker falls back to priority-order checks non-blockingly, and blocks on all capability queues if all are empty."
  },
  {
    id: "scale",
    title: "What are the scalability bottlenecks, and how would you resolve them?",
    icon: Award,
    color: "#a78bfa",
    summary: "PostgreSQL lock contention on lease updates; resolved via hash-ring partitioning.",
    detail: "The primary database bottleneck is the database lock footprint during pipeline lease checks. Multiple orchestrator instances run `UPDATE pipelines SET owner_instance_id = ...` queries. At 10,000+ concurrent pipelines, this will trigger lock contention in PostgreSQL. To scale further, we recommend introducing a consistent hashing ring: hash the pipeline UUID to assign ownership partition keys, so each orchestrator is exclusively responsible for a segment of pipeline IDs. This distributes the DB transaction load and eliminates lock contention."
  }
];

const InterviewGuide = () => {
  const [activeTopic, setActiveTopic] = useState('choice');

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px', marginTop: '10px' }}>
      
      {/* Left Column: Topics Accordion */}
      <div style={{ gridColumn: 'span 7', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', marginBottom: '8px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Award size={22} style={{ color: '#8b5cf6' }} />
            Interview Preparation Cheat Sheet
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
            A compilation of core system design questions, tradeoff rationales, and recovery flows to guide placement interviews.
          </p>
        </div>

        {INTERVIEW_TOPICS.map((topic) => {
          const Icon = topic.icon;
          const isActive = activeTopic === topic.id;
          
          return (
            <div 
              key={topic.id}
              onClick={() => setActiveTopic(topic.id)}
              style={{
                background: isActive ? 'var(--border-subtle)' : 'rgba(255, 255, 255, 0.02)',
                border: '1px solid',
                borderColor: isActive ? 'rgba(139, 92, 246, 0.4)' : 'var(--border-subtle)',
                borderRadius: '4px',
                padding: '16px 20px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: isActive ? '0 10px 20px rgba(139, 92, 246, 0.03)' : 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1 }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  background: `rgba(${topic.color === '#10b981' ? '16, 185, 129' : topic.color === '#ef4444' ? '239, 68, 68' : topic.color === '#f59e0b' ? '245, 158, 11' : topic.color === '#8b5cf6' ? '139, 92, 246' : topic.color === '#ec4899' ? '236, 72, 153' : topic.color === '#3b82f6' ? '59, 130, 246' : '167, 139, 250'}, 0.15)`,
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: topic.color
                }}>
                  <Icon size={20} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', textAlign: 'left' }}>
                  <span style={{ fontSize: '0.925rem', fontWeight: '700', color: isActive ? '#fff' : '#cbd5e1' }}>
                    {topic.title}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    {topic.summary}
                  </span>
                </div>
              </div>
              
              {isActive ? <ChevronUp size={18} style={{ color: '#8b5cf6' }} /> : <ChevronDown size={18} style={{ color: '#64748b' }} />}
            </div>
          );
        })}
      </div>

      {/* Right Column: Detailed Explanation Card */}
      <div style={{ gridColumn: 'span 5', display: 'flex', flexDirection: 'column' }}>
        
        {activeTopic && (
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: '800', color: '#8b5cf6', textTransform: 'uppercase', letterSpacing: '1px' }}>Technical Deep-Dive</span>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff', margin: '4px 0 0 0' }}>
                {INTERVIEW_TOPICS.find(t => t.id === activeTopic)?.title}
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
              
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '8px' }}>Executive Summary:</strong>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#a78bfa', fontWeight: '500', lineHeight: '1.5', padding: '10px 14px', background: 'rgba(139, 92, 246, 0.08)', borderRadius: '4px', borderLeft: '3px solid #8b5cf6' }}>
                  {INTERVIEW_TOPICS.find(t => t.id === activeTopic)?.summary}
                </p>
              </div>

              <div>
                <strong style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '8px' }}>Detailed Architectural Explanation:</strong>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8', lineHeight: '1.6', textAlign: 'left', whiteSpace: 'pre-wrap' }}>
                  {INTERVIEW_TOPICS.find(t => t.id === activeTopic)?.detail}
                </p>
              </div>

            </div>

            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '0.75rem' }}>
              <HelpCircle size={14} />
              <span>Use this breakdown to answer questions during system design interviews.</span>
            </div>

          </div>
        )}
      </div>

    </div>
  );
};

export default InterviewGuide;
