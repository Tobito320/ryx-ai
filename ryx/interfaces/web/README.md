# Ryx Web Interface

React-based web interface for Ryx AI.

## Prerequisites

- Node.js (v18 or higher recommended)
- npm

## Getting Started

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm start
```

This starts the development server at `http://localhost:3000`.

### Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Testing

### Run Tests Locally

```bash
npm test
```

This runs tests in interactive watch mode. Press `a` to run all tests, or `q` to quit.

### Run Tests in CI

```bash
npm run test:ci
```

This runs tests once without watch mode, suitable for CI/CD pipelines.

## Project Structure

```
ryx/interfaces/web/
├── public/          # Static assets
├── src/             # React source files
├── package.json     # Dependencies and scripts
├── tailwind.config.js
├── postcss.config.js
└── tsconfig.json    # TypeScript configuration
```
