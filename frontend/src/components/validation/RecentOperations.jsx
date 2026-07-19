import React, { useState } from 'react';
import Card from '../ui/Card';
import ButtonGroup from '../ui/ButtonGroup';
import Button from '../ui/Button';

/**
 * Filterable timeline log recording destructive activities.
 */
export const RecentOperations = ({ operationsLog = [] }) => {
  const [filter, setFilter] = useState('All');
  const categories = ['All', 'Validation', 'Chaos', 'Workers', 'Tests'];

  const filteredLogs = operationsLog.filter(log => {
    if (filter === 'All') return true;
    return log.category === filter;
  });

  return (
    <Card 
      className="recent-operations-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>Operations Audit Ledger</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        
        {/* Category Filters */}
        <ButtonGroup>
          {categories.map(cat => (
            <Button
              key={cat}
              variant={filter === cat ? 'primary' : 'secondary'}
              onClick={() => setFilter(cat)}
              style={{ padding: '4px 12px', fontSize: '11px' }}
            >
              {cat}
            </Button>
          ))}
        </ButtonGroup>

        {/* Audit list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)', maxH: '250px', overflowY: 'auto' }}>
          {filteredLogs.length === 0 ? (
            <div className="text-caption" style={{ color: 'var(--text-disabled)', padding: 'var(--spacing-16)', textAlign: 'center' }}>
              No recorded operations for this category.
            </div>
          ) : (
            filteredLogs.map(log => (
              <div 
                key={log.id} 
                style={{ 
                  padding: 'var(--spacing-12)', 
                  borderBottom: '1px solid var(--border-divider)', 
                  display: 'flex', 
                  gap: 'var(--spacing-12)', 
                  alignItems: 'flex-start' 
                }}
              >
                <span className="text-caption" style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--text-disabled)', whiteSpace: 'nowrap' }}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
                    <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                      {log.title}
                    </span>
                    <span 
                      style={{ 
                        fontSize: '9px', 
                        fontWeight: 'bold', 
                        padding: '2px 6px', 
                        borderRadius: '3px', 
                        background: log.category === 'Chaos' ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-hover)', 
                        color: log.category === 'Chaos' ? 'var(--color-failure)' : 'var(--text-secondary)' 
                      }}
                    >
                      {log.category.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-caption" style={{ color: 'var(--text-secondary)' }}>
                    {log.description}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </Card>
  );
};
export default RecentOperations;
