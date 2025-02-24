import pytest
from app import parse_input_content

def test_valid_plain_text():
    # Valid plain text with "feature" keyword and sufficient length
    input_text = "This is a valid feature requirement with more than ten letters."
    output = parse_input_content(input_text, file_type=None)
    assert "feature" in output.lower()

def test_too_short_input():
    # Input shorter than 10 characters should raise a ValueError
    with pytest.raises(ValueError, match=r"Input is too short"):
        parse_input_content("bug", file_type=None)

def test_missing_keyword_input():
    # Even if the input is long enough, missing 'feature' or 'bug' should raise an error
    valid_text = "This input is long enough but does not have any required keyword."
    with pytest.raises(ValueError, match=r"Input does not contain expected keywords"):
        parse_input_content(valid_text, file_type=None)

def test_html_input():
    # HTML input: extract text from HTML body; ensure keyword exists after conversion.
    html_content = "<html><body>This is an HTML test featuring the Feature keyword.</body></html>"
    output = parse_input_content(html_content, file_type='.html')
    assert "feature" in output.lower()

def test_markdown_input():
    # Markdown input: using mistune to parse Markdown; check that "bug" is present
    markdown_content = "# Header\nThis is a markdown file with a bug reported. Additional details to pass length."
    output = parse_input_content(markdown_content, file_type='.md')
    assert "bug" in output.lower() 