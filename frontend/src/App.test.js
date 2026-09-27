import { render, screen } from '@testing-library/react';
import React from 'react';

jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }) => <div>{children}</div>,
  Routes: ({ children }) => <div>{children}</div>,
  Route: ({ element }) => <div>{element}</div>,
  Navigate: () => null,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/' }),
}));

import App from './App';

test('renders ScaleFlow branding', () => {
  render(<App />);
  const brandingElements = screen.getAllByText(/ScaleFlow/i);
  expect(brandingElements.length).toBeGreaterThan(0);
});
