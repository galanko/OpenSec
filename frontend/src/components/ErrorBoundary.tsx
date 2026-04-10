import { Component, type ErrorInfo, type ReactNode } from 'react'
import ErrorState from './ErrorState'

interface ErrorBoundaryProps {
  children: ReactNode
  fallbackTitle?: string
  fallbackSubtitle?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          title={this.props.fallbackTitle ?? 'Something went wrong'}
          subtitle={this.props.fallbackSubtitle ?? 'An unexpected error occurred. Please try again.'}
          onRetry={this.handleRetry}
          retryLabel="Reload page"
        />
      )
    }
    return this.props.children
  }
}
