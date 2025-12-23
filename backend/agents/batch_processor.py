# agents/batch_processor.py
"""
Batch processing for multiple job descriptions.
Processes one resume against multiple JDs simultaneously.

Optimized with parallel processing using asyncio for 5-10x faster batch operations.
"""
from typing import List, Dict, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


async def process_batch_jds_async(
    resume_text: str,
    jd_list: List[Dict[str, str]],
    resume_id: str = None,
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """
    Process resume against multiple job descriptions in parallel (async).
    
    Uses asyncio.gather() to process multiple JDs concurrently, providing
    5-10x speedup for batch operations.
    
    Args:
        resume_text: Resume text
        jd_list: List of job descriptions with metadata
                 [{"jd_text": "...", "jd_id": "jd1", "title": "Software Engineer"}, ...]
        resume_id: Optional resume ID for tracking
        max_concurrent: Maximum number of concurrent JD analyses (default: 10)
    
    Returns:
        Batch processing results with scores and recommendations for each JD
    """
    from agents.jd_analyzer import analyze_jd_async
    from agents.ats_scorer import score_detailed
    from agents.role_detector import detect_role
    from agents.jd_normalizer import normalize_jd_keywords
    from agents.skill_gap_analyzer import analyze_skill_gap
    from agents.skill_inference import infer_skills_from_resume
    from agents.role_confidence import tune_confidence_by_role
    
    summary = {
        "total_jds": len(jd_list),
        "processed": 0,
        "failed": 0,
        "best_match": None,
        "worst_match": None,
        "average_score": 0
    }
    
    scores = []
    
    # Process each JD in parallel
    async def process_single_jd(jd_data: Dict[str, str], index: int) -> Optional[Dict[str, Any]]:
        """Process a single JD asynchronously."""
        jd_id = jd_data.get("jd_id", f"jd_{index}")
        jd_text = jd_data.get("jd_text", "")
        jd_title = jd_data.get("title", "Unknown Position")
        
        if not jd_text.strip():
            logger.warning(f"Skipping empty JD: {jd_id}")
            return None
        
        try:
            # Analyze JD (async - this is the main bottleneck)
            jd_analysis = await analyze_jd_async(jd_text)
            
            # Normalize keywords (sync - fast)
            raw_keywords = {
                "required_skills": jd_analysis.get("required_skills", []),
                "optional_skills": jd_analysis.get("optional_skills", []),
                "tools": jd_analysis.get("tools", []),
            }
            jd_keywords = normalize_jd_keywords(raw_keywords)
            
            # Detect role (sync - fast)
            role_info = detect_role(jd_text, resume_text)
            
            # Infer skills (sync - fast)
            inferred_skills = infer_skills_from_resume(
                resume_text=resume_text,
                explicit_skills=(
                    jd_keywords["required_skills"] +
                    jd_keywords["optional_skills"] +
                    jd_keywords["tools"]
                ),
            )
            
            # Tune confidence by role (sync - fast)
            inferred_skills = tune_confidence_by_role(
                inferred_skills,
                role=role_info["role"],
            )
            
            # Score resume (sync - fast) - using advanced scorer
            from agents.ats_scorer_advanced import score_detailed_advanced
            ats_score = score_detailed_advanced(
                jd_keywords,
                resume_text,
                jd_data=jd_analysis,
                inferred_skills=inferred_skills,
                enable_semantic=False,  # Disable for batch performance
            )
            
            # Skill gap analysis (sync - fast)
            skill_gap = analyze_skill_gap(
                jd_keywords,
                resume_text,
                inferred_skills
            )
            
            # Calculate fit score (sync - fast)
            fit_score = _calculate_fit_score(ats_score, skill_gap)
            
            result = {
                "jd_id": jd_id,
                "title": jd_title,
                "role": jd_analysis.get("role", ""),
                "seniority": jd_analysis.get("seniority", ""),
                "ats_score": ats_score["score"],
                "fit_score": fit_score,
                "skill_gap": {
                    "severity": skill_gap["gap_severity"],
                    "required_coverage": skill_gap["summary"]["required_coverage"],
                    "missing_required_count": len(skill_gap["missing_skills"]["required_skills"]),
                },
                "keywords": {
                    "required_matched": len(ats_score["matched_keywords"]["required_skills"]),
                    "required_total": len(jd_keywords["required_skills"]),
                    "tools_matched": len(ats_score["matched_keywords"]["tools"]),
                    "tools_total": len(jd_keywords["tools"]),
                },
                "recommendations": skill_gap["recommendations"][:3],  # Top 3
                "role_match": role_info["confidence"],
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process JD {jd_id}: {e}", exc_info=True)
            return {
                "jd_id": jd_id,
                "title": jd_title,
                "error": str(e),
                "status": "failed"
            }
    
    # Process all JDs in parallel with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(jd_data: Dict[str, str], index: int) -> Optional[Dict[str, Any]]:
        """Process JD with concurrency limit."""
        async with semaphore:
            return await process_single_jd(jd_data, index)
    
    # Create tasks for all JDs
    tasks = [
        process_with_limit(jd_data, idx)
        for idx, jd_data in enumerate(jd_list)
    ]
    
    # Execute all tasks in parallel
    logger.info(f"Processing {len(jd_list)} JDs in parallel (max {max_concurrent} concurrent)")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and handle exceptions
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Unexpected error in batch processing: {result}", exc_info=True)
            summary["failed"] += 1
            continue
        elif result is None:
            summary["failed"] += 1
            continue
        else:
            processed_results.append(result)
            if "ats_score" in result:
                scores.append(result["ats_score"])
                summary["processed"] += 1
            else:
                summary["failed"] += 1
    
    results = processed_results
    
    # Calculate summary statistics
    if scores:
        summary["average_score"] = sum(scores) / len(scores)
        
        # Find best and worst matches
        if results:
            valid_results = [r for r in results if "ats_score" in r]
            if valid_results:
                best = max(valid_results, key=lambda x: x.get("ats_score", 0))
                worst = min(valid_results, key=lambda x: x.get("ats_score", 100))
                
                summary["best_match"] = {
                    "jd_id": best["jd_id"],
                    "title": best["title"],
                    "score": best["ats_score"],
                    "fit_score": best.get("fit_score", 0)
                }
                
                summary["worst_match"] = {
                    "jd_id": worst["jd_id"],
                    "title": worst["title"],
                    "score": worst["ats_score"],
                    "fit_score": worst.get("fit_score", 0)
                }
    
    # Sort results by fit score (best matches first)
    results.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    
    return {
        "summary": summary,
        "results": results,
        "resume_id": resume_id
    }


def process_batch_jds(
    resume_text: str,
    jd_list: List[Dict[str, str]],
    resume_id: str = None
) -> Dict[str, Any]:
    """
    Process resume against multiple job descriptions (synchronous wrapper).
    
    This is a synchronous wrapper around the async version for backward compatibility.
    For better performance, use process_batch_jds_async() directly.
    
    Args:
        resume_text: Resume text
        jd_list: List of job descriptions with metadata
                 [{"jd_text": "...", "jd_id": "jd1", "title": "Software Engineer"}, ...]
        resume_id: Optional resume ID for tracking
    
    Returns:
        Batch processing results with scores and recommendations for each JD
    """
    # Run async version in event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        process_batch_jds_async(resume_text, jd_list, resume_id)
    )


def _calculate_fit_score(ats_result: Dict[str, Any], skill_gap: Dict[str, Any]) -> float:
    """
    Calculate overall fit score combining ATS score and skill coverage.
    Returns score from 0-100.
    """
    ats_score = ats_result.get("score", 0)
    required_coverage = skill_gap["summary"]["required_coverage"]
    
    # Weighted combination: 70% ATS score, 30% skill coverage
    fit_score = (ats_score * 0.7) + (required_coverage * 0.3)
    
    # Penalize for missing critical skills
    missing_required = len(skill_gap["missing_skills"]["required_skills"])
    if missing_required > 0:
        penalty = min(missing_required * 5, 20)  # Max 20 point penalty
        fit_score = max(0, fit_score - penalty)
    
    return round(fit_score, 1)
