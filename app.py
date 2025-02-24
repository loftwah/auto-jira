#!/usr/bin/env python3
"""
AI-Powered Jira Ticket Generator
A CLI tool that leverages OpenAI to transform requirements into detailed Jira tickets.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict
import os
from dotenv import load_dotenv
from ticket_generator import TicketGenerator
import json
from bs4 import BeautifulSoup
import mistune

# Load environment variables
load_dotenv()

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Jira Ticket Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Path to the requirements file (HTML, Markdown, or plain text)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o',  # Default to GPT-4o as required
        help='OpenAI model to use (recommended: gpt-4o or later)'
    )
    
    parser.add_argument(
        '--api-url',
        type=str,
        default='https://api.openai.com/v1/',
        help='Custom OpenAI API URL'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenAI API key (can also be set via OPENAI_API_KEY env variable)'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode'
    )

    # Added new argument for testing the OpenAI API
    parser.add_argument(
        '--test',
        action='store_true',
        help='Send a simple test prompt to the OpenAI API to verify connectivity'
    )

    # <-- New argument added for output format selection -->
    parser.add_argument(
        '--output-format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (markdown or json)'
    )

    return parser.parse_args()

def format_ticket_markdown(ticket: Dict) -> str:
    """Format a ticket as markdown."""
    # Precompute joined strings outside the f-string to avoid backslash in expression errors
    dependencies_str = "- " + "\n- ".join(ticket['dependencies']) if ticket['dependencies'] else "None"
    pr_files_str = "- " + "\n- ".join(ticket['pr_details']['files'])
    return f"""
# {ticket['title']}

## Description
{ticket['description']}

## Dependencies
{dependencies_str}

## Risk Analysis
{ticket['risk_analysis']}

## PR Details
### Files to Modify
{pr_files_str}

### Expected Changes
{ticket['pr_details']['changes']}

---
"""

def parse_input_content(content: str, file_type: str = None) -> str:
    """Parse and preprocess input content based on file type with stricter validation."""
    try:
        if file_type == '.html':
            soup = BeautifulSoup(content, 'lxml')
            text = soup.body.get_text() if soup.body else soup.get_text()
        elif file_type == '.md':
            # Use mistune's default HTML renderer and then strip HTML tags
            html = mistune.html(content)
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()
        else:
            text = content  # Return as-is for plain text

        # Preprocess the text: strip whitespace and normalize spaces/newlines
        text = text.strip()
        import re
        text = re.sub(r'\s+', ' ', text)

        # Validate minimum length - reject if less than 10 characters
        if len(text) < 10:
            raise ValueError("Input is too short (< 10 characters). Fix your input, dumbass.")

        # Validate that the input contains at least one required keyword (feature or bug)
        if "feature" not in text.lower() and "bug" not in text.lower():
            raise ValueError("Input does not contain expected keywords ('feature' or 'bug'). Provide a real fucking requirement.")

        return text
    except Exception as e:
        raise ValueError(f"Error parsing {file_type} content: {str(e)}")

def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        print("""
AI-Powered Jira Ticket Generator
===============================

Purpose: Transform requirements into detailed Jira tickets using OpenAI.

Usage:
    uv run app.py [--file <file>] [--model <model>] [--api-url <url>] [--api-key <key>] [--non-interactive]

Examples:
    # Generate tickets from a Markdown file with default model (gpt-4o)
    uv run app.py --file requirements.md

    # Use interactive mode with direct input
    uv run app.py

    # Non-interactive mode with specified model (GPT-4o or later only)
    uv run app.py --file specs.html --model gpt-4o --non-interactive
        """)
        sys.exit(0)
    
    # Get API key from arguments or environment
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key not found. Please provide it via --api-key or OPENAI_API_KEY environment variable.")
        sys.exit(1)

    # If --test flag is provided, send a simple test prompt to the OpenAI API
    if args.test:
        # Create the ticket generator that will be responsible for the API call.
        generator = TicketGenerator(
            api_key=api_key,
            model=args.model,
            api_base=args.api_url
        )
        # Define a simple set of messages to test the API connectivity:
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant. Please respond in JSON format."},
            {"role": "user", "content": "Hello, OpenAI. This is a test prompt. Please provide your response in JSON."}
        ]
        
        try:
            response = generator._get_completion(test_messages)
            print("Test response from OpenAI API:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error during API test: {str(e)}")
        sys.exit(0)
    
    # Get input content
    try:
        if not args.file and not args.non_interactive:
            print("Please enter your requirements (press Ctrl+D when finished):")
            requirements = sys.stdin.read()
            file_type = None
        elif args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File '{args.file}' not found.")
                sys.exit(1)
            
            file_type = file_path.suffix.lower()
            if file_type not in ['.md', '.html', '.txt', '']:
                print(f"Warning: Unrecognized file type '{file_type}'. Treating as plain text.")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                requirements = f.read()
        else:
            print("Error: In non-interactive mode, a file must be provided via --file")
            sys.exit(1)
        
        # Parse the input content
        requirements = parse_input_content(requirements, file_type)
        
    except Exception as e:
        print(f"Error processing input: {str(e)}")
        sys.exit(1)
    
    # Create ticket generator
    generator = TicketGenerator(
        api_key=api_key,
        model=args.model,
        api_base=args.api_url
    )
    
    try:
        # Generate tickets
        tickets = generator.generate_tickets(
            requirements=requirements,
            interactive=not args.non_interactive
        )
        
        # Format and display output based on format choice
        if args.output_format == 'json':
            print(json.dumps(tickets, indent=2))
        else:
            print("\n=== Generated Jira Tickets ===\n")
            for i, ticket in enumerate(tickets, 1):
                print(f"Ticket {i}:")
                print(format_ticket_markdown(ticket))
                print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 