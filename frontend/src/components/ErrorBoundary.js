import { Component } from 'react';
import './ErrorBoundary.css';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="eb-wrap">
          <div className="eb-card">
            <div className="eb-icon">!</div>
            <h2 className="eb-title">Something went wrong</h2>
            <p className="eb-msg">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              className="eb-btn"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}