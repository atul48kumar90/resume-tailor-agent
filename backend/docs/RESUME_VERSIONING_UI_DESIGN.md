# Resume Versioning UI - Design Document

## Overview

The Resume Versioning UI feature provides visual diff viewing and side-by-side comparison capabilities for resume versions. This enables users to see exactly what changed between versions in an intuitive, visual format.

## Current State

### Existing Infrastructure

1. **Database Models** (`db/models.py`):
   - `ResumeVersion` model with version tracking
   - Parent-child relationships for version history
   - Change summaries stored with each version

2. **Versioning System** (`agents/resume_versions.py`):
   - Redis-based version storage
   - Version list management
   - Current version pointer tracking

3. **Diff Viewer** (`agents/diff_viewer.py`):
   - Basic structured diff functionality
   - Section-by-section comparison
   - Text diff generation

4. **Existing Endpoints**:
   - `/ats/compare` - Already includes visual comparison
   - Basic version retrieval

## Proposed Implementation

### 1. Enhanced Visual Diff API Response

**Endpoint**: `GET /resumes/{resume_id}/versions/{version_id}/compare?compare_with={other_version_id}`

**Response Structure**:
```json
{
  "version1": {
    "version_id": "v12345678",
    "version_number": 1,
    "created_at": "2024-01-15T10:00:00Z",
    "change_summary": "Initial resume"
  },
  "version2": {
    "version_id": "v87654321",
    "version_number": 2,
    "created_at": "2024-01-16T14:30:00Z",
    "change_summary": "Added Python skills, updated experience"
  },
  "comparison": {
    "summary": {
      "changed": true,
      "before": "Experienced software engineer...",
      "after": "Senior software engineer with 5+ years...",
      "diff_lines": [
        {
          "line_number": 1,
          "type": "unchanged",
          "content": "Experienced software engineer"
        },
        {
          "line_number": 2,
          "type": "added",
          "content": "Senior software engineer with 5+ years"
        }
      ]
    },
    "experience": [
      {
        "index": 0,
        "action": "modified",
        "title": {
          "before": "Software Engineer",
          "after": "Senior Software Engineer",
          "changed": true
        },
        "company": {
          "before": "Tech Corp",
          "after": "Tech Corp",
          "changed": false
        },
        "bullets": {
          "added": ["Led team of 5 engineers"],
          "removed": ["Worked on backend systems"],
          "modified": [
            {
              "before": "Developed REST APIs",
              "after": "Designed and developed scalable REST APIs"
            }
          ],
          "unchanged": ["Improved system performance by 30%"]
        }
      }
    ],
    "skills": {
      "added": ["Python", "FastAPI"],
      "removed": ["PHP"],
      "unchanged": ["JavaScript", "React", "Node.js"]
    },
    "statistics": {
      "total_changes": 5,
      "sections_changed": ["summary", "experience", "skills"],
      "words_added": 45,
      "words_removed": 12,
      "net_change": "+33 words"
    }
  },
  "side_by_side": {
    "format": "html",  // or "json" for structured data
    "sections": [
      {
        "section_name": "summary",
        "left": {
          "version_id": "v12345678",
          "content": "...",
          "highlighted_changes": []
        },
        "right": {
          "version_id": "v87654321",
          "content": "...",
          "highlighted_changes": [
            {
              "start": 10,
              "end": 25,
              "type": "added",
              "text": "Senior software engineer"
            }
          ]
        }
      }
    ]
  }
}
```

### 2. Side-by-Side Comparison Format

**Two Approaches**:

#### A. Structured JSON (Recommended for API)
- Returns structured data that frontend can render
- Each section has `left` and `right` with change markers
- Frontend has full control over rendering

#### B. HTML Format (Alternative)
- Pre-rendered HTML with inline styles
- Easier to display but less flexible
- Good for quick previews

### 3. How It Works

#### Step 1: Version Retrieval
```
User requests: GET /resumes/{resume_id}/versions/{v1}/compare?compare_with={v2}

1. Fetch version1 from database/Redis
2. Fetch version2 from database/Redis
3. Extract resume_data from both versions
```

#### Step 2: Structured Diff Generation
```
1. Compare summary sections (text diff)
2. Compare experience entries (structured diff)
   - Match by index or company/title
   - Diff bullets line-by-line
   - Track additions, removals, modifications
3. Compare skills (set operations)
4. Compare education, certifications, projects
5. Generate statistics
```

#### Step 3: Side-by-Side Format Generation
```
For each section:
1. Align content (match similar lines)
2. Mark changes:
   - Added: highlight in green
   - Removed: highlight in red (strikethrough)
   - Modified: highlight both
   - Unchanged: normal text
3. Generate line-by-line comparison
4. Add change markers (line numbers, change types)
```

#### Step 4: Response Assembly
```
1. Combine version metadata
2. Add structured diff
3. Add side-by-side format
4. Add statistics
5. Return JSON response
```

### 4. API Endpoints

#### List Versions
```
GET /resumes/{resume_id}/versions
Response: List of all versions with metadata
```

#### Get Version Details
```
GET /resumes/{resume_id}/versions/{version_id}
Response: Full version data
```

#### Compare Versions
```
GET /resumes/{resume_id}/versions/{version_id}/compare?compare_with={other_version_id}
Response: Visual diff with side-by-side comparison
```

#### Compare with Current
```
GET /resumes/{resume_id}/versions/{version_id}/compare
Response: Compare with current version (default)
```

### 5. Frontend Rendering

The API response is designed to be easily rendered by frontend:

**Side-by-Side View**:
```javascript
// Frontend receives structured data
{
  side_by_side: {
    sections: [
      {
        section_name: "summary",
        left: { content: "...", changes: [...] },
        right: { content: "...", changes: [...] }
      }
    ]
  }
}

// Frontend renders:
<div class="side-by-side">
  <div class="left-panel">
    {renderSection(left, "removed")}
  </div>
  <div class="right-panel">
    {renderSection(right, "added")}
  </div>
</div>
```

**Unified Diff View**:
```javascript
// Frontend receives diff_lines
{
  diff_lines: [
    { type: "unchanged", content: "..." },
    { type: "removed", content: "..." },
    { type: "added", content: "..." }
  ]
}

// Frontend renders:
<div class="unified-diff">
  {diff_lines.map(line => (
    <div className={`line-${line.type}`}>
      {line.content}
    </div>
  ))}
</div>
```

### 6. Change Highlighting

**Word-Level Diff**:
- For text sections, use word-level diff
- Highlight individual words that changed
- Show context (unchanged words around changes)

**Line-Level Diff**:
- For structured sections (experience, skills)
- Show entire lines as added/removed/modified
- More suitable for structured data

### 7. Statistics and Summary

**Change Statistics**:
- Total number of changes
- Sections affected
- Words/lines added/removed
- Net change (growth/shrinkage)

**Change Summary**:
- High-level description of changes
- Most significant changes highlighted
- Quick overview for users

### 8. Integration Points

**With Existing Systems**:
1. **Resume Parser**: Use parsed structured data for better diffs
2. **Version Storage**: Integrate with database versioning
3. **ATS Comparison**: Reuse diff logic from `/ats/compare`
4. **Template System**: Show template changes if applicable

### 9. Performance Considerations

**Optimization Strategies**:
1. **Caching**: Cache diff results for common comparisons
2. **Lazy Loading**: Only generate side-by-side when requested
3. **Pagination**: For large resumes, paginate sections
4. **Async Generation**: Generate diffs in background for large comparisons

### 10. Example Use Cases

**Use Case 1: Review Changes After Tailoring**
```
User tailors resume → New version created
User clicks "View Changes" → Side-by-side comparison shown
User can see exactly what was modified
```

**Use Case 2: Compare Two Versions**
```
User has multiple versions
User selects two versions to compare
API returns structured diff
Frontend renders side-by-side view
```

**Use Case 3: Version History**
```
User views version history
Each version shows change summary
User clicks version → See full diff
User can restore any version
```

## Technical Implementation Details

### Diff Algorithm

**For Text Sections**:
- Use `difflib.SequenceMatcher` (already in use)
- Generate unified diff format
- Track line-by-line changes

**For Structured Sections**:
- Compare by structure (experience entries, skills)
- Use fuzzy matching for similar entries
- Track additions, removals, modifications

**For Skills**:
- Set operations (added, removed, unchanged)
- Simple and efficient

### Response Format Design

**Structured Format** (Recommended):
- JSON with clear structure
- Easy to parse and render
- Supports multiple view types

**HTML Format** (Optional):
- Pre-rendered HTML
- Inline CSS for styling
- Ready to display

### Error Handling

- Handle missing versions gracefully
- Return clear error messages
- Fallback to basic text diff if structured diff fails

## Benefits

1. **Better UX**: Users can visually see changes
2. **Transparency**: Clear understanding of what changed
3. **Decision Making**: Easy to decide if changes are good
4. **Version Control**: Better version management
5. **Collaboration**: Share diffs with others

## Next Steps

1. Implement enhanced diff viewer module
2. Create API endpoints for version comparison
3. Add side-by-side format generation
4. Integrate with existing versioning system
5. Add caching for performance
6. Create frontend-friendly response format

