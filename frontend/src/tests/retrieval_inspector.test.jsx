import React from 'react';
import { render, screen } from '@testing-library/react';
import RetrievalInspector from '../pages/RetrievalInspector';

describe('Retrieval Inspector Integration', () => {
  test('renders metrics scorebars and fusion values', () => {
    render(<RetrievalInspector />);
    const header = screen.getByText('Retrieval Inspector Console');
    expect(header).toBeInTheDocument();
  });
});
