import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppShell } from '../components/layout/AppShell';
import { NotificationProvider } from '../contexts/NotificationContext';

describe('Global Search Integration', () => {
  test('renders search trigger and input elements', () => {
    render(
      <NotificationProvider>
        <AppShell activeView="workspace" onNavigateToView={() => {}} leaderId="Checking...">
          <div>Workspace Content</div>
        </AppShell>
      </NotificationProvider>
    );

    const searchButton = screen.getByLabelText('Open global search');
    expect(searchButton).toBeInTheDocument();
  });
});
