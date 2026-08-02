import React from 'react';

/**
 * Reusable vertical timeline component for executions, activities, and system events.
 */
export const Timeline = ({ children }) => {
  return (
    <div className="timeline-list" role="log">
      {children}
    </div>
  );
};

Timeline.Item = ({ 
  timestamp, 
  title, 
  description, 
  variant = 'default', // 'success', 'error', 'warning', 'info', 'default'
  icon 
}) => {
  return (
    <div className={`timeline-item ${variant}`} role="listitem">
      <div className="timeline-icon-dot" aria-hidden="true">
        {icon}
      </div>
      <div className="timeline-item-content">
        <div className="timeline-item-meta">
          <span className="timeline-item-title">{title}</span>
          {timestamp && <span className="timeline-item-time">{timestamp}</span>}
        </div>
        {description && <p className="timeline-item-desc" style={{ margin: 0 }}>{description}</p>}
      </div>
    </div>
  );
};

export default Timeline;
