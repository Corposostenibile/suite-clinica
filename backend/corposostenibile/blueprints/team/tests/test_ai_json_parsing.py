"""Test for AI matching JSON parsing robustness."""

import json
import pytest


def test_parse_json_response_valid():
    """Test parsing valid JSON."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    valid_json = json.dumps({
        "summary": "Test summary",
        "criteria": ["TEST"],
        "suggested_focus": ["Focus 1"]
    })
    
    result = AIMatchingService._parse_json_response(valid_json)
    assert result is not None
    assert result["summary"] == "Test summary"
    assert result["criteria"] == ["TEST"]


def test_parse_json_response_with_extra_braces():
    """Test parsing JSON with extra closing braces (Gemini bug)."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    # This is the exact format Gemini was returning
    malformed_json = '''{
  "summary": "Test summary",
  "criteria": ["TEST"],
  "suggested_focus": ["Focus 1"]
}
}'''
    
    result = AIMatchingService._parse_json_response(malformed_json)
    assert result is not None
    assert result["summary"] == "Test summary"
    assert result["criteria"] == ["TEST"]


def test_parse_json_response_with_markdown():
    """Test parsing JSON wrapped in markdown code block."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    markdown_json = '''```json
{
  "summary": "Test summary",
  "criteria": ["TEST"],
  "suggested_focus": ["Focus 1"]
}
```'''
    
    result = AIMatchingService._parse_json_response(markdown_json)
    assert result is not None
    assert result["summary"] == "Test summary"


def test_parse_json_response_with_extra_text():
    """Test parsing JSON with extra text around it."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    text_with_json = '''Ecco il risultato dell'analisi:
{
  "summary": "Test summary",
  "criteria": ["TEST"],
  "suggested_focus": ["Focus 1"]
}
Spero che ti sia utile!'''
    
    result = AIMatchingService._parse_json_response(text_with_json)
    assert result is not None
    assert result["summary"] == "Test summary"


def test_parse_json_response_empty():
    """Test parsing empty/None input."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    assert AIMatchingService._parse_json_response("") is None
    assert AIMatchingService._parse_json_response(None) is None


def test_parse_json_response_invalid():
    """Test parsing completely invalid input."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    
    assert AIMatchingService._parse_json_response("not json at all") is None
    assert AIMatchingService._parse_json_response("{invalid}") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
