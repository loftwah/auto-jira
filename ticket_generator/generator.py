"""
Core ticket generation functionality.
"""

from typing import List, Dict, Optional
import openai
import json
import time
from dataclasses import dataclass
from openai import APIError, RateLimitError
import logging

logger = logging.getLogger(__name__)

@dataclass
class TicketValidation:
    """Validation rules for generated tickets."""
    min_description_length: int = 200
    required_fields: set = frozenset({
        'title', 'description', 'dependencies', 'risk_analysis', 'pr_details'
    })

class TicketGenerator:
    """Handles the generation of Jira tickets using OpenAI's API."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",  # Updated from gpt-4 to gpt-4o
        api_base: str = "https://api.openai.com/v1/"
    ):
        """
        Initialize the ticket generator.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model name (recommended: gpt-4o or later)
            api_base: Base URL for the OpenAI API
        """
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        if not model.startswith("gpt-4o"):  # Updated check for gpt-4o
            print("Warning: Using a model other than GPT-4o. Ensure it is GPT-4o or later for optimal performance.")

    def _create_system_prompt(self) -> str:
        """Create an enhanced system prompt for ticket generation."""
        return """You are an expert project manager and developer tasked with creating highly detailed Jira tickets for a CLI tool that transforms project requirements into actionable tasks. The application consists of multiple components including input parsing (for HTML, Markdown, and plain text), AI-powered ticket generation using OpenAI's API, a command-line interface supporting interactive and non-interactive modes, secure API key management, and comprehensive testing and CI/CD integration.
        
For each ticket, you MUST include:
1. Title: A short, clear summary (max 100 characters).
2. Description: A detailed explanation covering the purpose, technical implementation details, step-by-step instructions, and testing requirements.
3. Dependencies: A list of prerequisite tasks or tickets.
4. Risk Analysis: Detailed potential risks, their impact, likelihood, and mitigation strategies.
5. PR Details: Specific files to modify, expected code changes, and the testing approach.

Break down the overall requirements into separate, actionable tickets covering at least these areas:
- Input Parsing Module: Handling different formats (HTML, Markdown, plain text) and error handling.
- Ticket Generation Engine: Integrating with OpenAI's API and formatting tickets.
- CLI Interface: Parsing command-line arguments, interactive prompts, and mode handling.
- API Key Management: Securing and managing API keys via CLI, environment variables, or .env files.
- Testing and CI/CD Setup: Comprehensive unit, integration, and end-to-end tests along with pipeline integration.

Format your output as JSON with the following structure:
{
    "tickets": [
        {
            "title": "string",
            "description": "string",
            "dependencies": ["string"],
            "risk_analysis": "string",
            "pr_details": {
                "files": ["string"],
                "changes": "string"
            }
        },
        ...
    ]
}"""

    def _create_user_prompt(self, requirements: str) -> str:
        """Create the user prompt for ticket generation."""
        return f"""Please analyze the following project requirements and break them down into detailed, actionable Jira tickets. Ensure that you create separate tickets for each major functional area such as Input Parsing, Ticket Generation Engine, CLI Interface, API Key Management, and Testing/CI/CD integration. Each ticket should include:
- A concise title.
- A detailed description covering purpose, implementation details, step-by-step instructions, and testing.
- Any dependencies on other tasks.
- A risk analysis detailing potential challenges and mitigation strategies.
- PR details listing specific files and code changes needed.

Requirements:
{requirements}"""

    def _validate_ticket(self, ticket: Dict) -> List[str]:
        """Validate a ticket meets requirements, including title length,
        description word count, and PR details structure."""
        validation = TicketValidation()
        issues = []
        
        # Check required fields
        missing_fields = validation.required_fields - set(ticket.keys())
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check title length (max 100 characters)
        title = ticket.get('title', '')
        if len(title) > 100:
            issues.append("Title too long (maximum 100 characters)")
        
        # Check description length (minimum characters)
        description = ticket.get('description', '')
        if len(description) < validation.min_description_length:
            issues.append(f"Description too short (minimum {validation.min_description_length} characters)")
        
        # Validate PR details structure
        pr_details = ticket.get('pr_details')
        if not isinstance(pr_details, dict):
            issues.append("PR details are missing or not in the expected format (should be a dict)")
        else:
            if 'files' not in pr_details or 'changes' not in pr_details:
                issues.append("PR details missing required sub-fields: 'files' and 'changes'")
        
        return issues

    def _get_completion(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict:
        """Get completion from OpenAI API with retry logic and improved error handling."""
        for attempt in range(max_retries):
            try:
                logger.debug(f"_get_completion: Attempt {attempt+1}/{max_retries}")
                logger.debug(f"_get_completion: Sending messages: {messages}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                logger.debug(f"_get_completion: Received raw response: {response}")
                parsed_response = json.loads(response.choices[0].message.content)
                logger.debug(f"_get_completion: Parsed response: {parsed_response}")
                return parsed_response
            except RateLimitError as e:
                logger.warning(f"_get_completion: RateLimitError encountered: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"_get_completion: Retrying after {wait_time} seconds due to rate limit.")
                    time.sleep(wait_time)  # Exponential backoff
                    continue
                raise
            except APIError as e:
                logger.warning(f"_get_completion: APIError encountered: {e}")
                if attempt < max_retries - 1 and e.status_code in {500, 502, 503, 504}:
                    wait_time = 2 ** attempt
                    logger.warning(f"_get_completion: Retrying after {wait_time} seconds due to server error.")
                    time.sleep(wait_time)
                    continue
                raise
            except json.JSONDecodeError as e:
                logger.error(f"_get_completion: Failed to decode JSON: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"_get_completion: Retrying after {wait_time} seconds due to JSON decode error.")
                    time.sleep(wait_time)
                    continue
                print("Received an invalid response from OpenAI API. Check your API and try again later.")
                raise
            except Exception as e:
                # Import requests here to check if it's a network-related error
                import requests
                if isinstance(e, requests.exceptions.RequestException):
                    logger.error(f"_get_completion: Network error encountered: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"_get_completion: Retrying after {wait_time} seconds due to network error. Check your internet, dumbass.")
                        time.sleep(wait_time)
                        continue
                    print("Network's down, try again later.")
                    raise
                else:
                    logger.error(f"_get_completion: Unexpected error encountered: {e}", exc_info=True)
                    print("An unexpected error occurred. See logs for details.")
                    raise

    def generate_tickets(
        self,
        requirements: str,
        interactive: bool = True
    ) -> List[Dict]:
        """Generate tickets with enhanced validation and feedback."""
        messages = [
            {"role": "system", "content": self._create_system_prompt()},
            {"role": "user", "content": self._create_user_prompt(requirements)}
        ]
        logger.debug(f"generate_tickets: Initial messages: {messages}")

        # For non-interactive mode, try a few times before giving up
        non_interactive_max_attempts = 3
        attempts = 0

        while True:
            attempts += 1
            try:
                response = self._get_completion(messages)
                logger.debug(f"generate_tickets: API response received: {response}")
                tickets = response.get("tickets", [])
                
                # Validate all tickets
                all_issues = []
                for i, ticket in enumerate(tickets, 1):
                    issues = self._validate_ticket(ticket)
                    logger.debug(f"generate_tickets: Validation for ticket {i}: {issues}")
                    if issues:
                        all_issues.append(f"Ticket {i} issues:\n" +
                                          "\n".join(f"- {issue}" for issue in issues))
                
                # Display the generated tickets first
                print("\nGenerated Tickets:")
                for i, ticket in enumerate(tickets, 1):
                    print(f"\nTicket {i}:")
                    print(f"Title: {ticket.get('title', '')}")
                    print(f"Description (first 200 chars): {ticket.get('description', '')[:200]}...")

                if all_issues:
                    print("\nIssues detected:")
                    print("\n".join(all_issues))
                
                if not interactive:
                    if attempts < non_interactive_max_attempts and all_issues:
                        logger.warning("Attempt {}/{}: Generated tickets did not meet quality requirements:\n{}\nRetrying...".format(
                            attempts, non_interactive_max_attempts, "\n".join(all_issues)))
                        continue
                    return tickets
                
                # Interactive mode: ask for feedback
                feedback = input("\nAre you satisfied with these tickets? (y/n): ").lower()
                if feedback == 'y':
                    return tickets
                else:
                    # Get specific feedback from the user
                    user_feedback = input("\nPlease describe what you'd like to improve: ")
                    # Add the feedback to messages for context in the next generation
                    messages.extend([
                        {"role": "assistant", "content": json.dumps(response)},
                        {"role": "user", "content": f"Please regenerate the tickets with these improvements: {user_feedback}"}
                    ])
                    continue
                
            except Exception as e:
                logger.error(f"generate_tickets: Exception encountered: {e}")
                raise e 