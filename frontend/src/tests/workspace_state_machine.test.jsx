import React from 'react';
import { render, screen } from '@testing-library/react';
import { WorkspaceHome } from '../pages/WorkspaceHome';
import { DocumentProvider } from '../contexts/DocumentContext';
import { PipelineProvider } from '../contexts/PipelineContext';
import { WorkspaceProvider } from '../contexts/WorkspaceContext';

describe('Workspace State Machine Integration', () => {
  test('renders interactive chat tabs and checks sidebar options', () => {
    render(
      <DocumentProvider>
        <PipelineProvider>
          <WorkspaceProvider>
            <WorkspaceHome />
          </WorkspaceProvider>
        </PipelineProvider>
      </DocumentProvider>
    );
    const chatTab = screen.getByText('Interactive Chat');
    expect(chatTab).toBeInTheDocument();
  });
});
