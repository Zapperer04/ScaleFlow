import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationProvider } from '../contexts/NotificationContext';
import { PipelineProvider } from '../contexts/PipelineContext';
import { DocumentProvider } from '../contexts/DocumentContext';
import { AppShell } from '../components/layout/AppShell';

describe('Global Search Integration', () => {
  test('renders search trigger and input elements', () => {
    render(
      <NotificationProvider>
        <DocumentProvider>
          <PipelineProvider>
            <AppShell activeView="workspace" onNavigateToView={() => {}} leaderId="Checking...">
              <div>Workspace Content</div>
            </AppShell>
          </PipelineProvider>
        </DocumentProvider>
      </NotificationProvider>
    );

    const searchButton = screen.getByLabelText('Open global search');
    expect(searchButton).toBeInTheDocument();
  });
});
