@pytest.fixture
def generator():
    return TicketGenerator(api_key="test_key", model="gpt-4o", api_base="https://api.openai.com/v1/") 

def fake_get_completion_rate_limit(messages, max_retries=3):
    error_response = {
        "status_code": 429,
        "message": "Rate limit exceeded",
        "request_id": "fake_request_id"
    }
    raise RateLimitError(message="Rate limit exceeded", body=error_response) 

def test_validate_ticket_invalid_pr_details(generator):
    invalid_ticket = {
        "title": "Invalid PR Details",
        "description": "This is a very detailed description that meets the minimum length requirement. " * 5,
        "dependencies": [],
        "risk_analysis": "Low risk",
        "pr_details": {}  # Missing required sub-fields
    }
    issues = generator._validate_ticket(invalid_ticket)
    assert len(issues) > 0
    assert any("PR details missing required sub-fields" in issue for issue in issues) 