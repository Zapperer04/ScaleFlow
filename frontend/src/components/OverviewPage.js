import React from 'react';
import WorkspaceLayout from './workspace/WorkspaceLayout';
import WorkspaceGrid from './workspace/WorkspaceGrid';
import OverviewHeader from './workspace/OverviewHeader';
import UploadCard from './workspace/upload/UploadCard';
import SearchCard from './workspace/search/SearchCard';
import MetricsCard from './workspace/metrics/MetricsCard';
import RecentDocuments from './workspace/documents/RecentDocuments';
import ActivityTimeline from './workspace/timeline/ActivityTimeline';

/**
 * Pure declarative composition root for the AI Document Ingestion Workspace.
 */
export const OverviewPage = () => {
  return (
    <WorkspaceLayout>
      <OverviewHeader />
      
      <WorkspaceGrid cols={3}>
        <UploadCard />
        <SearchCard />
        <MetricsCard />
      </WorkspaceGrid>
      
      <WorkspaceGrid cols={2}>
        <RecentDocuments />
        <ActivityTimeline />
      </WorkspaceGrid>
    </WorkspaceLayout>
  );
};

export default OverviewPage;
