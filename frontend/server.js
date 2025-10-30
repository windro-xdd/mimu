const http = require('http');

const HOST = '0.0.0.0';
const PORT = parseInt(process.env.FRONTEND_PORT || process.env.PORT || '3000', 10);
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const ALLOWED_ORIGINS = process.env.CORS_ALLOWED_ORIGINS || '*';

const sendJson = (res, statusCode, payload) => {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS,
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Credentials': process.env.CORS_ALLOW_CREDENTIALS || 'true',
  });
  res.end(body);
};

const sendHtml = (res, statusCode, html) => {
  res.writeHead(statusCode, {
    'Content-Type': 'text/html; charset=utf-8',
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS,
  });
  res.end(html);
};

const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': ALLOWED_ORIGINS,
      'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': process.env.CORS_ALLOW_CREDENTIALS || 'true',
    });
    res.end();
    return;
  }

  if (req.url === '/' || req.url === '/index.html') {
    const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Frontend Placeholder</title>
    <style>
      body { font-family: system-ui, sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1.5rem; }
      pre { background: #f5f5f5; padding: 1rem; border-radius: 0.75rem; }
      code { font-family: "Fira Code", "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
  </head>
  <body>
    <h1>Frontend scaffold online</h1>
    <p>This lightweight Node.js server is a stand-in until the real frontend application is ready.</p>
    <p>It forwards development traffic to the backend running at <code>${API_BASE_URL}</code>.</p>
    <pre>
Try the following endpoints:
- <a href="/healthz">/healthz</a>
- <a href="/api">/api</a>
    </pre>
  </body>
</html>`;
    sendHtml(res, 200, html);
    return;
  }

  if (req.url === '/health' || req.url === '/healthz') {
    sendJson(res, 200, {
      status: 'ok',
      service: 'frontend',
      apiBaseUrl: API_BASE_URL,
    });
    return;
  }

  if (req.url === '/api') {
    sendJson(res, 200, {
      message: 'Future frontend assets will proxy API calls to this backend base URL.',
      apiBaseUrl: API_BASE_URL,
    });
    return;
  }

  sendJson(res, 404, { detail: 'Not found' });
});

server.listen(PORT, HOST, () => {
  process.stdout.write(`Frontend placeholder server listening on http://${HOST}:${PORT}\n`);
});
