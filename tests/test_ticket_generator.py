import pytest
from unittest.mock import Mock, patch
import json
from ticket_generator.generator import TicketGenerator
from openai import APIError, RateLimitError

def fake_get_completion_success(messages, max_retries=3):
    # Return a valid ticket structure with all required fields correctly populated
    return {
        "tickets": [
            {
                "title": "Implement User Authentication",
                "description": "This is a detailed description that covers all the necessary implementation details. " * 5,
                "dependencies": ["Setup Database", "Create API Endpoints"],
                "risk_analysis": "Medium risk: Requires careful security review and testing.",
                "pr_details": {
                    "files": ["auth.py", "models.py"],
                    "changes": "Add authentication middleware and user model."
                }
            }
        ]
    }

def fake_get_completion_invalid(messages, max_retries=3):
    # Return an invalid ticket missing required fields
    return {
        "tickets": [
            {
                "title": "Invalid Ticket"
                # Missing description, dependencies, risk_analysis, and pr_details
            }
        ]
    }

def fake_get_completion_rate_limit(messages, max_retries=3):
    from openai.types import APIResponse
    response = APIResponse(
        response=Mock(status_code=429),
        body={"error": {"message": "Rate limit exceeded"}}
    )
    raise RateLimitError(response=response, body=response.body)

def fake_get_completion_api_error(messages, max_retries=3):
    from openai import APIError
    from openai._base_client import HttpxRequest
    request = HttpxRequest(
        method="post",
        url="https://api.openai.com/v1/chat/completions",
        params={},
        headers={},
        json={}
    )
    raise APIError("API error occurred", request=request)

@pytest.fixture
def generator():
    return TicketGenerator(api_key="dummy", model="gpt-4o", api_base="https://api.openai.com/v1/")

def test_generate_tickets_valid(generator, monkeypatch):
    # Create a proper mock function that handles self correctly
    def mock_get_completion(*args, **kwargs):
        return fake_get_completion_success(None)
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    tickets = generator.generate_tickets("This is a feature requirement.", interactive=False)
    assert isinstance(tickets, list)
    assert len(tickets) == 1
    
    ticket = tickets[0]
    assert all(key in ticket for key in ['title', 'description', 'dependencies', 'risk_analysis', 'pr_details'])
    assert all(key in ticket['pr_details'] for key in ['files', 'changes'])
    assert len(ticket['description']) >= 200  # Minimum description length

def test_generate_tickets_invalid(generator, monkeypatch):
    def mock_get_completion(*args, **kwargs):
        result = fake_get_completion_invalid(None)
        # Force validation to fail immediately instead of retrying
        generator.non_interactive_max_attempts = 1
        return result
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    with pytest.raises(ValueError, match=r"Generated tickets did not meet quality requirements"):
        generator.generate_tickets("This is a feature requirement.", interactive=False)

def test_generate_tickets_rate_limit(generator, monkeypatch):
    def mock_get_completion(*args, **kwargs):
        return fake_get_completion_rate_limit(None)
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    with pytest.raises(RateLimitError):
        generator.generate_tickets("This is a feature requirement.", interactive=False)

def test_generate_tickets_api_error(generator, monkeypatch):
    def mock_get_completion(*args, **kwargs):
        return fake_get_completion_api_error(None)
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    with pytest.raises(APIError):
        generator.generate_tickets("This is a feature requirement.", interactive=False)

def test_validate_ticket_valid(generator):
    valid_ticket = {
        "title": "Valid Ticket",
        "description": "This is a very detailed description that meets the minimum length requirement. " * 5,
        "dependencies": ["Dep1"],
        "risk_analysis": "Low risk identified",
        "pr_details": {
            "files": ["file1.py"],
            "changes": "Update function implementation"
        }
    }
    issues = generator._validate_ticket(valid_ticket)
    assert not issues  # Should be empty list for valid ticket

def test_validate_ticket_invalid_description(generator):
    invalid_ticket = {
        "title": "Invalid Ticket",
        "description": "Too short",  # Below minimum length
        "dependencies": [],
        "risk_analysis": "Low risk",
        "pr_details": {
            "files": ["file1.py"],
            "changes": "Update"
        }
    }
    issues = generator._validate_ticket(invalid_ticket)
    assert any("Description too short" in issue for issue in issues)

def test_validate_ticket_missing_fields(generator):
    invalid_ticket = {
        "title": "Missing Fields",
        # Missing required fields
    }
    issues = generator._validate_ticket(invalid_ticket)
    assert len(issues) > 0
    assert any("Missing required fields" in issue for issue in issues)

def test_validate_ticket_invalid_pr_details(generator):
    invalid_ticket = {
        "title": "Invalid PR Details",
        "description": "This is a very detailed description that meets the minimum length requirement. " * 5,
        "dependencies": [],
        "risk_analysis": "Low risk",
        "pr_details": {}  # Missing required sub-fields
    }
    issues = generator._validate_ticket(invalid_ticket)
    assert any("PR details missing required sub-fields" in issue for issue in issues) 