# AI-Powered Jira Ticket Generator

The AI-Powered Jira Ticket Generator is a CLI tool that leverages OpenAI to transform high-level project requirements into detailed Jira tickets. Whether your input is in HTML, Markdown, or plain text, the tool uses GPT-4 (or later) to generate tickets complete with metadata, risk assessments, and pull request details.

## Key Features

- **Input Parsing:** Supports HTML, Markdown, and plain text.
- **Ticket Generation:** Produces comprehensive Jira tickets including:
  - Title and description
  - Dependencies
  - Risk analysis
  - Pull request details
- **Modes:**
  - **Interactive Mode:** Iteratively refine tickets with live feedback.
  - **Non-Interactive Mode:** Generate tickets in a one-shot command.
- **Customizable Integration:** Configure OpenAI API URL and API key as needed.
- **Output Formats:** Defaults to Markdown; JSON output is also supported.

## Getting Started

### Prerequisites

- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) for virtual environment and dependency management
- Python dependencies (see [requirements.txt](requirements.txt) for details)

### Setup Instructions

1. **Create and activate a virtual environment:**
   ```bash
   uv venv
   # On Linux/Mac:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```
2. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```

## Running the Application

### Non-Interactive Mode (Automated Ticket Generation)

For a fast, one-shot ticket generation from a requirements file, run:

```bash
uv run app.py --file requirements.md --non-interactive
```

**What to Expect:**

- **Input:** The tool reads your `requirements.md` file containing the project requirements.
- **Processing:** The content is sent to the GPT-4 (or later) API, which processes and generates detailed ticket information.
- **Output:** Tickets are output in Markdown format and include comprehensive details:
  - **Title** and **Description** of the ticket
  - **Dependencies** for further work
  - **Risk Assessments** and potential issues
  - **Pull Request (PR) Details** for implementation
- **Automation:** The command executes without prompting for further interaction, perfect for automated workflows.

### Interactive Mode (Iterative Refinement)

To manually refine the ticket creation process, simply run:

```bash
uv run app.py
```

- **Direct Input:** If no file is provided, you will be prompted to paste or type your requirements.
- **Feedback Guided:** After initial ticket generation, you can review the output and provide feedback for refinements.
- **Repeat as Needed:** Continue refining until you are completely satisfied with the tickets.

## Docker Deployment

For containerized deployment, see [docker.md](docker.md) which provides detailed instructions on building the Docker image, running the container, and managing environment variables securely.

## Contributing

Contributions are welcome! Please reference the guidelines in [.cursorrules](.cursorrules) for code style, testing, documentation, and security guidelines before contributing.

## License

This project is licensed under the MIT License. Please see the [LICENSE](LICENSE) file for further details.
