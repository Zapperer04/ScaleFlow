import React from 'react';
import { render, screen } from '@testing-library/react';
import ArtifactsExplorer from '../pages/ArtifactsExplorer';

describe('Artifact Explorer Integration', () => {
  test('renders JSON payload explorer files tree', () => {
    render(<ArtifactsExplorer />);
    const header = screen.getByText('WORKSPACE EXPLORER');
    expect(header).toBeInTheDocument();
  });
});
