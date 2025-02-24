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
    """Parse input content based on file type."""
    try:
        if file_type == '.html':
            soup = BeautifulSoup(content, 'lxml')
            # Extract text from body, or full document if no body
            return soup.body.get_text() if soup.body else soup.get_text()
        elif file_type == '.md':
            # Use mistune's default HTML renderer and then strip HTML tags
            html = mistune.html(content)
            soup = BeautifulSoup(html, 'lxml')
            return soup.get_text()
        return content  # Return as-is for plain text
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
    python app.py [--file <file>] [--model <model>] [--api-url <url>] [--api-key <key>] [--non-interactive]

Examples:
    # Generate tickets from a Markdown file with default model (gpt-4o)
    python app.py --file requirements.md

    # Use interactive mode with direct input
    python app.py

    # Non-interactive mode with specified model (GPT-4o or later only)
    python app.py --file specs.html --model gpt-4o --non-interactive
        """)
        sys.exit(0)
    
    # Get API key from arguments or environment
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key not found. Please provide it via --api-key or OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
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
        
        # Format output
        output = "# Generated Jira Tickets\n\n"
        for ticket in tickets:
            output += format_ticket_markdown(ticket)
        
        print(output)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 