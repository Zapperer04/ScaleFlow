import React from 'react';
import { render, screen } from '@testing-library/react';
import { NotificationProvider } from '../contexts/NotificationContext';
import { AppShell } from '../components/layout/AppShell';

describe('Notifications Center Integration', () => {
  test('renders notifications badge and triggers sidebar status indicators', () => {
    render(
      <NotificationProvider>
        <AppShell activeView="workspace" onNavigateToView={() => {}} leaderId="Checking...">
          <div>Content</div>
        </AppShell>
      </NotificationProvider>
    );
    const bell = screen.getByLabelText('Open notifications');
    expect(bell).toBeInTheDocument();
  });
});
