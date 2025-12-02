/**
 * @file ryx/interfaces/web/src/__tests__/ToolResults.test.tsx
 * @description Unit tests for ToolResults component.
 * 
 * Tests:
 * - Renders without crashing
 * - Displays tool results with correct formatting
 * - Handles different tool types (search_local, search_web, edit_file, launch_app)
 * - Shows streaming updates
 * - Allows retry on failed results
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import ToolResults, { ToolResult, FileResult, UrlResult, DiffResult, LaunchResult } from '../components/ToolResults';
import { WorkflowEvent } from '../hooks/useWorkflowWebsocket';

describe('ToolResults', () => {
  const createMockResult = (overrides: Partial<ToolResult> = {}): ToolResult => ({
    id: `result-${Math.random().toString(36).substr(2, 9)}`,
    toolName: 'search_local',
    status: 'success',
    latency: 100,
    timestamp: new Date(),
    ...overrides,
  });

  it('renders without crashing', () => {
    render(<ToolResults />);
    expect(screen.getByTestId('tool-results')).toBeInTheDocument();
  });

  it('displays header with title', () => {
    render(<ToolResults />);
    expect(screen.getByText('Tool Results')).toBeInTheDocument();
  });

  it('displays empty state when no results', () => {
    render(<ToolResults results={[]} />);
    expect(screen.getByText('No tool results to display')).toBeInTheDocument();
  });

  it('displays result count', () => {
    const results = [createMockResult(), createMockResult()];
    render(<ToolResults results={results} />);
    expect(screen.getByText('2 results')).toBeInTheDocument();
  });

  it('shows loading indicator when isLoading is true', () => {
    render(<ToolResults isLoading={true} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders search_local tool results', () => {
    const fileResults: FileResult[] = [
      { path: '/home/user/file.txt', name: 'file.txt', type: 'file', size: 1024 },
      { path: '/home/user/folder', name: 'folder', type: 'directory' },
    ];

    const results = [
      createMockResult({
        toolName: 'search_local',
        output: fileResults,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Local Search')).toBeInTheDocument();
    expect(screen.getByText('file.txt')).toBeInTheDocument();
    expect(screen.getByText('/home/user/file.txt')).toBeInTheDocument();
    expect(screen.getByText('folder')).toBeInTheDocument();
    expect(screen.getByText('1.0KB')).toBeInTheDocument();
  });

  it('renders search_web tool results as URL cards', () => {
    const urlResults: UrlResult[] = [
      { url: 'https://example.com', title: 'Example Site', snippet: 'This is an example' },
      { url: 'https://test.com', title: 'Test Site' },
    ];

    const results = [
      createMockResult({
        toolName: 'search_web',
        output: urlResults,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Web Search')).toBeInTheDocument();
    expect(screen.getByText('Example Site')).toBeInTheDocument();
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
    expect(screen.getByText('This is an example')).toBeInTheDocument();
    expect(screen.getByText('Test Site')).toBeInTheDocument();
  });

  it('renders edit_file tool results with diff', () => {
    const diffResult: DiffResult = {
      path: 'src/App.tsx',
      additions: 5,
      deletions: 2,
      diff: '@@ -1,3 +1,6 @@\n+import React from "react";\n function App() {\n-  return null;\n+  return <div>Hello</div>;\n }',
    };

    const results = [
      createMockResult({
        toolName: 'edit_file',
        output: diffResult,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('File Editor')).toBeInTheDocument();
    expect(screen.getByText('src/App.tsx')).toBeInTheDocument();
    expect(screen.getByText('+5')).toBeInTheDocument();
    expect(screen.getByText('-2')).toBeInTheDocument();
  });

  it('renders launch_app tool results', () => {
    const launchResult: LaunchResult = {
      appName: 'Firefox',
      pid: 12345,
      status: 'running',
      message: 'Browser started successfully',
    };

    const results = [
      createMockResult({
        toolName: 'launch_app',
        output: launchResult,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('App Launcher')).toBeInTheDocument();
    expect(screen.getByText('Firefox')).toBeInTheDocument();
    expect(screen.getByText(/Running/)).toBeInTheDocument();
    expect(screen.getByText(/PID: 12345/)).toBeInTheDocument();
    expect(screen.getByText('Browser started successfully')).toBeInTheDocument();
  });

  it('renders string output for generic tools', () => {
    const results = [
      createMockResult({
        toolName: 'unknown',
        output: 'Simple string output',
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Simple string output')).toBeInTheDocument();
  });

  it('displays error message for failed results', () => {
    const results = [
      createMockResult({
        status: 'failed',
        error: 'Tool execution failed: File not found',
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Tool execution failed: File not found')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows retry button for failed results when onRetry is provided', () => {
    const onRetryMock = jest.fn();
    const results = [
      createMockResult({
        id: 'failed-result',
        status: 'failed',
        error: 'Error occurred',
      }),
    ];

    render(<ToolResults results={results} onRetry={onRetryMock} />);
    
    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeInTheDocument();
    
    fireEvent.click(retryButton);
    expect(onRetryMock).toHaveBeenCalledWith('failed-result');
  });

  it('shows processing indicator for running status', () => {
    const results = [
      createMockResult({
        status: 'running',
        output: undefined,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Running...')).toBeInTheDocument();
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('shows latency for completed results', () => {
    const results = [
      createMockResult({
        latency: 250,
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('250ms')).toBeInTheDocument();
  });

  it('displays correct status colors', () => {
    const successResult = createMockResult({ id: 'success', status: 'success' });
    const failedResult = createMockResult({ id: 'failed', status: 'failed' });
    const runningResult = createMockResult({ id: 'running', status: 'running' });
    const pendingResult = createMockResult({ id: 'pending', status: 'pending' });

    render(<ToolResults results={[successResult, failedResult, runningResult, pendingResult]} />);
    
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Running...')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('calls onResultClick when result is clicked', () => {
    const onResultClickMock = jest.fn();
    const results = [createMockResult({ id: 'clickable-result' })];

    render(<ToolResults results={results} onResultClick={onResultClickMock} />);
    
    // Find the result container and click it
    const resultElement = screen.getByTestId(`tool-result-${results[0].id}`);
    fireEvent.click(resultElement);
    
    expect(onResultClickMock).toHaveBeenCalledWith(results[0]);
  });

  it('subscribes to workflow events when subscribe is provided', () => {
    const mockSubscribe = jest.fn((callback) => {
      return jest.fn(); // unsubscribe
    });

    render(<ToolResults subscribe={mockSubscribe} />);
    
    expect(mockSubscribe).toHaveBeenCalled();
  });

  it('limits displayed results to maxResults', () => {
    const results = Array.from({ length: 30 }, (_, i) =>
      createMockResult({ id: `result-${i}`, output: `Output ${i}` })
    );

    render(<ToolResults results={results} maxResults={5} />);
    
    // Should only show last 5 results
    expect(screen.queryByText('Output 0')).not.toBeInTheDocument();
    expect(screen.queryByText('Output 24')).not.toBeInTheDocument();
    expect(screen.getByText('Output 25')).toBeInTheDocument();
    expect(screen.getByText('Output 29')).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    render(<ToolResults className="custom-class" />);
    const toolResults = screen.getByTestId('tool-results');
    
    expect(toolResults).toHaveClass('custom-class');
    expect(toolResults).toHaveClass('bg-[#282a36]');
    expect(toolResults).toHaveClass('rounded-lg');
    expect(toolResults).toHaveClass('border');
    expect(toolResults).toHaveClass('border-[#6272a4]');
  });

  it('displays streaming indicator when result is streaming', () => {
    const results = [
      createMockResult({
        streaming: true,
        status: 'running',
      }),
    ];

    render(<ToolResults results={results} />);
    
    expect(screen.getByText('Streaming')).toBeInTheDocument();
  });

  it('renders tool icons correctly', () => {
    const results = [
      createMockResult({ toolName: 'search_local' }),
      createMockResult({ toolName: 'search_web' }),
      createMockResult({ toolName: 'edit_file' }),
      createMockResult({ toolName: 'launch_app' }),
    ];

    render(<ToolResults results={results} />);
    
    // Check that tool names are displayed
    expect(screen.getByText('Local Search')).toBeInTheDocument();
    expect(screen.getByText('Web Search')).toBeInTheDocument();
    expect(screen.getByText('File Editor')).toBeInTheDocument();
    expect(screen.getByText('App Launcher')).toBeInTheDocument();
  });
});
