# Frontend Setup Guide

## Quick Start

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   echo "VITE_API_URL=http://localhost:8000" > .env
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open in browser:**
   ```
   http://localhost:3000
   ```

## Project Structure

```
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── common/       # Header, Footer, Loading, etc.
│   │   ├── upload/       # File upload components
│   │   └── results/      # Results display components
│   ├── pages/            # Page components (routes)
│   ├── services/         # API service functions
│   ├── hooks/            # Custom React hooks
│   └── utils/            # Utility functions
├── public/               # Static assets
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind CSS config
└── tsconfig.json        # TypeScript config
```

## Features Implemented

✅ **Complete React Application Structure**
- React Router for navigation
- TanStack Query for data fetching
- TypeScript for type safety
- Tailwind CSS for styling

✅ **Pages Created:**
- HomePage - Landing page with features
- UploadPage - Main upload interface
- ResultsPage - Display tailoring results
- DashboardPage - Resume management
- BatchPage - Batch processing
- TemplatesPage - Template gallery

✅ **Components Created:**
- FileUpload - Drag & drop file upload
- PersonaSelector - Recruiter persona selection
- ATSScoreCard - ATS score visualization
- SkillGapAnalysis - Skill gap display
- ResumePreview - Resume preview with comparison
- DownloadButtons - Multiple format downloads
- Header & Footer - Navigation
- LoadingSpinner - Loading states

✅ **API Integration:**
- Complete API service layer
- All backend endpoints integrated
- Error handling
- Type definitions

## Next Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start backend API** (in another terminal):
   ```bash
   cd ../backend
   ./scripts/start_api.sh
   ```

3. **Start frontend:**
   ```bash
   npm run dev
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Building for Production

```bash
npm run build
```

Output will be in `dist/` directory, ready to be served by any static file server.

## Visual Design

See `VISUAL_MOCKUPS.md` and `VISUAL_DESIGN_GUIDE.md` for detailed design specifications and mockups.

## Notes

- The frontend is configured to proxy API requests to `http://localhost:8000`
- All API calls are centralized in `src/services/api.ts`
- Components use Tailwind CSS utility classes
- TypeScript provides type safety throughout

