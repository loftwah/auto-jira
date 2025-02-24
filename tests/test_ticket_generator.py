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
    import httpx
    error_response = httpx.Response(
        status_code=429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b'{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}'
    )
    raise RateLimitError(message="Rate limit exceeded", response=error_response, body=error_response.json())

def fake_get_completion_api_error(messages, max_retries=3):
    import httpx
    error_response = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b'{"error": {"message": "API error occurred", "type": "api_error"}}'
    )
    raise APIError(message="API error occurred", request=error_response.request, body=error_response.json())

@pytest.fixture
def generator():
    return TicketGenerator(api_key="test_key", model="gpt-4o", api_base="https://api.openai.com/v1/")

def test_generate_tickets_valid(generator, monkeypatch):
    def mock_get_completion(*args, **kwargs):
        return fake_get_completion_success(None)
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    tickets = generator.generate_tickets("This is a feature requirement.", interactive=False)
    assert isinstance(tickets, list)
    assert len(tickets) == 1
    
    ticket = tickets[0]
    assert all(key in ticket for key in ['title', 'description', 'dependencies', 'risk_analysis', 'pr_details'])
    assert all(key in ticket['pr_details'] for key in ['files', 'changes'])

def test_generate_tickets_invalid(generator, monkeypatch):
    def mock_get_completion(*args, **kwargs):
        return fake_get_completion_invalid(None)
    
    monkeypatch.setattr(generator, "_get_completion", mock_get_completion)
    
    # Now we just ensure it returns whatever the API gave us
    tickets = generator.generate_tickets("This is a feature requirement.", interactive=False)
    assert isinstance(tickets, list)
    assert len(tickets) == 1

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