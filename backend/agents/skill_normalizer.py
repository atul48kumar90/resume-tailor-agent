# agents/skill_normalizer.py
"""
Skill normalization and deduplication utilities.
Groups similar skills (e.g., "java", "java technologies", "j2ee") into canonical forms.
"""
from typing import List, Set
from difflib import SequenceMatcher


# Canonical skill mappings - maps variations to a canonical form
SKILL_CANONICAL_MAP = {
    # Java variations
    "java": "Java",
    "java technologies": "Java",
    "java/j2ee": "Java",
    "j2ee": "Java",
    "java ee": "Java",
    "java enterprise": "Java",
    "java ecosystem": "Java",
    "java expertise": "Java",
    "java proficiency": "Java",
    "java development": "Java",
    
    # REST/API variations
    "rest": "REST",
    "rest api": "REST",
    "restful": "REST",
    "restful api": "REST",
    "restful apis": "REST",
    
    # GraphQL variations
    "graphql": "GraphQL",
    "graph ql": "GraphQL",
    
    # gRPC variations
    "grpc": "gRPC",
    "g rpc": "gRPC",
    
    # NoSQL variations
    "nosql": "NoSQL",
    "nosql databases": "NoSQL databases",
    "no sql": "NoSQL",
    
    # Data structures variations
    "data structures": "Data structures",
    "data structures and algorithms": "Data structures and algorithms",
    "dsa": "Data structures and algorithms",
    "algorithms": "Algorithms",
    "data structures & algorithms": "Data structures and algorithms",
    
    # Documentation variations
    "documentation": "Documentation",
    "documentation best practices": "Documentation best practices",
    "technical documentation": "Documentation",
}


def normalize_skill_name(skill: str) -> str:
    """
    Normalize a skill name to its canonical form.
    
    Args:
        skill: Skill name to normalize
    
    Returns:
        Canonical skill name
    """
    if not skill:
        return skill
    
    skill_lower = skill.lower().strip()
    
    # Check canonical map first
    if skill_lower in SKILL_CANONICAL_MAP:
        return SKILL_CANONICAL_MAP[skill_lower]
    
    # Check if skill contains any canonical key
    for key, canonical in SKILL_CANONICAL_MAP.items():
        if key in skill_lower or skill_lower in key:
            # If one is a substring of the other, use the canonical form
            if len(key) <= len(skill_lower) and key in skill_lower:
                return canonical
            elif len(skill_lower) <= len(key) and skill_lower in key:
                return canonical
    
    # Return original with proper capitalization
    return skill.strip()


def are_skills_similar(skill1: str, skill2: str, threshold: float = 0.85) -> bool:
    """
    Check if two skills are similar (duplicates or variations).
    
    Args:
        skill1: First skill name
        skill2: Second skill name
        threshold: Similarity threshold (0-1)
    
    Returns:
        True if skills are similar
    """
    if not skill1 or not skill2:
        return False
    
    s1 = skill1.lower().strip()
    s2 = skill2.lower().strip()
    
    # Exact match
    if s1 == s2:
        return True
    
    # Check if one contains the other (for cases like "java" and "java technologies")
    # Also handle cases like "java" in "java expertise" or "java/j2ee"
    if s1 in s2 or s2 in s1:
        # For core skill names (like "java", "rest"), allow matching even if length ratio is low
        # This handles "java" matching "java expertise" or "java/j2ee"
        core_skills = ["java", "rest", "python", "javascript", "sql", "aws", "docker", "kubernetes"]
        is_core_skill = any(core in s1 or core in s2 for core in core_skills)
        
        if is_core_skill:
            # For core skills, be more lenient - just check if one contains the other
            return True
        
        # But not if they're too different in length (avoid false positives for non-core skills)
        length_ratio = min(len(s1), len(s2)) / max(len(s1), len(s2))
        if length_ratio >= 0.5:  # At least 50% length match
            return True
    
    # Check canonical map
    s1_canonical = normalize_skill_name(skill1).lower()
    s2_canonical = normalize_skill_name(skill2).lower()
    if s1_canonical == s2_canonical:
        return True
    
    # Fuzzy string matching
    similarity = SequenceMatcher(None, s1, s2).ratio()
    if similarity >= threshold:
        return True
    
    return False


def deduplicate_skills(skills: List[str], preferred_skills: List[str] = None) -> List[str]:
    """
    Remove duplicate and similar skills from a list.
    Prefers skills from preferred_skills (e.g., JD keywords) when found.
    
    Args:
        skills: List of skill names
        preferred_skills: List of preferred skill names (e.g., from JD) - these take precedence
    
    Returns:
        Deduplicated list of skills (preferring JD terminology)
    """
    if not skills:
        return []
    
    # Build a set of preferred skills for quick lookup
    preferred_set = set()
    preferred_map = {}  # Maps normalized preferred skills to original
    if preferred_skills:
        for pref_skill in preferred_skills:
            if pref_skill:
                pref_lower = pref_skill.lower().strip()
                preferred_set.add(pref_lower)
                # Map variations to the preferred form
                preferred_map[pref_lower] = pref_skill.strip()
                # Also map normalized version
                pref_normalized = normalize_skill_name(pref_skill).lower()
                if pref_normalized != pref_lower:
                    preferred_map[pref_normalized] = pref_skill.strip()
    
    seen = set()
    result = []
    skill_groups = {}  # Maps normalized form to list of similar skills
    
    # First pass: group similar skills
    for skill in skills:
        if not skill:
            continue
        
        skill_normalized = normalize_skill_name(skill)
        skill_lower = skill_normalized.lower()
        
        # Check if we've seen a similar skill
        found_group = None
        for seen_normalized in seen:
            if are_skills_similar(skill_normalized, seen_normalized):
                found_group = seen_normalized
                break
        
        if found_group:
            # Add to existing group
            if found_group not in skill_groups:
                skill_groups[found_group] = [found_group]
            skill_groups[found_group].append(skill.strip())
        else:
            # Create new group
            seen.add(skill_normalized)
            skill_groups[skill_normalized] = [skill.strip()]
    
    # Second pass: for each group, prefer JD terminology
    for normalized, group in skill_groups.items():
        # Check if any skill in the group matches a preferred skill
        preferred_match = None
        for skill_in_group in group:
            skill_lower = skill_in_group.lower().strip()
            if skill_lower in preferred_set:
                preferred_match = skill_in_group
                break
            # Also check normalized version
            skill_normalized = normalize_skill_name(skill_in_group).lower()
            if skill_normalized in preferred_map:
                preferred_match = preferred_map[skill_normalized]
                break
        
        if preferred_match:
            # Use the preferred form from JD
            result.append(preferred_match)
        else:
            # Use the first occurrence (or normalized form)
            result.append(group[0])
    
    return result


def merge_skill_lists(*skill_lists: List[str], **kwargs) -> List[str]:
    """
    Merge multiple skill lists and deduplicate.
    Prefers skills from preferred_skills (e.g., JD keywords) when found.
    
    Args:
        *skill_lists: Variable number of skill lists
        **kwargs: Optional keyword arguments:
            preferred_skills: List of preferred skill names (e.g., from JD) - these take precedence
    
    Returns:
        Merged and deduplicated skill list (preferring JD terminology)
    """
    preferred_skills = kwargs.get("preferred_skills", None)
    all_skills = []
    for skill_list in skill_lists:
        if skill_list:
            all_skills.extend(skill_list)
    
    return deduplicate_skills(all_skills, preferred_skills=preferred_skills)

