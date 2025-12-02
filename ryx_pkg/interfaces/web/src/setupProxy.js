/**
 * Proxy configuration for React development server
 * Only proxies /api/* requests to backend
 * Static assets are served by React dev server (not proxied)
 */

const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Only proxy API requests, not static assets
  app.use(
    '/api',
    createProxyMiddleware({
      target: process.env.REACT_APP_API_URL || 'http://localhost:8000',
      changeOrigin: true,
      // Don't proxy errors - let them be handled by the app
      onError: (err, req, res) => {
        console.warn('Proxy error (backend may be down):', err.message);
        // Don't send response - let React handle it
        // This prevents proxy errors from crashing the app
      },
      // Handle proxy errors gracefully
      onProxyReq: (proxyReq, req, res) => {
        // Add timeout to prevent hanging
        proxyReq.setTimeout(5000, () => {
          proxyReq.destroy();
        });
      },
      // Log proxy errors but don't crash
      logLevel: 'warn',
      // Don't rewrite paths - keep /api prefix
      pathRewrite: {
        '^/api': '/api', // Keep /api in the path
      },
    })
  );
};

