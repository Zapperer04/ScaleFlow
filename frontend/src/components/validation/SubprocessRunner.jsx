import React, { useRef, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Spinner from '../ui/Spinner';
import Select from '../ui/Select';

/**
 * Presentational block to run stress test suites and stream console terminal output.
 */
export const SubprocessRunner = ({
  selectedTest,
  onTestChange,
  testStatus,
  testLogs = [],
  isRunningTest,
  onRunTest
}) => {
  const consoleEndRef = useRef(null);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [testLogs]);

  const testOptions = [
    { value: 'validation', label: 'Cluster Verification Test Suite' },
    { value: 'stress', label: 'Broker Load Stress Test Suite' },
    { value: 'ha', label: 'HA Coordinator Failover Test Suite' }
  ];

  return (
    <Card 
      className="subprocess-runner-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>System Subprocess Validation Runner</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        
        {/* Test Selector and Trigger Bar */}
        <div style={{ display: 'flex', gap: 'var(--spacing-12)', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Select
              label="Select Subprocess Test Suite"
              value={selectedTest}
              options={testOptions}
              onChange={(e) => onTestChange(e.target.value)}
              disabled={isRunningTest}
            />
          </div>
          <Button 
            variant="primary"
            onClick={() => onRunTest(selectedTest)}
            disabled={isRunningTest}
            iconLeft={isRunningTest ? <Spinner size="sm" /> : undefined}
          >
            {isRunningTest ? 'Running Suite' : 'Execute Test'}
          </Button>
        </div>

        {/* Live Terminal Log Excerpt console block */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Terminal Diagnostic Console
            </span>
            <span className="text-caption" style={{ color: isRunningTest ? 'var(--color-accent)' : 'var(--text-disabled)' }}>
              Status: {testStatus.toUpperCase()}
            </span>
          </div>

          <div 
            className="terminal-console-block"
            style={{
              height: '220px',
              overflowY: 'auto',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-4)',
              padding: 'var(--spacing-12)',
              fontFamily: 'var(--font-family-mono)',
              fontSize: '12px',
              lineHeight: '1.5',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}
          >
            {testLogs.length === 0 ? (
              <span style={{ color: 'var(--text-disabled)' }}>Terminal idle. Select test suite to begin verification...</span>
            ) : (
              testLogs.map((log, idx) => {
                let color = 'var(--text-secondary)';
                if (log.includes('[ERROR]') || log.includes('Failed')) color = 'var(--color-failure)';
                if (log.includes('[SUCCESS]') || log.includes('passed')) color = 'var(--color-success)';
                if (log.includes('[INFO]')) color = 'var(--color-accent)';
                
                return (
                  <div key={idx} style={{ color, whiteSpace: 'pre-wrap' }}>
                    {log}
                  </div>
                );
              })
            )}
            <div ref={consoleEndRef} />
          </div>
        </div>

      </div>
    </Card>
  );
};
export default SubprocessRunner;
