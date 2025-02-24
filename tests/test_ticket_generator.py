import pytest
from ticket_generator.generator import TicketGenerator

def fake_get_completion_success(self, messages, max_retries=3):
    # Return a valid ticket structure with all required fields correctly populated.
    return {
        "tickets": [
            {
                "title": "Ticket Title",
                "description": "This is a detailed description that is meant to have enough content. " * 5,
                "dependencies": ["dependency1"],
                "risk_analysis": "Low risk identified; proceed with caution.",
                "pr_details": {
                    "files": ["file1.py"],
                    "changes": "Modify file1 to update function behavior."
                }
            }
        ]
    }

def fake_get_completion_invalid(self, messages, max_retries=3):
    # Return an invalid ticket missing many required fields.
    return {
        "tickets": [
            {
                "title": "Invalid Ticket"
                # Missing description, dependencies, risk_analysis, and pr_details content.
            }
        ]
    }

def test_generate_tickets_valid(monkeypatch):
    generator = TicketGenerator(api_key="dummy", model="gpt-4o", api_base="https://api.openai.com/v1/")
    # Monkey-patch _get_completion to simulate a valid API response.
    monkeypatch.setattr(generator, "_get_completion", fake_get_completion_success)
    tickets = generator.generate_tickets("This is a feature requirement with plenty of details.", interactive=True)
    assert isinstance(tickets, list)
    assert len(tickets) == 1
    ticket = tickets[0]
    # Verify that all required keys are present.
    assert 'title' in ticket
    assert 'description' in ticket
    assert 'dependencies' in ticket
    assert 'risk_analysis' in ticket
    assert 'pr_details' in ticket

def test_validate_ticket_invalid():
    generator = TicketGenerator(api_key="dummy", model="gpt-4o", api_base="https://api.openai.com/v1/")
    # Create an invalid ticket: description too short and pr_details missing sub-fields.
    invalid_ticket = {
        "title": "Ticket Title That Is Fine",
        "description": "Too short",  # Fails the minimum description length (expected ≥200)
        "dependencies": [],
        "risk_analysis": "",
        "pr_details": {}  # Missing required 'files' and 'changes'
    }
    issues = generator._validate_ticket(invalid_ticket)
    # Check that issues include a description length problem and missing PR sub-fields.
    assert any("Description too short" in issue for issue in issues)
    assert any("PR details missing required sub-fields" in issue for issue in issues) 