# Resume Tailor Agent - Frontend

React-based frontend application for the Resume Tailor Agent.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Routing
- **TanStack Query** - Data fetching and caching
- **Tailwind CSS** - Styling
- **React Hot Toast** - Notifications
- **React Dropzone** - File uploads

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   │   ├── common/     # Header, Footer, Loading, etc.
│   │   ├── upload/     # Upload-related components
│   │   ├── results/    # Results display components
│   │   └── ...
│   ├── pages/          # Page components
│   ├── services/       # API service functions
│   ├── hooks/          # Custom React hooks
│   ├── utils/          # Utility functions
│   └── App.tsx         # Main app component
├── public/             # Static assets
├── package.json
└── vite.config.ts
```

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set environment variables:**
   Create `.env` file:
   ```
   VITE_API_URL=http://localhost:8000
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Build for production:**
   ```bash
   npm run build
   ```

## Features

### Main Features
- ✅ Resume and JD file upload (drag & drop)
- ✅ Text input for JD
- ✅ Real-time job status polling
- ✅ ATS score visualization
- ✅ Skill gap analysis
- ✅ Resume preview (before/after)
- ✅ Multiple download formats (DOCX, PDF, TXT, ZIP)
- ✅ Resume management dashboard
- ✅ Batch processing for multiple JDs
- ✅ Template selection and customization
- ✅ Version history and comparison

### Pages
- **Home** - Landing page with features
- **Upload** - Main upload and tailoring page
- **Results** - Display tailoring results
- **Dashboard** - Resume management
- **Batch** - Batch processing interface
- **Templates** - Template gallery and customization

## API Integration

All API calls are centralized in `src/services/api.ts`. The frontend connects to the backend API at `http://localhost:8000` by default.

## Styling

Uses Tailwind CSS for styling. Configuration in `tailwind.config.js`.

## Development

- Hot module replacement enabled
- TypeScript for type safety
- ESLint for code quality
- React Query for efficient data fetching

## Deployment

Build the production bundle:
```bash
npm run build
```

The `dist/` folder contains the production-ready files that can be served by any static file server.
