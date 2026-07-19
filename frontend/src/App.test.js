import { render, screen } from '@testing-library/react';
import App from './App';

test('renders ScaleFlow branding', () => {
  render(<App />);
  const brandingElements = screen.getAllByText(/ScaleFlow/i);
  expect(brandingElements.length).toBeGreaterThan(0);
});
