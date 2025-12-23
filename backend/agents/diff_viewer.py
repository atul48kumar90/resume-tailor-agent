import difflib
from typing import Dict, List, Any, Optional, Tuple


def diff_text(old: str, new: str) -> str:
    """Simple text diff for basic comparison."""
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def diff_resume_structured(
    before_resume: Dict[str, Any],
    after_resume: Dict[str, Any],
    include_side_by_side: bool = True
) -> Dict[str, Any]:
    """
    Create structured diff for resume comparison.
    Returns changes organized by section with before/after values.
    
    Args:
        before_resume: Original resume data
        after_resume: Updated resume data
        include_side_by_side: Whether to include side-by-side format
    
    Returns:
        Dictionary with structured diff, side-by-side comparison, and statistics
    """
    from agents.resume_formatter import format_resume_text
    
    before_text = format_resume_text(before_resume)
    after_text = format_resume_text(after_resume)
    
    # Structured diff by section
    comparison = {
        "summary": _diff_section(
            before_resume.get("summary", "") or "",
            after_resume.get("summary", "") or ""
        ),
        "experience": _diff_experience(
            before_resume.get("experience", []) or [],
            after_resume.get("experience", []) or []
        ),
        "skills": _diff_skills(
            before_resume.get("skills", []) or [],
            after_resume.get("skills", []) or []
        ),
        "education": _diff_education(
            before_resume.get("education", []) or [],
            after_resume.get("education", []) or []
        ),
        "certifications": _diff_certifications(
            before_resume.get("certifications", []) or [],
            after_resume.get("certifications", []) or []
        ),
        "projects": _diff_projects(
            before_resume.get("projects", []) or [],
            after_resume.get("projects", []) or []
        ),
        "languages": _diff_languages(
            before_resume.get("languages", []) or [],
            after_resume.get("languages", []) or []
        ),
        "awards": _diff_awards(
            before_resume.get("awards", []) or [],
            after_resume.get("awards", []) or []
        ),
        "contact": _diff_contact(
            before_resume.get("contact", {}) or {},
            after_resume.get("contact", {}) or {}
        ),
        "text_diff": _create_text_diff(before_text, after_text),
    }
    
    # Calculate statistics
    statistics = calculate_change_statistics(before_resume, after_resume, comparison)
    
    result = {
        "comparison": comparison,
        "statistics": statistics,
    }
    
    # Add side-by-side format if requested
    if include_side_by_side:
        result["side_by_side"] = create_side_by_side_diff(before_resume, after_resume)
    
    return result


def _diff_section(before: str, after: str) -> Dict[str, Any]:
    """Diff a single text section."""
    if before == after:
        return {"changed": False, "before": before, "after": after}
    
    return {
        "changed": True,
        "before": before,
        "after": after,
        "diff": list(difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            lineterm="",
            n=3
        ))
    }


def _diff_experience(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Diff experience sections."""
    changes = []
    max_len = max(len(before), len(after))
    
    for i in range(max_len):
        before_exp = before[i] if i < len(before) else None
        after_exp = after[i] if i < len(after) else None
        
        if before_exp is None:
            changes.append({
                "index": i,
                "action": "added",
                "before": None,
                "after": after_exp
            })
        elif after_exp is None:
            changes.append({
                "index": i,
                "action": "removed",
                "before": before_exp,
                "after": None
            })
        else:
            # Compare title
            title_changed = before_exp.get("title") != after_exp.get("title")
            
            # Compare bullets
            before_bullets = before_exp.get("bullets", [])
            after_bullets = after_exp.get("bullets", [])
            bullets_diff = _diff_bullets(before_bullets, after_bullets)
            
            if title_changed or bullets_diff["changed"]:
                changes.append({
                    "index": i,
                    "action": "modified",
                    "before": before_exp,
                    "after": after_exp,
                    "title_changed": title_changed,
                    "bullets_diff": bullets_diff
                })
            else:
                changes.append({
                    "index": i,
                    "action": "unchanged",
                    "before": before_exp,
                    "after": after_exp
                })
    
    return changes


def _diff_bullets(before: List[str], after: List[str]) -> Dict[str, Any]:
    """Diff bullet points."""
    added = [b for b in after if b not in before]
    removed = [b for b in before if b not in after]
    modified = []
    
    # Find modified bullets (similar but changed)
    for b_bullet in before:
        if b_bullet not in removed:
            for a_bullet in after:
                if a_bullet not in added and b_bullet != a_bullet:
                    # Check if they're similar (same start, different content)
                    if b_bullet.split()[0:3] == a_bullet.split()[0:3]:
                        modified.append({
                            "before": b_bullet,
                            "after": a_bullet
                        })
                        break
    
    return {
        "changed": len(added) > 0 or len(removed) > 0 or len(modified) > 0,
        "added": added,
        "removed": removed,
        "modified": modified,
        "before_count": len(before),
        "after_count": len(after)
    }


def _diff_skills(before: List[str], after: List[str]) -> Dict[str, Any]:
    """Diff skills list."""
    before_set = set(before)
    after_set = set(after)
    
    added = list(after_set - before_set)
    removed = list(before_set - after_set)
    
    return {
        "changed": len(added) > 0 or len(removed) > 0,
        "added": added,
        "removed": removed,
        "before": before,
        "after": after,
        "before_count": len(before),
        "after_count": len(after)
    }


def _diff_education(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Diff education sections."""
    changes = []
    max_len = max(len(before), len(after))
    
    for i in range(max_len):
        before_edu = before[i] if i < len(before) else None
        after_edu = after[i] if i < len(after) else None
        
        if before_edu is None:
            changes.append({
                "index": i,
                "action": "added",
                "before": None,
                "after": after_edu
            })
        elif after_edu is None:
            changes.append({
                "index": i,
                "action": "removed",
                "before": before_edu,
                "after": None
            })
        else:
            # Compare key fields
            institution_changed = before_edu.get("institution") != after_edu.get("institution")
            degree_changed = before_edu.get("degree") != after_edu.get("degree")
            
            if institution_changed or degree_changed:
                changes.append({
                    "index": i,
                    "action": "modified",
                    "before": before_edu,
                    "after": after_edu,
                })
            else:
                changes.append({
                    "index": i,
                    "action": "unchanged",
                    "before": before_edu,
                    "after": after_edu
                })
    
    return changes


def _diff_certifications(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Diff certifications sections."""
    changes = []
    max_len = max(len(before), len(after))
    
    for i in range(max_len):
        before_cert = before[i] if i < len(before) else None
        after_cert = after[i] if i < len(after) else None
        
        if before_cert is None:
            changes.append({
                "index": i,
                "action": "added",
                "before": None,
                "after": after_cert
            })
        elif after_cert is None:
            changes.append({
                "index": i,
                "action": "removed",
                "before": before_cert,
                "after": None
            })
        else:
            # Compare key fields
            name_changed = before_cert.get("name") != after_cert.get("name")
            
            if name_changed:
                changes.append({
                    "index": i,
                    "action": "modified",
                    "before": before_cert,
                    "after": after_cert,
                })
            else:
                changes.append({
                    "index": i,
                    "action": "unchanged",
                    "before": before_cert,
                    "after": after_cert
                })
    
    return changes


def _diff_projects(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Diff projects sections."""
    changes = []
    max_len = max(len(before), len(after))
    
    for i in range(max_len):
        before_proj = before[i] if i < len(before) else None
        after_proj = after[i] if i < len(after) else None
        
        if before_proj is None:
            changes.append({
                "index": i,
                "action": "added",
                "before": None,
                "after": after_proj
            })
        elif after_proj is None:
            changes.append({
                "index": i,
                "action": "removed",
                "before": before_proj,
                "after": None
            })
        else:
            # Compare key fields
            name_changed = before_proj.get("name") != after_proj.get("name")
            desc_changed = before_proj.get("description") != after_proj.get("description")
            
            if name_changed or desc_changed:
                changes.append({
                    "index": i,
                    "action": "modified",
                    "before": before_proj,
                    "after": after_proj,
                })
            else:
                changes.append({
                    "index": i,
                    "action": "unchanged",
                    "before": before_proj,
                    "after": after_proj
                })
    
    return changes


def _diff_languages(before: List[str], after: List[str]) -> Dict[str, Any]:
    """Diff languages list."""
    before_set = set(before)
    after_set = set(after)
    
    added = list(after_set - before_set)
    removed = list(before_set - after_set)
    
    return {
        "changed": len(added) > 0 or len(removed) > 0,
        "added": added,
        "removed": removed,
        "before": before,
        "after": after,
        "before_count": len(before),
        "after_count": len(after)
    }


def _diff_awards(before: List[str], after: List[str]) -> Dict[str, Any]:
    """Diff awards list."""
    before_set = set(before)
    after_set = set(after)
    
    added = list(after_set - before_set)
    removed = list(before_set - after_set)
    
    return {
        "changed": len(added) > 0 or len(removed) > 0,
        "added": added,
        "removed": removed,
        "before": before,
        "after": after,
        "before_count": len(before),
        "after_count": len(after)
    }


def _diff_contact(
    before: Dict[str, Any],
    after: Dict[str, Any]
) -> Dict[str, Any]:
    """Diff contact information."""
    changes = {}
    all_keys = set(before.keys()) | set(after.keys())
    
    for key in all_keys:
        before_val = before.get(key)
        after_val = after.get(key)
        
        if before_val != after_val:
            changes[key] = {
                "changed": True,
                "before": before_val,
                "after": after_val
            }
        else:
            changes[key] = {
                "changed": False,
                "before": before_val,
                "after": after_val
            }
    
    has_changes = any(c.get("changed") for c in changes.values())
    
    return {
        "changed": has_changes,
        "fields": changes
    }


def _create_text_diff(before: str, after: str) -> Dict[str, Any]:
    """Create HTML-friendly diff with line-by-line changes."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    
    differ = difflib.SequenceMatcher(None, before_lines, after_lines)
    diff_lines = []
    
    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            for line in before_lines[i1:i2]:
                diff_lines.append({
                    "type": "unchanged",
                    "content": line
                })
        elif tag == "delete":
            for line in before_lines[i1:i2]:
                diff_lines.append({
                    "type": "removed",
                    "content": line
                })
        elif tag == "insert":
            for line in after_lines[j1:j2]:
                diff_lines.append({
                    "type": "added",
                    "content": line
                })
        elif tag == "replace":
            for line in before_lines[i1:i2]:
                diff_lines.append({
                    "type": "removed",
                    "content": line
                })
            for line in after_lines[j1:j2]:
                diff_lines.append({
                    "type": "added",
                    "content": line
                })
    
    return {
        "lines": diff_lines,
        "added_count": sum(1 for l in diff_lines if l["type"] == "added"),
        "removed_count": sum(1 for l in diff_lines if l["type"] == "removed"),
        "unchanged_count": sum(1 for l in diff_lines if l["type"] == "unchanged")
    }


def create_side_by_side_diff(
    before_resume: Dict[str, Any],
    after_resume: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create side-by-side comparison format for frontend rendering.
    
    Returns structured data that can be easily rendered in a side-by-side view.
    """
    side_by_side = {
        "format": "structured",  # For frontend rendering
        "sections": []
    }
    
    # Summary section
    before_summary = before_resume.get("summary", "")
    after_summary = after_resume.get("summary", "")
    if before_summary or after_summary:
        side_by_side["sections"].append({
            "section_name": "summary",
            "left": _create_side_by_side_text(before_summary, after_summary, "left"),
            "right": _create_side_by_side_text(before_summary, after_summary, "right"),
        })
    
    # Experience section
    before_exp = before_resume.get("experience", [])
    after_exp = after_resume.get("experience", [])
    if before_exp or after_exp:
        side_by_side["sections"].append({
            "section_name": "experience",
            "left": _create_side_by_side_experience(before_exp, after_exp, "left"),
            "right": _create_side_by_side_experience(before_exp, after_exp, "right"),
        })
    
    # Skills section
    before_skills = before_resume.get("skills", [])
    after_skills = after_resume.get("skills", [])
    if before_skills or after_skills:
        side_by_side["sections"].append({
            "section_name": "skills",
            "left": _create_side_by_side_skills(before_skills, after_skills, "left"),
            "right": _create_side_by_side_skills(before_skills, after_skills, "right"),
        })
    
    # Education section
    before_edu = before_resume.get("education", [])
    after_edu = after_resume.get("education", [])
    if before_edu or after_edu:
        side_by_side["sections"].append({
            "section_name": "education",
            "left": _create_side_by_side_education(before_edu, after_edu, "left"),
            "right": _create_side_by_side_education(before_edu, after_edu, "right"),
        })
    
    # Certifications section
    before_certs = before_resume.get("certifications", [])
    after_certs = after_resume.get("certifications", [])
    if before_certs or after_certs:
        side_by_side["sections"].append({
            "section_name": "certifications",
            "left": _create_side_by_side_certifications(before_certs, after_certs, "left"),
            "right": _create_side_by_side_certifications(before_certs, after_certs, "right"),
        })
    
    # Projects section
    before_projects = before_resume.get("projects", [])
    after_projects = after_resume.get("projects", [])
    if before_projects or after_projects:
        side_by_side["sections"].append({
            "section_name": "projects",
            "left": _create_side_by_side_projects(before_projects, after_projects, "left"),
            "right": _create_side_by_side_projects(before_projects, after_projects, "right"),
        })
    
    # Languages section
    before_langs = before_resume.get("languages", [])
    after_langs = after_resume.get("languages", [])
    if before_langs or after_langs:
        side_by_side["sections"].append({
            "section_name": "languages",
            "left": _create_side_by_side_skills(before_langs, after_langs, "left"),  # Reuse skills format
            "right": _create_side_by_side_skills(before_langs, after_langs, "right"),
        })
    
    # Awards section
    before_awards = before_resume.get("awards", [])
    after_awards = after_resume.get("awards", [])
    if before_awards or after_awards:
        side_by_side["sections"].append({
            "section_name": "awards",
            "left": _create_side_by_side_skills(before_awards, after_awards, "left"),  # Reuse skills format
            "right": _create_side_by_side_skills(before_awards, after_awards, "right"),
        })
    
    return side_by_side


def _create_side_by_side_text(before: str, after: str, side: str) -> Dict[str, Any]:
    """Create side-by-side text comparison with word-level highlighting."""
    if side == "left":
        content = before
        # Find what was removed
        highlighted_changes = _find_word_changes(before, after, "removed")
    else:
        content = after
        # Find what was added
        highlighted_changes = _find_word_changes(before, after, "added")
    
    return {
        "content": content,
        "highlighted_changes": highlighted_changes,
        "word_count": len(content.split()) if content else 0,
    }


def _find_word_changes(before: str, after: str, change_type: str) -> List[Dict[str, Any]]:
    """Find word-level changes for highlighting."""
    if not before and not after:
        return []
    
    # If one is empty, mark entire other as changed
    if not before:
        if change_type == "added":
            return [{"start": 0, "end": len(after), "type": "added", "text": after}]
        return []
    if not after:
        if change_type == "removed":
            return [{"start": 0, "end": len(before), "type": "removed", "text": before}]
        return []
    
    before_words = before.split()
    after_words = after.split()
    
    # Use SequenceMatcher to find word-level differences
    matcher = difflib.SequenceMatcher(None, before_words, after_words)
    changes = []
    current_pos = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if change_type == "removed" and tag in ["delete", "replace"]:
            # Words removed from before
            for word in before_words[i1:i2]:
                word_start = before.find(word, current_pos)
                if word_start != -1:
                    changes.append({
                        "start": word_start,
                        "end": word_start + len(word),
                        "type": "removed",
                        "text": word
                    })
                    current_pos = word_start + len(word)
        
        elif change_type == "added" and tag in ["insert", "replace"]:
            # Words added to after
            for word in after_words[j1:j2]:
                word_start = after.find(word, current_pos)
                if word_start != -1:
                    changes.append({
                        "start": word_start,
                        "end": word_start + len(word),
                        "type": "added",
                        "text": word
                    })
                    current_pos = word_start + len(word)
        
        elif tag == "equal":
            # Skip unchanged words but update position
            text = before if change_type == "removed" else after
            words = before_words[i1:i2] if change_type == "removed" else after_words[j1:j2]
            for word in words:
                word_start = text.find(word, current_pos)
                if word_start != -1:
                    current_pos = word_start + len(word)
    
    return changes


def _create_side_by_side_experience(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
    side: str
) -> Dict[str, Any]:
    """Create side-by-side experience comparison."""
    max_len = max(len(before), len(after))
    entries = []
    
    for i in range(max_len):
        before_exp = before[i] if i < len(before) else None
        after_exp = after[i] if i < len(after) else None
        
        if side == "left":
            entry = before_exp
            if before_exp is None:
                entry = {"title": "", "company": "", "bullets": []}
        else:
            entry = after_exp
            if after_exp is None:
                entry = {"title": "", "company": "", "bullets": []}
        
        # Determine change status
        if before_exp is None:
            change_status = "added"
        elif after_exp is None:
            change_status = "removed"
        elif before_exp != after_exp:
            change_status = "modified"
        else:
            change_status = "unchanged"
        
        entries.append({
            "index": i,
            "title": entry.get("title", ""),
            "company": entry.get("company", ""),
            "bullets": entry.get("bullets", []),
            "change_status": change_status if side == "right" else ("removed" if change_status == "removed" else "unchanged"),
        })
    
    return {
        "entries": entries,
        "count": len(entries),
    }


def _create_side_by_side_skills(
    before: List[str],
    after: List[str],
    side: str
) -> Dict[str, Any]:
    """Create side-by-side skills comparison."""
    before_set = set(before)
    after_set = set(after)
    
    if side == "left":
        skills = before
        added = []
        removed = list(before_set - after_set)
        unchanged = list(before_set & after_set)
    else:
        skills = after
        added = list(after_set - before_set)
        removed = []
        unchanged = list(before_set & after_set)
    
    return {
        "skills": skills,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "count": len(skills),
    }


def _create_side_by_side_education(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
    side: str
) -> Dict[str, Any]:
    """Create side-by-side education comparison."""
    max_len = max(len(before), len(after))
    entries = []
    
    for i in range(max_len):
        before_edu = before[i] if i < len(before) else None
        after_edu = after[i] if i < len(after) else None
        
        if side == "left":
            entry = before_edu
            if before_edu is None:
                entry = {"institution": "", "degree": "", "field_of_study": ""}
        else:
            entry = after_edu
            if after_edu is None:
                entry = {"institution": "", "degree": "", "field_of_study": ""}
        
        # Determine change status
        if before_edu is None:
            change_status = "added"
        elif after_edu is None:
            change_status = "removed"
        elif before_edu != after_edu:
            change_status = "modified"
        else:
            change_status = "unchanged"
        
        entries.append({
            "index": i,
            "institution": entry.get("institution", ""),
            "degree": entry.get("degree", ""),
            "field_of_study": entry.get("field_of_study", ""),
            "change_status": change_status if side == "right" else ("removed" if change_status == "removed" else "unchanged"),
        })
    
    return {
        "entries": entries,
        "count": len(entries),
    }


def _create_side_by_side_certifications(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
    side: str
) -> Dict[str, Any]:
    """Create side-by-side certifications comparison."""
    max_len = max(len(before), len(after))
    entries = []
    
    for i in range(max_len):
        before_cert = before[i] if i < len(before) else None
        after_cert = after[i] if i < len(after) else None
        
        if side == "left":
            entry = before_cert
            if before_cert is None:
                entry = {"name": "", "issuer": "", "date": ""}
        else:
            entry = after_cert
            if after_cert is None:
                entry = {"name": "", "issuer": "", "date": ""}
        
        # Determine change status
        if before_cert is None:
            change_status = "added"
        elif after_cert is None:
            change_status = "removed"
        elif before_cert != after_cert:
            change_status = "modified"
        else:
            change_status = "unchanged"
        
        entries.append({
            "index": i,
            "name": entry.get("name", ""),
            "issuer": entry.get("issuer", ""),
            "date": entry.get("date", ""),
            "change_status": change_status if side == "right" else ("removed" if change_status == "removed" else "unchanged"),
        })
    
    return {
        "entries": entries,
        "count": len(entries),
    }


def _create_side_by_side_projects(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
    side: str
) -> Dict[str, Any]:
    """Create side-by-side projects comparison."""
    max_len = max(len(before), len(after))
    entries = []
    
    for i in range(max_len):
        before_proj = before[i] if i < len(before) else None
        after_proj = after[i] if i < len(after) else None
        
        if side == "left":
            entry = before_proj
            if before_proj is None:
                entry = {"name": "", "description": "", "technologies": []}
        else:
            entry = after_proj
            if after_proj is None:
                entry = {"name": "", "description": "", "technologies": []}
        
        # Determine change status
        if before_proj is None:
            change_status = "added"
        elif after_proj is None:
            change_status = "removed"
        elif before_proj != after_proj:
            change_status = "modified"
        else:
            change_status = "unchanged"
        
        entries.append({
            "index": i,
            "name": entry.get("name", ""),
            "description": entry.get("description", ""),
            "technologies": entry.get("technologies", []),
            "change_status": change_status if side == "right" else ("removed" if change_status == "removed" else "unchanged"),
        })
    
    return {
        "entries": entries,
        "count": len(entries),
    }


def calculate_change_statistics(
    before_resume: Dict[str, Any],
    after_resume: Dict[str, Any],
    comparison: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate comprehensive change statistics."""
    from agents.resume_formatter import format_resume_text
    
    before_text = format_resume_text(before_resume)
    after_text = format_resume_text(after_resume)
    
    before_words = before_text.split()
    after_words = after_text.split()
    
    # Count changes by section
    sections_changed = []
    if comparison.get("summary", {}).get("changed"):
        sections_changed.append("summary")
    if any(exp.get("action") != "unchanged" for exp in comparison.get("experience", [])):
        sections_changed.append("experience")
    if comparison.get("skills", {}).get("changed"):
        sections_changed.append("skills")
    if any(edu.get("action") != "unchanged" for edu in comparison.get("education", [])):
        sections_changed.append("education")
    if any(cert.get("action") != "unchanged" for cert in comparison.get("certifications", [])):
        sections_changed.append("certifications")
    if any(proj.get("action") != "unchanged" for proj in comparison.get("projects", [])):
        sections_changed.append("projects")
    if comparison.get("languages", {}).get("changed"):
        sections_changed.append("languages")
    if comparison.get("awards", {}).get("changed"):
        sections_changed.append("awards")
    if comparison.get("contact", {}).get("changed"):
        sections_changed.append("contact")
    
    # Count word changes using diff algorithm
    # Use SequenceMatcher to accurately count added/removed words
    matcher = difflib.SequenceMatcher(None, before_words, after_words)
    words_added = 0
    words_removed = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "delete":
            words_removed += (i2 - i1)
        elif tag == "insert":
            words_added += (j2 - j1)
        elif tag == "replace":
            words_removed += (i2 - i1)
            words_added += (j2 - j1)
    
    net_change = len(after_words) - len(before_words)
    
    return {
        "total_changes": len(sections_changed),
        "sections_changed": sections_changed,
        "words_added": words_added,
        "words_removed": words_removed,
        "net_change": net_change,
        "net_change_display": f"{'+' if net_change >= 0 else ''}{net_change} words",
        "before_word_count": len(before_words),
        "after_word_count": len(after_words),
        "before_length": len(before_text),
        "after_length": len(after_text),
    }
