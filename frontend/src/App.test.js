import { render, screen } from '@testing-library/react';
import App from './App';

test('renders ScaleFlow branding', () => {
  render(<App />);
  const brandingElement = screen.getByText(/ScaleFlow/i);
  expect(brandingElement).toBeInTheDocument();
});
