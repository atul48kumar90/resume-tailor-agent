# Resume Tailor Agent - UI Design Document

## Overview
A modern, user-friendly React application for tailoring resumes to job descriptions with AI-powered ATS optimization.

## Main User Flow

### 1. Landing/Upload Page
**Primary Action:** Upload JD + Resume → Get Tailored Resume

**Features:**
- Drag & drop file uploads for JD and Resume
- Text input option for JD
- Recruiter persona selector (general, technical, executive, etc.)
- Real-time file validation
- Progress indicator during processing

### 2. Results Dashboard
**Shows:**
- Before/After ATS Score comparison
- Skill gap analysis
- Missing keywords highlighted
- Tailored resume preview
- Download options (DOCX, PDF, TXT, ZIP)

### 3. Resume Management
**Features:**
- Saved resumes list
- Applications tracking
- Version history with visual diff
- Template selection and customization

### 4. Batch Processing
**For active job seekers:**
- Upload resume once
- Process multiple JDs simultaneously
- Compare results side-by-side

## UI Components Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   └── ProgressBar.tsx
│   │   ├── upload/
│   │   │   ├── UploadPage.tsx
│   │   │   ├── JDUpload.tsx
│   │   │   ├── ResumeUpload.tsx
│   │   │   └── PersonaSelector.tsx
│   │   ├── results/
│   │   │   ├── ResultsDashboard.tsx
│   │   │   ├── ATSScoreCard.tsx
│   │   │   ├── SkillGapAnalysis.tsx
│   │   │   ├── ResumePreview.tsx
│   │   │   └── DownloadButtons.tsx
│   │   ├── resume-management/
│   │   │   ├── ResumeList.tsx
│   │   │   ├── ResumeCard.tsx
│   │   │   ├── ApplicationTracker.tsx
│   │   │   └── VersionHistory.tsx
│   │   ├── batch/
│   │   │   ├── BatchUpload.tsx
│   │   │   └── BatchResults.tsx
│   │   └── templates/
│   │       ├── TemplateSelector.tsx
│   │       └── TemplateCustomizer.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── UploadPage.tsx
│   │   ├── ResultsPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── BatchPage.tsx
│   │   └── TemplatesPage.tsx
│   ├── services/
│   │   └── api.ts
│   ├── hooks/
│   │   ├── useJobStatus.ts
│   │   └── useResumeData.ts
│   ├── utils/
│   │   └── formatters.ts
│   └── App.tsx
```

## Key Features Implementation

### 1. File Upload Component
- Drag & drop interface
- File type validation (PDF, DOCX, TXT)
- File size limits
- Preview uploaded files
- Support for both file and text input for JD

### 2. Job Status Polling
- Real-time job status updates
- Progress bar showing processing stages
- Auto-refresh when job completes
- Error handling and retry

### 3. ATS Score Visualization
- Circular progress indicator
- Before/After comparison
- Color-coded score (red/yellow/green)
- Detailed breakdown of score components

### 4. Skill Gap Analysis
- Visual list of missing skills
- Recommended skills to add
- Skill match percentage
- Categorized by importance

### 5. Resume Preview
- Side-by-side comparison (original vs tailored)
- Highlighted changes
- Section-by-section view
- Editable sections

### 6. Version Management
- Timeline view of versions
- Visual diff viewer
- Restore previous versions
- Compare any two versions

### 7. Template System
- Template gallery with previews
- Template recommendations based on role
- Customizable colors, fonts, layouts
- Live preview

## Design System

### Colors
- Primary: #2563EB (Blue)
- Success: #10B981 (Green)
- Warning: #F59E0B (Orange)
- Error: #EF4444 (Red)
- Background: #F9FAFB (Light Gray)
- Card: #FFFFFF (White)

### Typography
- Headings: Inter, Bold
- Body: Inter, Regular
- Code: Fira Code, Regular

### Components Style
- Modern, clean design
- Rounded corners (8px)
- Subtle shadows
- Smooth transitions
- Responsive grid layout

## API Integration Points

### Main Endpoints Used:
1. `POST /tailor` - Main tailoring endpoint
2. `GET /jobs/{job_id}` - Job status polling
3. `POST /ats/compare` - Get comparison data
4. `GET /ats/compare/{job_id}/skill-gap` - Skill gap analysis
5. `POST /ats/download` - Download tailored resume
6. `GET /resumes` - List saved resumes
7. `POST /resumes` - Save resume
8. `GET /resumes/{id}/versions` - Version history
9. `GET /ats/templates` - List templates
10. `POST /ats/batch` - Batch processing

## User Experience Flow

1. **Upload** → User uploads JD and Resume
2. **Processing** → Show progress, poll job status
3. **Results** → Display ATS score, skill gap, preview
4. **Review** → User reviews tailored resume
5. **Download** → User downloads in preferred format
6. **Save** → Optionally save to resume library
7. **Track** → Track application status

## Responsive Design
- Mobile-first approach
- Breakpoints: 640px, 768px, 1024px, 1280px
- Touch-friendly file uploads
- Collapsible sections on mobile

