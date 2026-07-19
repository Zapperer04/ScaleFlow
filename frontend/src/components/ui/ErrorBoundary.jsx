import React from 'react';
import ErrorState from './ErrorState';

/**
 * ErrorBoundary React class component to isolate sub-page crashes.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught a runtime crash:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 'var(--spacing-32)' }}>
          <ErrorState
            title="Workspace component crash"
            message={this.state.error?.message || 'A runtime rendering error occurred inside this page component.'}
            onRetry={() => this.setState({ hasError: false, error: null })}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
