from agents.ats_scorer import score, _match_keyword, _tokenize


def test_ats_score_full_match():
    keywords = ["Java", "Spring Boot"]
    resume = "Java developer using Spring Boot"

    result = score(keywords, resume)

    assert result["score"] == 100
    assert len(result["matched_keywords"]) == 2
    assert len(result["missing_keywords"]) == 0


def test_ats_score_partial_match():
    keywords = ["Java", "Kafka"]
    resume = "Java developer"

    result = score(keywords, resume)

    assert result["score"] == 50
    assert "Java" in result["matched_keywords"]
    assert "Kafka" in result["missing_keywords"]


def test_fuzzy_matching_typos():
    """Test that fuzzy matching catches typos and variations"""
    tokens = _tokenize("React.js developer with Postgresql database")
    
    # Test typo: Postgresql vs PostgreSQL
    match = _match_keyword("PostgreSQL", tokens)
    assert match == "fuzzy" or match == "alias"  # Should match via fuzzy or alias
    
    # Test variation: React.js vs React
    match = _match_keyword("React", tokens)
    assert match in ["exact", "alias", "fuzzy"]  # Should match


def test_fuzzy_matching_abbreviations():
    """Test that fuzzy matching handles abbreviations"""
    tokens = _tokenize("ML engineer with AWS and REST API experience")
    
    # Test abbreviation: ML vs Machine Learning
    match = _match_keyword("Machine Learning", tokens)
    assert match == "fuzzy" or match == "alias"  # Should match via fuzzy or alias
    
    # Test abbreviation: AWS vs Amazon Web Services
    match = _match_keyword("Amazon Web Services", tokens)
    assert match == "fuzzy" or match == "alias"  # Should match via fuzzy or alias


def test_normalization_variations():
    """Test that normalization handles common variations"""
    tokens = _tokenize("ReactJS and NodeJS developer")
    
    # Should match React.js
    match = _match_keyword("React.js", tokens)
    assert match in ["exact", "alias", "fuzzy"]
    
    # Should match Node.js
    match = _match_keyword("Node.js", tokens)
    assert match in ["exact", "alias", "fuzzy"]
