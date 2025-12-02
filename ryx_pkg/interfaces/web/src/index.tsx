import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import ErrorBoundary from './components/ErrorBoundary';
import GlobalErrorHandler from './components/GlobalErrorHandler';
import { SearchProviderContext } from './contexts/SearchContext';

// Setup global error handlers before rendering
// This catches errors that happen during initial render
if (typeof window !== 'undefined') {
  // Prevent default error handling that shows browser error pages
  window.addEventListener('error', (event) => {
    // Only prevent default for non-resource errors
    if (!event.target || (event.target as HTMLElement).tagName === 'SCRIPT') {
      event.preventDefault();
    }
  });

  window.addEventListener('unhandledrejection', (event) => {
    event.preventDefault();
  });
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

// Wrap in try-catch to ensure app always renders
try {
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <GlobalErrorHandler>
          <SearchProviderContext>
            <App />
          </SearchProviderContext>
        </GlobalErrorHandler>
      </ErrorBoundary>
    </React.StrictMode>
  );
} catch (error) {
  // Fallback render if initial render fails
  console.error('Failed to render app:', error);
  root.render(
    <div style={{ 
      padding: '20px', 
      fontFamily: 'sans-serif',
      backgroundColor: '#1a1a1a',
      color: '#fff',
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ textAlign: 'center', maxWidth: '500px' }}>
        <h1 style={{ color: '#ef4444', marginBottom: '16px' }}>Application Error</h1>
        <p style={{ marginBottom: '16px' }}>
          The application encountered an error during startup. Please refresh the page.
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '10px 20px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Refresh Page
        </button>
      </div>
    </div>
  );
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
