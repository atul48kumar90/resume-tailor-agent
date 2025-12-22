import difflib
from typing import Dict, List, Any


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
    after_resume: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create structured diff for resume comparison.
    Returns changes organized by section with before/after values.
    """
    from agents.resume_formatter import format_resume_text
    
    before_text = format_resume_text(before_resume)
    after_text = format_resume_text(after_resume)
    
    changes = {
        "summary": _diff_section(
            before_resume.get("summary", ""),
            after_resume.get("summary", "")
        ),
        "experience": _diff_experience(
            before_resume.get("experience", []),
            after_resume.get("experience", [])
        ),
        "skills": _diff_skills(
            before_resume.get("skills", []),
            after_resume.get("skills", [])
        ),
        "text_diff": _create_text_diff(before_text, after_text),
        "statistics": {
            "before_word_count": len(before_text.split()),
            "after_word_count": len(after_text.split()),
            "before_length": len(before_text),
            "after_length": len(after_text),
        }
    }
    
    return changes


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
