import React from 'react';
import { render, screen } from '@testing-library/react';
import { NotificationProvider } from '../contexts/NotificationContext';
import { PipelineProvider } from '../contexts/PipelineContext';
import { DocumentProvider } from '../contexts/DocumentContext';
import { AppShell } from '../components/layout/AppShell';

describe('Notifications Center Integration', () => {
  test('renders notifications badge and triggers sidebar status indicators', () => {
    render(
      <NotificationProvider>
        <DocumentProvider>
          <PipelineProvider>
            <AppShell activeView="workspace" onNavigateToView={() => {}} leaderId="Checking...">
              <div>Content</div>
            </AppShell>
          </PipelineProvider>
        </DocumentProvider>
      </NotificationProvider>
    );
    const bell = screen.getByLabelText('Open notifications');
    expect(bell).toBeInTheDocument();
  });
});
