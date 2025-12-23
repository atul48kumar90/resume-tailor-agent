# Visual Mockup Image Descriptions

This document provides detailed descriptions for creating visual mockup images of the Resume Tailor Agent UI.

## Image 1: Home Page Mockup

**Layout:**
- Full-width header bar (white, 64px height) with logo on left, navigation on right
- Hero section: Full-width gradient background (blue #2563EB to darker blue #1E40AF)
  - Centered content: Large white text "Tailor Your Resume to Any Job" (48px, bold)
  - Subtitle in lighter blue (#DBEAFE): "AI-powered resume optimization for maximum ATS compatibility"
  - Large white button with blue text: "Get Started" (20px padding, rounded corners)
- Features section: White background, three cards in a row
  - Each card: White background, shadow, rounded corners (8px)
  - Icon in colored circle (blue, green, purple) - 48px
  - Title: "ATS Optimization" / "Skill Gap Analysis" / "Batch Processing"
  - Description text below
- CTA section: Light gray background (#F3F4F6), centered text and button

**Colors:**
- Header: White (#FFFFFF)
- Hero: Gradient blue
- Features: White cards on white background
- Text: Dark gray (#111827) for headings, medium gray (#6B7280) for body

## Image 2: Upload Page Mockup

**Layout:**
- Same header as Home Page
- Centered white card (max-width: 896px, shadow, rounded-lg, padding: 32px)
- Title: "Tailor Your Resume" (36px, bold, dark gray)
- Subtitle: Gray text (16px)
- Form sections:
  1. Resume Upload:
     - Label: "Resume *" (red asterisk)
     - Large dashed border box (2px dashed, gray #D1D5DB)
     - Icon: Upload icon (48px, gray)
     - Text: "Click to upload or drag and drop"
     - File type hint: "PDF, DOCX, or TXT"
     - Max size: "Max size: 10MB"
  2. Job Description:
     - Toggle buttons: "Upload File" (active, blue) and "Paste Text" (gray)
     - Textarea: Large text input box (gray border, rounded)
  3. Persona Selector:
     - Four cards in a 2x2 grid
     - Each card: Border, rounded, padding
     - Selected card: Blue border, blue background tint
     - Radio button indicator
  4. Submit Button:
     - Full width, blue background, white text, large padding

**Visual Elements:**
- File upload areas have hover states (blue border when dragging)
- Selected files show below upload area with green checkmark
- Form validation indicators

## Image 3: Results Page Mockup

**Layout:**
- Same header
- Multiple white cards stacked vertically (spacing: 24px)
- Card 1: Header card - "Resume Tailoring Results" title
- Card 2: ATS Score Comparison
  - Two large circles side-by-side (128px diameter)
  - Left circle: Red background (#FEE2E2), red text (#DC2626), "45"
  - Right circle: Green background (#D1FAE5), green text (#059669), "87"
  - Below: Blue badge with arrow icon: "+42 points (93% improvement)"
  - Score breakdown table below
- Card 3: Skill Gap Analysis
  - Progress bar: Blue bar at 75% width
  - "Missing Skills" section: Red tags/badges
  - "Recommended Skills" section: Green tags/badges
- Card 4: Resume Preview
  - Tabs: "Original" | "Compare" | "Tailored" (Tailored active, blue)
  - Preview area: Gray background (#F9FAFB), monospace text
  - In compare mode: Two columns side-by-side
- Card 5: Download Section
  - Four buttons in a grid (2x2)
  - Each button: Icon on top, format label below
  - Icons: Document icon (blue), PDF icon (red), Text icon (gray), ZIP icon (purple)

**Color Coding:**
- Scores: Red (<60), Yellow (60-79), Green (80+)
- Missing skills: Red badges
- Recommended skills: Green badges
- Improvements: Blue highlights

## Image 4: Dashboard Page Mockup

**Layout:**
- Same header
- Page title: "My Resumes" (left) + "+ New Resume" button (right, blue)
- Grid of resume cards (3 columns on desktop)
- Each card:
  - White background, shadow, rounded corners
  - Title at top (bold, dark gray)
  - Creation date (small, gray)
  - Tags as small badges (gray background)
  - Application count
  - Two buttons at bottom: "View" (blue) and "Edit" (gray)
- Empty state: Centered message with CTA button

**Visual Style:**
- Cards have hover effect (slightly increased shadow)
- Clean, organized grid layout
- Consistent spacing and typography

## Image 5: Batch Processing Page Mockup

**Layout:**
- Similar to Upload Page
- Resume upload section (single file)
- Job Description section:
  - Multiple file upload area
  - List of selected files below
  - Each file: Gray background box with filename and "Remove" button
  - Counter: "Selected Files (3/20)"
- Submit button shows count: "Process 3 Job Descriptions"

## Design Principles Applied

1. **Consistency:**
   - Same header/footer on all pages
   - Consistent card styling
   - Uniform spacing and typography

2. **Visual Hierarchy:**
   - Large, bold headings
   - Clear section separation
   - Prominent call-to-action buttons

3. **Color Psychology:**
   - Blue: Trust, professionalism
   - Green: Success, positive changes
   - Red: Warnings, missing items
   - Gray: Neutral, secondary information

4. **User Feedback:**
   - Loading spinners
   - Success/error messages
   - Hover states
   - Active states

5. **Accessibility:**
   - High contrast ratios
   - Clear labels
   - Keyboard navigation support
   - Screen reader friendly

## Tools to Create Mockups

You can use these descriptions with:
- **Figma** - Create high-fidelity mockups
- **Adobe XD** - Design and prototype
- **Sketch** - UI design tool
- **Canva** - Quick mockups
- **Draw.io** - Free diagramming tool

## Key Visual Elements to Include

1. **Icons:**
   - Upload icon (document with arrow)
   - Checkmark icon (success)
   - X icon (remove/error)
   - Download icon
   - Spinner icon (loading)

2. **Shadows:**
   - Cards: Medium shadow
   - Buttons: Subtle shadow
   - Hover: Increased shadow

3. **Borders:**
   - Cards: No border (shadow only)
   - Inputs: 1px solid gray
   - Upload areas: 2px dashed gray

4. **Spacing:**
   - Consistent 24px padding in cards
   - 16px gaps between elements
   - 48px section spacing

These descriptions provide enough detail to create pixel-perfect mockup images that match the implemented React code.

