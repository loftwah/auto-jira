import pytest
import sys
from pathlib import Path
import json
from app import parse_input_content, parse_arguments, format_ticket_markdown, main
from unittest.mock import patch

def test_valid_plain_text():
    # Valid plain text with "feature" keyword and sufficient length
    input_text = "This is a valid feature requirement with more than ten letters."
    output = parse_input_content(input_text, file_type=None)
    assert "feature" in output.lower()
    assert len(output) >= 10

def test_valid_bug_text():
    # Valid plain text with "bug" keyword and sufficient length
    input_text = "This is a critical bug that needs to be fixed immediately."
    output = parse_input_content(input_text, file_type=None)
    assert "bug" in output.lower()
    assert len(output) >= 10

def test_too_short_input():
    # Input shorter than 10 characters should raise a ValueError
    with pytest.raises(ValueError, match=r"Input is too short"):
        parse_input_content("bug", file_type=None)

def test_missing_keyword_input():
    # Even if the input is long enough, missing 'feature' or 'bug' should raise an error
    valid_text = "This input is long enough but does not have any required keyword."
    with pytest.raises(ValueError, match=r"Input must contain either 'feature' or 'bug' keyword"):
        parse_input_content(valid_text, file_type=None)

def test_html_input():
    # HTML input: extract text from HTML body; ensure keyword exists after conversion
    html_content = "<html><body>This is an HTML test featuring the Feature keyword.</body></html>"
    output = parse_input_content(html_content, file_type='.html')
    assert "feature" in output.lower()

def test_markdown_input():
    # Markdown input: using mistune to parse Markdown; check that "bug" is present
    markdown_content = "# Header\nThis is a markdown file with a bug reported. Additional details to pass length."
    output = parse_input_content(markdown_content, file_type='.md')
    assert "bug" in output.lower()

def test_format_ticket_markdown():
    # Test markdown formatting of a ticket
    ticket = {
        "title": "Test Ticket",
        "description": "This is a test description",
        "dependencies": ["Dep1", "Dep2"],
        "risk_analysis": "Low risk",
        "pr_details": {
            "files": ["file1.py", "file2.py"],
            "changes": "Update function calls"
        }
    }
    output = format_ticket_markdown(ticket)
    assert "# Test Ticket" in output
    assert "## Description" in output
    assert "- Dep1\n- Dep2" in output
    assert "## Risk Analysis" in output
    assert "- file1.py\n- file2.py" in output

def test_format_ticket_markdown_no_dependencies():
    # Test markdown formatting when dependencies list is empty
    ticket = {
        "title": "Test Ticket",
        "description": "This is a test description",
        "dependencies": [],
        "risk_analysis": "Low risk",
        "pr_details": {
            "files": ["file1.py"],
            "changes": "Update function"
        }
    }
    output = format_ticket_markdown(ticket)
    assert "None" in output  # Should show "None" for empty dependencies

def test_parse_arguments_defaults(monkeypatch):
    # Mock sys.argv
    test_args = ['app.py', '--file', 'test.md']
    monkeypatch.setattr(sys, 'argv', test_args)
    
    args = parse_arguments()
    assert args.file == 'test.md'
    assert args.model == 'gpt-4o'  # Check default value
    assert args.api_url == 'https://api.openai.com/v1/'
    assert not args.non_interactive
    assert not args.test
    assert args.output_format == 'markdown'

def test_parse_arguments_all_options(monkeypatch):
    # Mock sys.argv with all options
    test_args = [
        'app.py',
        '--file', 'test.md',
        '--model', 'custom-model',
        '--api-url', 'http://custom-url',
        '--api-key', 'test-key',
        '--non-interactive',
        '--test',
        '--output-format', 'json'
    ]
    monkeypatch.setattr(sys, 'argv', test_args)
    
    args = parse_arguments()
    assert args.file == 'test.md'
    assert args.model == 'custom-model'
    assert args.api_url == 'http://custom-url'
    assert args.api_key == 'test-key'
    assert args.non_interactive
    assert args.test
    assert args.output_format == 'json'

def test_invalid_file_type():
    """Test handling of unsupported file types."""
    with pytest.raises(ValueError, match=r"Unsupported file type"):
        parse_input_content("test content", file_type='.xyz')

def test_empty_input():
    """Test handling of empty input."""
    with pytest.raises(ValueError, match=r"Input is too short"):
        parse_input_content("")

def test_invalid_html():
    """Test handling of malformed HTML."""
    invalid_html = "<html><body>Incomplete tag"
    with pytest.raises(ValueError):
        parse_input_content(invalid_html, file_type='.html')

def test_invalid_markdown():
    """Test handling of malformed Markdown."""
    invalid_md = "```python\nunclosed code block with a bug in it"
    output = parse_input_content(invalid_md, file_type='.md')
    assert len(output) > 0

def test_parse_arguments_invalid_output_format():
    """Test handling of invalid output format."""
    with pytest.raises(SystemExit):
        with patch('sys.argv', ['app.py', '--output-format', 'invalid']):
            parse_arguments()

def test_format_ticket_markdown_missing_fields():
    """Test markdown formatting with missing optional fields."""
    ticket = {
        "title": "Test Ticket",
        "description": "Test description",
        "dependencies": [],
        "risk_analysis": "Test risks",
        "pr_details": {
            "files": [],  # Empty files list
            "changes": ""  # Empty changes
        }
    }
    output = format_ticket_markdown(ticket)
    assert "# Test Ticket" in output
    assert "None" in output  # Should show "None" for empty lists

def test_main_no_api_key(monkeypatch):
    """Test main function without API key."""
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setattr('sys.argv', ['app.py', '--file', 'test.md'])
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1

def test_main_file_not_found(monkeypatch):
    """Test main function with non-existent file."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test_key')
    monkeypatch.setattr('sys.argv', ['app.py', '--file', 'nonexistent.md'])
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1 