import React from 'react';
import Skeleton from '../ui/Skeleton';

/**
 * Loading skeletons layout presets.
 */
export const PageSkeleton = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)', width: '100%' }}>
      {/* Page Header Row Skeleton */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 'var(--spacing-16)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '200px' }}>
          <Skeleton variant="text" width="100%" height="1.5rem" />
          <Skeleton variant="text" width="60%" height="0.8rem" />
        </div>
        <Skeleton variant="rect" width="100px" height="36px" />
      </div>

      {/* Metric Cards Skeleton */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--spacing-24)' }}>
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>

      {/* Main Table Skeleton */}
      <TableSkeleton rows={4} />
    </div>
  );
};

export const CardSkeleton = () => {
  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '110px' }}>
      <Skeleton variant="text" width="40%" height="0.9rem" />
      <Skeleton variant="text" width="80%" height="1.5rem" />
      <Skeleton variant="text" width="90%" height="0.75rem" />
    </div>
  );
};

export const TableSkeleton = ({ rows = 5 }) => {
  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-divider)', paddingBottom: '8px' }}>
        <Skeleton variant="text" width="20%" />
        <Skeleton variant="text" width="30%" />
        <Skeleton variant="text" width="20%" />
        <Skeleton variant="text" width="30%" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ display: 'flex', gap: '16px', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
          <Skeleton variant="text" width="20%" />
          <Skeleton variant="text" width="40%" />
          <Skeleton variant="text" width="15%" />
          <Skeleton variant="text" width="25%" />
        </div>
      ))}
    </div>
  );
};

export const SidebarSkeleton = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px' }}>
      {Array.from({ length: 7 }).map((_, i) => (
        <Skeleton key={i} variant="rect" width="100%" height="32px" />
      ))}
    </div>
  );
};

export default {
  PageSkeleton,
  CardSkeleton,
  TableSkeleton,
  SidebarSkeleton
};
