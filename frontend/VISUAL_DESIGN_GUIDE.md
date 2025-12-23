# Visual Design Guide - Resume Tailor Agent

## Design System Overview

### Color Palette

**Primary Colors:**
- Primary Blue: `#2563EB` - Main actions, links, highlights
- Primary Blue Light: `#3B82F6` - Hover states
- Primary Blue Dark: `#1D4ED8` - Active states

**Semantic Colors:**
- Success Green: `#10B981` - Success messages, high scores (80+)
- Warning Orange: `#F59E0B` - Warnings, medium scores (60-79)
- Error Red: `#EF4444` - Errors, low scores (<60), missing items

**Neutral Colors:**
- Background: `#F9FAFB` - Page background
- Card: `#FFFFFF` - Card backgrounds
- Border: `#E5E7EB` - Borders, dividers
- Text Primary: `#111827` - Headings, important text
- Text Secondary: `#6B7280` - Body text, descriptions
- Text Muted: `#9CA3AF` - Placeholders, helper text

### Typography

**Font Family:** Inter (system fallback: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto)

**Font Sizes:**
- Hero: 48px (3rem) - Bold
- H1: 36px (2.25rem) - Bold
- H2: 30px (1.875rem) - Semibold
- H3: 24px (1.5rem) - Semibold
- Body: 16px (1rem) - Regular
- Small: 14px (0.875rem) - Regular
- XS: 12px (0.75rem) - Regular

### Spacing

- Base unit: 4px
- Common spacing: 8px, 12px, 16px, 24px, 32px, 48px

### Border Radius

- Small: 4px (rounded)
- Medium: 8px (rounded-lg)
- Large: 12px (rounded-xl)
- Full: 9999px (rounded-full)

### Shadows

- Small: `0 1px 2px 0 rgba(0, 0, 0, 0.05)`
- Medium: `0 4px 6px -1px rgba(0, 0, 0, 0.1)`
- Large: `0 10px 15px -3px rgba(0, 0, 0, 0.1)`

## Component Specifications

### Buttons

**Primary Button:**
- Background: `#2563EB`
- Text: White
- Padding: `12px 24px`
- Border radius: `8px`
- Font: Medium, 16px
- Hover: Background `#1D4ED8`
- Disabled: Background `#9CA3AF`, cursor not-allowed

**Secondary Button:**
- Background: Transparent
- Border: 1px solid `#D1D5DB`
- Text: `#374151`
- Hover: Background `#F3F4F6`

### Cards

- Background: White
- Border radius: `8px`
- Shadow: Medium
- Padding: `24px`
- Hover: Shadow increases slightly

### Input Fields

- Border: 1px solid `#D1D5DB`
- Border radius: `6px`
- Padding: `12px 16px`
- Focus: 2px ring `#2563EB`, border becomes `#2563EB`
- Placeholder: `#9CA3AF`

### File Upload Areas

- Border: 2px dashed `#D1D5DB`
- Background: `#F9FAFB`
- Border radius: `8px`
- Padding: `32px`
- Hover: Border `#2563EB`, background `#EFF6FF`
- Active (drag over): Border `#1D4ED8`, background `#DBEAFE`

## Page Layouts

### 1. Home Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header (White, shadow-sm)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Hero Section (Gradient Blue Background)                       │
│ ┌─────────────────────────────────────────────────────┐   │
│ │                                                       │   │
│ │        Tailor Your Resume to Any Job                 │   │
│ │        (48px, Bold, White)                           │   │
│ │                                                       │   │
│ │        AI-powered resume optimization...             │   │
│ │        (20px, Regular, Blue-100)                     │   │
│ │                                                       │   │
│ │        [Get Started Button]                          │   │
│ │        (White bg, Blue text, 20px padding)           │   │
│ │                                                       │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
│ Features Section (White Background)                           │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│ │ 📊 Icon      │  │ ✅ Icon      │  │ 📦 Icon      │      │
│ │ ATS          │  │ Skill Gap    │  │ Batch        │      │
│ │ Optimization│  │ Analysis     │  │ Processing   │      │
│ │              │  │              │  │              │      │
│ │ Description  │  │ Description  │  │ Description  │      │
│ └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│ CTA Section (Gray-100 Background)                            │
│ ┌─────────────────────────────────────────────────────┐   │
│ │        Ready to Optimize Your Resume?                │   │
│ │        [Start Tailoring Button]                     │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Upload Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header                                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Card (White, shadow-md, rounded-lg, p-8)             │   │
│ │                                                       │   │
│ │ Tailor Your Resume (H1, 36px, Bold)                  │   │
│ │ Subtitle (16px, Gray-600)                            │   │
│ │                                                       │   │
│ │ Resume *                                              │   │
│ │ ┌─────────────────────────────────────────────┐   │   │
│ │ │ File Upload Area (Dashed border)             │   │   │
│ │ │ - Icon (48px, Gray-400)                      │   │   │
│ │ │ - "Click to upload or drag and drop"         │   │   │
│ │ │ - File type hint                              │   │   │
│ │ │ - Max size hint                               │   │   │
│ │ └─────────────────────────────────────────────┘   │   │
│ │                                                       │   │
│ │ Job Description *                                     │   │
│ │ [Upload File] [Paste Text] ← Toggle buttons         │   │
│ │                                                       │   │
│ │ ┌─────────────────────────────────────────────┐   │   │
│ │ │ Textarea or File Upload                      │   │   │
│ │ └─────────────────────────────────────────────┘   │   │
│ │                                                       │   │
│ │ Recruiter Persona                                   │   │
│ │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                │   │
│ │ │General│ │Tech  │ │Exec  │ │Creat │                │   │
│ │ └──────┘ └──────┘ └──────┘ └──────┘                │   │
│ │                                                       │   │
│ │ [Tailor Resume] ← Full width, Blue button           │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3. Results Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header                                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Results Header Card                                   │   │
│ │ "Resume Tailoring Results" (H1)                      │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ ATS Score Comparison Card                            │   │
│ │                                                       │   │
│ │ Before Optimization    After Optimization             │   │
│ │      ┌─────┐              ┌─────┐                   │   │
│ │      │ 45  │              │ 87  │                   │   │
│ │      └─────┘              └─────┘                   │   │
│ │      (Red circle)         (Green circle)              │   │
│ │                                                       │   │
│ │        ⬆ +42 points (93% improvement)                │   │
│ │        (Blue badge with arrow icon)                  │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Skill Gap Analysis Card                              │   │
│ │                                                       │   │
│ │ Skill Match: 75% ████████░░                          │   │
│ │                                                       │   │
│ │ Missing Skills (3)                                    │   │
│ │ [Kubernetes] [AWS] [Docker]                          │   │
│ │ (Red tags)                                            │   │
│ │                                                       │   │
│ │ Recommended Skills                                    │   │
│ │ [CI/CD] [Microservices] [Redis]                     │   │
│ │ (Green tags)                                          │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Resume Preview Card                                  │   │
│ │ [Original] [Compare] [Tailored] ← Tabs              │   │
│ │ ┌─────────────────────────────────────────────┐   │   │
│ │ │ Resume content in formatted text             │   │   │
│ │ │ (Monospace font, gray background)            │   │   │
│ │ └─────────────────────────────────────────────┘   │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Download Section                                      │   │
│ │ ┌────┐ ┌────┐ ┌────┐ ┌────┐                         │   │
│ │ │DOCX│ │PDF │ │TXT │ │ZIP │                         │   │
│ │ │Icon│ │Icon│ │Icon│ │Icon│                         │   │
│ │ └────┘ └────┘ └────┘ └────┘                         │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Visual Mockup Descriptions

### Mockup 1: Home Page
**Visual Description:**
- Full-width hero section with gradient blue background (from #2563EB to #1E40AF)
- Large white text: "Tailor Your Resume to Any Job" centered
- Subtitle in lighter blue
- Prominent white "Get Started" button with shadow
- Three feature cards in a row below hero
- Each card: White background, icon in colored circle, title, description
- Bottom CTA section with gray background

### Mockup 2: Upload Page
**Visual Description:**
- Clean white card centered on page
- Large title at top
- Two file upload areas with dashed borders
- First upload: Resume (required, red asterisk)
- Second upload: Job description with toggle buttons
- Persona selector: Four radio button cards in a grid
- Large blue submit button at bottom
- File previews shown below upload areas when selected

### Mockup 3: Results Page
**Visual Description:**
- Multiple white cards stacked vertically
- First card: Header with title
- Second card: Two large circular score indicators side-by-side
  - Left: Red circle with "45" (before)
  - Right: Green circle with "87" (after)
  - Improvement badge below with blue background
- Third card: Skill gap with progress bar
  - Red tags for missing skills
  - Green tags for recommended skills
- Fourth card: Resume preview with tabs
  - Monospace font, gray background
  - Side-by-side comparison option
- Fifth card: Four download buttons in a grid
  - Each with icon and format label
  - Hover effects

### Mockup 4: Dashboard Page
**Visual Description:**
- Header with "My Resumes" title and "+ New Resume" button
- Grid of resume cards (2-3 columns)
- Each card: White, shadow, rounded corners
  - Title at top
  - Creation date
  - Tags as small badges
  - Application count
  - Action buttons at bottom
- Empty state: Centered message with CTA button

## Interactive Elements

### Hover States
- Buttons: Slightly darker background
- Cards: Increased shadow
- Links: Underline or color change
- File upload areas: Border color change, background tint

### Loading States
- Spinner animation (rotating circle)
- Disabled buttons with gray background
- Skeleton loaders for content

### Success States
- Green checkmark icons
- Success toast notifications (top-right)
- Green highlights on improved metrics

### Error States
- Red error messages
- Red borders on invalid inputs
- Error toast notifications

## Responsive Breakpoints

- Mobile: < 640px
  - Single column layout
  - Stacked cards
  - Full-width buttons
  - Collapsed navigation

- Tablet: 640px - 1024px
  - 2-column grids
  - Side-by-side comparisons
  - Horizontal navigation

- Desktop: > 1024px
  - 3-4 column grids
  - Full feature set
  - Optimal spacing

## Accessibility

- Color contrast ratios meet WCAG AA standards
- Keyboard navigation support
- Screen reader friendly labels
- Focus indicators on all interactive elements
- Alt text for all icons and images

