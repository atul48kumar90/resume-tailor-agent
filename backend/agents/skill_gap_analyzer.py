# agents/skill_gap_analyzer.py
"""
Skill gap analysis - identifies missing skills and provides recommendations.
"""
from typing import Dict, List, Any
from agents.ats_scorer import _tokenize, _match_keyword


def analyze_skill_gap(
    jd_keywords: Dict[str, List[str]],
    resume_text: str,
    inferred_skills: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze skill gaps between JD requirements and resume.
    
    Args:
        jd_keywords: JD keywords organized by category
        resume_text: Resume text
        inferred_skills: Skills inferred from resume (optional)
    
    Returns:
        Skill gap analysis with missing skills, recommendations, etc.
    """
    resume_tokens = _tokenize(resume_text)
    
    # Track which skills are present
    present_skills = {
        "required_skills": [],
        "optional_skills": [],
        "tools": []
    }
    
    missing_skills = {
        "required_skills": [],
        "optional_skills": [],
        "tools": []
    }
    
    # Check each category
    for category in ["required_skills", "optional_skills", "tools"]:
        for skill in jd_keywords.get(category, []):
            if _match_keyword(skill, resume_tokens):
                present_skills[category].append(skill)
            else:
                missing_skills[category].append(skill)
    
    # Add inferred skills to present skills
    if inferred_skills:
        inferred_skill_names = [s["skill"] for s in inferred_skills if s.get("confidence", 0) >= 0.8]
        for skill_name in inferred_skill_names:
            # Check if this inferred skill matches any JD requirement
            for category in ["required_skills", "optional_skills", "tools"]:
                for jd_skill in jd_keywords.get(category, []):
                    if skill_name.lower() in jd_skill.lower() or jd_skill.lower() in skill_name.lower():
                        if skill_name not in present_skills[category]:
                            present_skills[category].append(skill_name)
                        # Remove from missing if it was there
                        if skill_name in missing_skills[category]:
                            missing_skills[category].remove(skill_name)
    
    # Calculate coverage
    total_required = len(jd_keywords.get("required_skills", []))
    total_optional = len(jd_keywords.get("optional_skills", []))
    total_tools = len(jd_keywords.get("tools", []))
    
    required_coverage = len(present_skills["required_skills"]) / max(total_required, 1) * 100
    optional_coverage = len(present_skills["optional_skills"]) / max(total_optional, 1) * 100
    tools_coverage = len(present_skills["tools"]) / max(total_tools, 1) * 100
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        missing_skills,
        present_skills,
        required_coverage
    )
    
    # Prioritize missing skills
    priority_skills = _prioritize_missing_skills(
        missing_skills["required_skills"],
        jd_keywords
    )
    
    return {
        "summary": {
            "required_coverage": round(required_coverage, 1),
            "optional_coverage": round(optional_coverage, 1),
            "tools_coverage": round(tools_coverage, 1),
            "total_required": total_required,
            "total_optional": total_optional,
            "total_tools": total_tools,
            "present_required": len(present_skills["required_skills"]),
            "present_optional": len(present_skills["optional_skills"]),
            "present_tools": len(present_skills["tools"]),
        },
        "present_skills": present_skills,
        "missing_skills": missing_skills,
        "priority_skills": priority_skills,
        "recommendations": recommendations,
        "gap_severity": _calculate_gap_severity(required_coverage, missing_skills)
    }


def _generate_recommendations(
    missing_skills: Dict[str, List[str]],
    present_skills: Dict[str, List[str]],
    required_coverage: float
) -> List[Dict[str, Any]]:
    """Generate actionable recommendations."""
    recommendations = []
    
    # Critical missing required skills
    if missing_skills["required_skills"]:
        recommendations.append({
            "type": "critical",
            "title": "Add Required Skills",
            "message": f"You're missing {len(missing_skills['required_skills'])} required skills. "
                      f"These are essential for this role.",
            "skills": missing_skills["required_skills"][:5],  # Top 5
            "action": "Consider highlighting related experience or taking courses to develop these skills."
        })
    
    # Low coverage warning
    if required_coverage < 60:
        recommendations.append({
            "type": "warning",
            "title": "Low Skill Match",
            "message": f"Only {required_coverage:.1f}% of required skills are present in your resume.",
            "action": "Consider tailoring your resume more closely to the job description or "
                     "applying to roles that better match your current skill set."
        })
    
    # Missing tools
    if missing_skills["tools"]:
        recommendations.append({
            "type": "info",
            "title": "Add Technical Tools",
            "message": f"Consider adding experience with: {', '.join(missing_skills['tools'][:3])}",
            "skills": missing_skills["tools"][:5],
            "action": "If you have experience with similar tools, mention them explicitly."
        })
    
    # Quick wins (easy to add skills)
    quick_wins = _identify_quick_wins(missing_skills, present_skills)
    if quick_wins:
        recommendations.append({
            "type": "quick_win",
            "title": "Quick Wins",
            "message": "These skills might be easy to add based on your existing experience:",
            "skills": quick_wins,
            "action": "Review your experience - you may already have these skills but haven't mentioned them."
        })
    
    return recommendations


def _prioritize_missing_skills(
    missing_required: List[str],
    jd_keywords: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """Prioritize missing skills by importance."""
    # Skills that appear in multiple categories are more important
    all_jd_skills = (
        jd_keywords.get("required_skills", []) +
        jd_keywords.get("optional_skills", []) +
        jd_keywords.get("tools", [])
    )
    
    skill_frequency = {}
    for skill in all_jd_skills:
        skill_lower = skill.lower()
        skill_frequency[skill_lower] = skill_frequency.get(skill_lower, 0) + 1
    
    prioritized = []
    for skill in missing_required:
        priority = "high"  # All required skills are high priority
        frequency = skill_frequency.get(skill.lower(), 1)
        
        prioritized.append({
            "skill": skill,
            "priority": priority,
            "frequency": frequency,
            "category": "required"
        })
    
    # Sort by frequency (skills mentioned multiple times are more important)
    prioritized.sort(key=lambda x: x["frequency"], reverse=True)
    
    return prioritized


def _identify_quick_wins(
    missing_skills: Dict[str, List[str]],
    present_skills: Dict[str, List[str]]
) -> List[str]:
    """Identify skills that might be easy to add (related to existing skills)."""
    # Skill relationships (e.g., if you know Java, Spring Boot is a quick win)
    skill_relationships = {
        "java": ["spring boot", "spring", "j2ee", "maven", "gradle"],
        "python": ["django", "flask", "fastapi", "pandas", "numpy"],
        "javascript": ["typescript", "react", "node.js", "express"],
        "sql": ["database", "postgresql", "mysql", "oracle"],
        "aws": ["cloud", "ec2", "s3", "lambda", "docker"],
        "docker": ["kubernetes", "containerization", "ci/cd"],
        "rest": ["api", "http", "json", "microservices"],
    }
    
    quick_wins = []
    all_present = (
        present_skills["required_skills"] +
        present_skills["optional_skills"] +
        present_skills["tools"]
    )
    
    for present_skill in all_present:
        present_lower = present_skill.lower()
        if present_lower in skill_relationships:
            related = skill_relationships[present_lower]
            for related_skill in related:
                # Check if this related skill is missing
                for category in ["required_skills", "optional_skills", "tools"]:
                    for missing in missing_skills[category]:
                        if related_skill.lower() in missing.lower() or missing.lower() in related_skill.lower():
                            if related_skill not in quick_wins:
                                quick_wins.append(related_skill)
    
    return quick_wins[:5]  # Top 5 quick wins


def _calculate_gap_severity(required_coverage: float, missing_skills: Dict[str, List[str]]) -> str:
    """Calculate severity of skill gap."""
    missing_required_count = len(missing_skills["required_skills"])
    
    if required_coverage >= 80 and missing_required_count == 0:
        return "low"
    elif required_coverage >= 60 and missing_required_count <= 2:
        return "medium"
    elif required_coverage >= 40:
        return "high"
    else:
        return "critical"

