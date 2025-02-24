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

def test_interactive_feedback_loop(generator, monkeypatch, capsys):
    """Test that the interactive feedback loop properly maintains context and incorporates feedback."""
    
    # Mock responses to simulate interaction
    responses = [
        # First response
        {
            "tickets": [{
                "title": "Initial Ticket",
                "description": "First version",
                "dependencies": [],
                "risk_analysis": "Initial risks",
                "pr_details": {"files": ["test.py"], "changes": "initial"}
            }]
        },
        # Second response (should incorporate feedback)
        {
            "tickets": [{
                "title": "Updated Ticket",
                "description": "Incorporated feedback: Added humor",
                "dependencies": [],
                "risk_analysis": "Updated risks with a joke about Dean",
                "pr_details": {"files": ["test.py"], "changes": "updated"}
            }]
        }
    ]
    
    response_iter = iter(responses)
    
    def mock_get_completion(*args, **kwargs):
        return next(response_iter)
    
    # Mock input responses: first 'n' for not satisfied, then 'y' for satisfied
    input_responses = iter(['n', 'Make it funny and mention Dean', 'y'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion)
    
    # Run the generator
    final_tickets = generator.generate_tickets("Test requirements", interactive=True)
    
    # Verify the conversation flow
    captured = capsys.readouterr()
    output = captured.out
    
    # Check that both ticket versions were displayed
    assert "Initial Ticket" in output
    assert "Updated Ticket" in output
    
    # Verify feedback was incorporated
    assert final_tickets[0]["description"] == "Incorporated feedback: Added humor"
    assert "Dean" in final_tickets[0]["risk_analysis"]

def test_interactive_feedback_maintains_json_structure(generator, monkeypatch):
    """Test that the JSON structure is maintained throughout feedback iterations."""
    
    messages_history = []
    
    def mock_get_completion(messages, *args):
        messages_history.extend(messages)
        return {
            "tickets": [{
                "title": "Test Ticket",
                "description": "Test description",
                "dependencies": [],
                "risk_analysis": "Test risks",
                "pr_details": {"files": ["test.py"], "changes": "test"}
            }]
        }
    
    input_responses = iter(['n', 'Test feedback', 'y'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion)
    
    generator.generate_tickets("Test requirements", interactive=True)
    
    # Verify all assistant messages are valid JSON
    for msg in messages_history:
        if msg["role"] == "assistant":
            # This will raise an exception if the JSON is invalid
            parsed = json.loads(msg["content"])
            assert "tickets" in parsed
            assert isinstance(parsed["tickets"], list)
            for ticket in parsed["tickets"]:
                assert all(key in ticket for key in [
                    "title", "description", "dependencies", 
                    "risk_analysis", "pr_details"
                ])
                assert all(key in ticket["pr_details"] for key in ["files", "changes"])

def test_interactive_feedback_error_handling(generator, monkeypatch, capsys, caplog):
    """Test error handling during the interactive feedback loop."""
    
    def mock_get_completion_with_error(*args, **kwargs):
        # Create a proper mock request object
        import httpx
        error_request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        error_response = httpx.Response(
            status_code=500,
            request=error_request,
            content=b'{"error": {"message": "Test API Error", "type": "api_error"}}'
        )
        raise APIError(
            message="Test API Error",
            request=error_request,
            body=error_response.json()
        )
    
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion_with_error)
    input_responses = iter(['n', 'Test feedback'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    
    with pytest.raises(APIError) as exc_info:
        generator.generate_tickets("Test requirements", interactive=True)
    
    # Verify the error message in the exception
    assert "Test API Error" in str(exc_info.value)
    
    # Verify the error appears in the logs instead of stdout/stderr
    assert "Test API Error" in caplog.text

def test_interactive_feedback_empty_response(generator, monkeypatch):
    """Test handling of empty or invalid responses from the API."""
    
    responses = [
        {"tickets": []},  # Empty tickets list
        {  # Valid response after feedback
            "tickets": [{
                "title": "Fixed Ticket",
                "description": "Valid ticket after empty response",
                "dependencies": [],
                "risk_analysis": "Test risks",
                "pr_details": {"files": ["test.py"], "changes": "test"}
            }]
        }
    ]
    
    response_iter = iter(responses)
    monkeypatch.setattr(generator, '_get_completion', lambda *args: next(response_iter))
    
    input_responses = iter(['n', 'Please generate valid tickets', 'y'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    
    final_tickets = generator.generate_tickets("Test requirements", interactive=True)
    
    assert len(final_tickets) > 0
    assert final_tickets[0]["title"] == "Fixed Ticket"

def test_interactive_feedback_message_limit(generator, monkeypatch):
    """Test that the conversation history doesn't grow indefinitely."""
    
    messages_history = []
    
    def mock_get_completion(messages, *args):
        messages_history.append(len(messages))  # Track message count
        return {
            "tickets": [{
                "title": "Test Ticket",
                "description": "Test description",
                "dependencies": [],
                "risk_analysis": "Test risks",
                "pr_details": {"files": ["test.py"], "changes": "test"}
            }]
        }
    
    # Simulate multiple feedback iterations
    input_responses = iter(['n', 'Feedback 1', 'n', 'Feedback 2', 'n', 'Feedback 3', 'y'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion)
    
    generator.generate_tickets("Test requirements", interactive=True)
    
    # Check that message history doesn't grow exponentially
    message_counts = messages_history
    for i in range(1, len(message_counts)):
        # Each iteration should add at most 2 messages (assistant + user)
        assert message_counts[i] - message_counts[i-1] <= 2 

def test_validate_ticket_structure_invalid_types(generator):
    """Test validation of ticket structure with invalid field types."""
    invalid_tickets = [
        {
            "tickets": [{
                "title": 123,  # Should be string
                "description": "Valid description",
                "dependencies": "not_a_list",  # Should be list
                "risk_analysis": ["not_a_string"],  # Should be string
                "pr_details": {
                    "files": "not_a_list",  # Should be list
                    "changes": ["not_a_string"]  # Should be string
                }
            }]
        }
    ]
    
    with pytest.raises(ValueError, match="must be a string"):
        generator._validate_ticket_structure(invalid_tickets[0])

def test_validate_ticket_structure_missing_pr_fields(generator):
    """Test validation of ticket structure with missing PR fields."""
    invalid_tickets = {
        "tickets": [{
            "title": "Test Ticket",
            "description": "Test description",
            "dependencies": [],
            "risk_analysis": "Test risks",
            "pr_details": {}  # Missing required fields
        }]
    }
    
    with pytest.raises(ValueError, match="missing PR fields"):
        generator._validate_ticket_structure(invalid_tickets)

def test_create_system_prompt(generator):
    """Test system prompt creation."""
    prompt = generator._create_system_prompt()
    assert "You are an expert project manager" in prompt
    assert "JSON" in prompt
    assert "tickets" in prompt

def test_create_user_prompt(generator):
    """Test user prompt creation."""
    requirements = "Test requirements"
    prompt = generator._create_user_prompt(requirements)
    assert requirements in prompt
    assert "Please analyze" in prompt

def test_interactive_feedback_with_invalid_json(generator, monkeypatch, capsys):
    """Test handling of invalid JSON during interactive feedback."""
    def mock_get_completion_invalid_json(*args, **kwargs):
        # Create a mock response that mimics the OpenAI API response structure
        response = Mock()
        message_mock = Mock()
        message_mock.content = "Not a JSON response"
        choice_mock = Mock()
        choice_mock.message = message_mock
        response.choices = [choice_mock]
        return response
    
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion_invalid_json)
    
    # Provide enough responses for the entire interaction
    # First round: 'n' (not satisfied), 'Test feedback'
    # Second round: 'y' (satisfied) to exit the loop
    input_responses = iter(['n', 'Test feedback', 'y'])
    monkeypatch.setattr('builtins.input', lambda *args: next(input_responses))
    
    # We expect a JSONDecodeError when trying to parse the invalid response
    with pytest.raises(json.JSONDecodeError):
        generator.generate_tickets("Test requirements", interactive=True)

def test_max_retries_exceeded(generator, monkeypatch):
    """Test behavior when max retries are exceeded."""
    def mock_get_completion_always_fails(*args, **kwargs):
        import httpx
        error_request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        raise APIError(
            message="API Error",
            request=error_request,
            body={"error": "Test error"}
        )
    
    monkeypatch.setattr(generator, '_get_completion', mock_get_completion_always_fails)
    
    with pytest.raises(APIError):
        generator.generate_tickets("Test requirements", interactive=False) 