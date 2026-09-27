import React from 'react';
import { render, screen } from '@testing-library/react';
import { WorkspaceHome } from '../pages/WorkspaceHome';
import { DocumentProvider } from '../contexts/DocumentContext';
import { PipelineProvider } from '../contexts/PipelineContext';
import { WorkspaceProvider } from '../contexts/WorkspaceContext';

import { NotificationProvider } from '../contexts/NotificationContext';

describe('Workspace State Machine Integration', () => {
  test('renders upload document workspace when no document is selected', () => {
    render(
      <NotificationProvider>
        <DocumentProvider>
          <PipelineProvider>
            <WorkspaceProvider>
              <WorkspaceHome />
            </WorkspaceProvider>
          </PipelineProvider>
        </DocumentProvider>
      </NotificationProvider>
    );
    const uploadTitle = screen.getByText('Upload a Document');
    expect(uploadTitle).toBeInTheDocument();
  });
});
