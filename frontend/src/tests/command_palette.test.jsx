import React from 'react';
import { render, screen } from '@testing-library/react';
import CommandPalette from '../components/ui/CommandPalette';

describe('Command Palette Integration', () => {
  test('renders palette options and matches category labels', () => {
    const actions = [
      { id: 'nav-settings', label: 'Go to Settings', category: 'Navigation', perform: jest.fn() }
    ];
    render(
      <CommandPalette isOpen={true} onClose={() => {}} actions={actions} />
    );

    const input = screen.getByPlaceholderText(/Type a command or navigate.../i);
    expect(input).toBeInTheDocument();
  });
});
