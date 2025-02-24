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
        return """You are an expert project manager and developer tasked with creating highly detailed Jira tickets.
        Your goal is to produce exhaustive, verbose, and pedantic tickets that leave no detail unaddressed.
        
        For each ticket, you MUST include:
        1. Title: Clear, concise summary (max 100 characters)
        2. Description: Detailed explanation (minimum 200 words) covering:
           - Purpose and business value
           - Technical implementation details
           - Step-by-step implementation guide
           - Testing requirements
        3. Dependencies: Comprehensive list of prerequisite tickets
        4. Risk Analysis: Provide a detailed analysis of potential risks including:
           - Impact assessment
           - Probability evaluation
           - Mitigation strategies
        5. PR Details:
           - Specific files to modify
           - Detailed code changes expected
           - Testing approach
        
        Be exhaustive and leave no detail unaddressed. Format as JSON with the structure:
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
                }
            ]
        }"""

    def _create_user_prompt(self, requirements: str) -> str:
        """Create the user prompt for ticket generation."""
        return f"""Please analyze these requirements and create detailed Jira tickets:

{requirements}

Break this down into specific, actionable tickets. Be thorough and consider all implementation details."""

    def _validate_ticket(self, ticket: Dict) -> List[str]:
        """Validate a ticket meets requirements."""
        validation = TicketValidation()
        issues = []
        
        # Check required fields
        missing_fields = validation.required_fields - set(ticket.keys())
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check description length
        if len(ticket.get('description', '')) < validation.min_description_length:
            issues.append(f"Description too short (minimum {validation.min_description_length} characters)")
        
        return issues

    def _get_completion(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict:
        """Get completion from OpenAI API with retry logic."""
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
        
        while True:
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
                        all_issues.append(f"Ticket {i} issues:\n" + "\n".join(f"- {issue}" for issue in issues))
                
                if all_issues and not interactive:
                    raise ValueError("Generated tickets did not meet quality requirements:\n" + "\n".join(all_issues))
                
                if not interactive:
                    return tickets
                
                # In interactive mode, display tickets and get feedback
                print("\nGenerated Tickets:")
                for i, ticket in enumerate(tickets, 1):
                    print(f"\nTicket {i}:")
                    print(f"Title: {ticket['title']}")
                    print(f"Description (first 200 chars): {ticket['description'][:200]}...")
                
                feedback = input("\nAre you satisfied with these tickets? (y/n): ").lower()
                if feedback == 'y':
                    return tickets
                
                # Get feedback for refinement
                feedback = input("Please provide feedback for improvement: ")
                logger.debug(f"generate_tickets: Received user feedback: {feedback}")
                messages.extend([
                    {"role": "assistant", "content": json.dumps(response)},
                    {"role": "user", "content": f"Please refine the tickets based on this feedback: {feedback}"}
                ])
                logger.debug(f"generate_tickets: Updated messages: {messages}")
            
            except Exception as e:
                logger.error(f"generate_tickets: Exception encountered: {e}")
                if not interactive:
                    raise
                retry = input("Would you like to retry? (y/n): ").lower()
                if retry != 'y':
                    raise 