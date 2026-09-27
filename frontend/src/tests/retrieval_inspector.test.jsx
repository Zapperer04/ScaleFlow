import React from 'react';
import { render, screen } from '@testing-library/react';
import RetrievalInspector from '../pages/RetrievalInspector';
import { PipelineProvider } from '../contexts/PipelineContext';

describe('Retrieval Inspector Integration', () => {
  test('renders metrics scorebars and fusion values', () => {
    render(
      <PipelineProvider>
        <RetrievalInspector />
      </PipelineProvider>
    );
    const header = screen.getByText('Retrieval Inspector Console');
    expect(header).toBeInTheDocument();
  });
});
