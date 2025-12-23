"""
Tests for diff_viewer module - Resume Versioning UI
"""
import pytest
from agents.diff_viewer import (
    diff_resume_structured,
    create_side_by_side_diff,
    calculate_change_statistics,
    _diff_section,
    _diff_experience,
    _diff_skills,
    _diff_education,
    _diff_certifications,
    _diff_projects,
    _diff_languages,
    _diff_awards,
    _diff_contact,
)


class TestDiffSection:
    """Test _diff_section function"""
    
    def test_unchanged_section(self):
        """Test diff of unchanged section"""
        result = _diff_section("Same text", "Same text")
        assert result["changed"] is False
        assert result["before"] == "Same text"
        assert result["after"] == "Same text"
    
    def test_changed_section(self):
        """Test diff of changed section"""
        result = _diff_section("Old text", "New text")
        assert result["changed"] is True
        assert result["before"] == "Old text"
        assert result["after"] == "New text"
        assert "diff" in result
    
    def test_empty_section(self):
        """Test diff with empty section"""
        result = _diff_section("", "New text")
        assert result["changed"] is True
        assert result["before"] == ""
        assert result["after"] == "New text"


class TestDiffSkills:
    """Test _diff_skills function"""
    
    def test_no_changes(self):
        """Test skills with no changes"""
        result = _diff_skills(["Python", "Java"], ["Python", "Java"])
        assert result["changed"] is False
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
    
    def test_added_skills(self):
        """Test added skills"""
        result = _diff_skills(["Python"], ["Python", "Java", "Go"])
        assert result["changed"] is True
        assert "Java" in result["added"]
        assert "Go" in result["added"]
        assert len(result["removed"]) == 0
    
    def test_removed_skills(self):
        """Test removed skills"""
        result = _diff_skills(["Python", "Java", "Go"], ["Python"])
        assert result["changed"] is True
        assert "Java" in result["removed"]
        assert "Go" in result["removed"]
        assert len(result["added"]) == 0
    
    def test_mixed_changes(self):
        """Test both added and removed skills"""
        result = _diff_skills(["Python", "Java"], ["Python", "Go"])
        assert result["changed"] is True
        assert "Go" in result["added"]
        assert "Java" in result["removed"]


class TestDiffExperience:
    """Test _diff_experience function"""
    
    def test_no_changes(self):
        """Test experience with no changes"""
        before = [{"title": "Engineer", "company": "Tech", "bullets": []}]
        after = [{"title": "Engineer", "company": "Tech", "bullets": []}]
        result = _diff_experience(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "unchanged"
    
    def test_added_experience(self):
        """Test added experience entry"""
        before = []
        after = [{"title": "Engineer", "company": "Tech", "bullets": []}]
        result = _diff_experience(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "added"
        assert result[0]["after"] == after[0]
    
    def test_removed_experience(self):
        """Test removed experience entry"""
        before = [{"title": "Engineer", "company": "Tech", "bullets": []}]
        after = []
        result = _diff_experience(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "removed"
        assert result[0]["before"] == before[0]
    
    def test_modified_experience(self):
        """Test modified experience entry"""
        before = [{"title": "Engineer", "company": "Tech", "bullets": ["Old bullet"]}]
        after = [{"title": "Engineer", "company": "Tech", "bullets": ["New bullet"]}]
        result = _diff_experience(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "modified"
        assert "bullets_diff" in result[0]


class TestDiffResumeStructured:
    """Test diff_resume_structured function"""
    
    def test_complete_comparison(self):
        """Test complete resume comparison"""
        before = {
            "summary": "Old summary",
            "experience": [{"title": "Engineer", "company": "Tech", "bullets": []}],
            "skills": ["Python"],
            "education": [],
            "certifications": [],
            "projects": [],
            "languages": [],
            "awards": [],
            "contact": {}
        }
        after = {
            "summary": "New summary",
            "experience": [{"title": "Engineer", "company": "Tech", "bullets": []}],
            "skills": ["Python", "Java"],
            "education": [],
            "certifications": [],
            "projects": [],
            "languages": [],
            "awards": [],
            "contact": {}
        }
        
        result = diff_resume_structured(before, after, include_side_by_side=True)
        
        # Check main structure
        assert "comparison" in result
        assert "statistics" in result
        assert "side_by_side" in result
        
        # Check comparison sections
        assert "summary" in result["comparison"]
        assert "experience" in result["comparison"]
        assert "skills" in result["comparison"]
        assert "education" in result["comparison"]
        assert "certifications" in result["comparison"]
        assert "projects" in result["comparison"]
        assert "languages" in result["comparison"]
        assert "awards" in result["comparison"]
        assert "contact" in result["comparison"]
        assert "text_diff" in result["comparison"]
        
        # Check statistics
        assert "total_changes" in result["statistics"]
        assert "sections_changed" in result["statistics"]
        assert "words_added" in result["statistics"]
        assert "words_removed" in result["statistics"]
        
        # Check side-by-side format
        assert "format" in result["side_by_side"]
        assert "sections" in result["side_by_side"]
    
    def test_without_side_by_side(self):
        """Test comparison without side-by-side format"""
        before = {"summary": "Old", "experience": [], "skills": []}
        after = {"summary": "New", "experience": [], "skills": []}
        
        result = diff_resume_structured(before, after, include_side_by_side=False)
        
        assert "comparison" in result
        assert "statistics" in result
        assert "side_by_side" not in result
    
    def test_empty_resumes(self):
        """Test comparison with empty resumes"""
        before = {}
        after = {}
        
        result = diff_resume_structured(before, after)
        
        assert "comparison" in result
        assert "statistics" in result


class TestSideBySideDiff:
    """Test create_side_by_side_diff function"""
    
    def test_side_by_side_structure(self):
        """Test side-by-side diff structure"""
        before = {
            "summary": "Old summary",
            "experience": [],
            "skills": ["Python"],
            "education": []
        }
        after = {
            "summary": "New summary",
            "experience": [],
            "skills": ["Python", "Java"],
            "education": []
        }
        
        result = create_side_by_side_diff(before, after)
        
        assert result["format"] == "structured"
        assert "sections" in result
        assert len(result["sections"]) > 0
        
        # Check each section has left and right
        for section in result["sections"]:
            assert "section_name" in section
            assert "left" in section
            assert "right" in section
            assert "content" in section["left"]
            assert "content" in section["right"]


class TestChangeStatistics:
    """Test calculate_change_statistics function"""
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        before = {
            "summary": "Old summary text",
            "experience": [],
            "skills": ["Python"]
        }
        after = {
            "summary": "New summary text with more words",
            "experience": [],
            "skills": ["Python", "Java"]
        }
        
        comparison = {
            "summary": {"changed": True},
            "experience": [],
            "skills": {"changed": True}
        }
        
        result = calculate_change_statistics(before, after, comparison)
        
        assert "total_changes" in result
        assert "sections_changed" in result
        assert "words_added" in result
        assert "words_removed" in result
        assert "net_change" in result
        assert "net_change_display" in result
        
        # Verify sections_changed includes modified sections
        assert "summary" in result["sections_changed"]
        assert "skills" in result["sections_changed"]


class TestDiffOtherSections:
    """Test diff functions for other resume sections"""
    
    def test_diff_education(self):
        """Test education diff"""
        before = [{"institution": "University", "degree": "BS"}]
        after = [{"institution": "University", "degree": "MS"}]
        
        result = _diff_education(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "modified"
    
    def test_diff_certifications(self):
        """Test certifications diff"""
        before = [{"name": "Cert1", "issuer": "Org1"}]
        after = [{"name": "Cert2", "issuer": "Org1"}]
        
        result = _diff_certifications(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "modified"
    
    def test_diff_projects(self):
        """Test projects diff"""
        before = [{"name": "Project1", "description": "Old desc"}]
        after = [{"name": "Project1", "description": "New desc"}]
        
        result = _diff_projects(before, after)
        assert len(result) == 1
        assert result[0]["action"] == "modified"
    
    def test_diff_languages(self):
        """Test languages diff"""
        before = ["English"]
        after = ["English", "Spanish"]
        
        result = _diff_languages(before, after)
        assert result["changed"] is True
        assert "Spanish" in result["added"]
    
    def test_diff_awards(self):
        """Test awards diff"""
        before = ["Award1"]
        after = ["Award1", "Award2"]
        
        result = _diff_awards(before, after)
        assert result["changed"] is True
        assert "Award2" in result["added"]
    
    def test_diff_contact(self):
        """Test contact diff"""
        before = {"email": "old@email.com", "phone": "123-456-7890"}
        after = {"email": "new@email.com", "phone": "123-456-7890"}
        
        result = _diff_contact(before, after)
        assert result["changed"] is True
        assert "fields" in result
        assert result["fields"]["email"]["changed"] is True
        assert result["fields"]["phone"]["changed"] is False

