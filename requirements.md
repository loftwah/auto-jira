# AI-Powered Jira Ticket Generator Requirements

**Version**: 1.0  
**Author**: Dean Lofts  
**Date**: 24 February 2025

---

## 1. Overview

### 1.1 Purpose

The AI-Powered Jira Ticket Generator is a CLI tool that leverages OpenAI to transform high-level project requirements into exhaustive, pedantic, and detailed hypothetical Jira-style tickets. It breaks down requirements into actionable tasks—including detailed descriptions, dependencies, risk analysis, and associated pull request (PR) details—ensuring that no stone is left unturned in planning the project.

### 1.2 Scope

The tool will:

- **Be CLI-based in Python** using the `uv` tool for virtual environment and dependency management.
- **Accept requirements** in HTML, Markdown, or plain text formats via file input or direct terminal entry.
- **Integrate with OpenAI’s API** (defaulting to GPT‑4o) while allowing users to change the model name and API URL to support any OpenAI‑compatible model that is GPT‑4o or later.
- **Generate detailed, hypothetical Jira tickets** that include comprehensive metadata and verbose PR details.
- **Support both interactive and non-interactive modes**:
  - **Interactive Mode:** Iteratively refine tickets with user feedback until fully satisfied.
  - **Non-Interactive Mode:** Provide a one-shot generation based on the input.
- **Output tickets in Markdown by default**, with options for other formats (e.g., JSON) and piping to files.

---

## 2. Functional Requirements

### 2.1 Core Features

| **ID** | **Feature Name**     | **Description**                                                                                                        |
| ------ | -------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| FR1    | Input Parsing        | Parse requirements from HTML, Markdown, or plain text documents provided via file or terminal input.                   |
| FR2    | Ticket Generation    | Use AI to generate exhaustive and verbose Jira tickets with detailed metadata, ensuring every detail is covered.       |
| FR3    | Interactive Mode     | Allow iterative refinement with prompts—displaying generated tickets, soliciting feedback, and looping until approved. |
| FR4    | Non-Interactive Mode | Generate tickets in a one-shot execution without iterative feedback.                                                   |
| FR5    | Help & Documentation | Display the tool's purpose, usage instructions, and examples when run without arguments.                               |

#### 2.1.1 Interactive Mode Details

- **Prompt for Requirements:** If no `--file` flag is provided, prompt the user for input directly.
- **Display Output:** Show generated tickets in Markdown.
- **Feedback Loop:** Ask, "Are you satisfied with this output? (y/n)" and if not, prompt for feedback to regenerate tickets until confirmed.

#### 2.1.2 Non-Interactive Mode Details

- **Input Handling:** Accept requirements from a file (`--file`) or piped input.
- **Single Output:** Generate and output tickets once, without prompting for feedback.

### 2.2 AI & OpenAI Integration

| **ID** | **Feature Name**     | **Description**                                                                                                                               |
| ------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| AI1    | Default Model        | Use OpenAI’s GPT‑4o model as the default for ticket generation.                                                                               |
| AI2    | Custom Model Support | Allow users to specify any OpenAI‑compatible model (default: GPT‑4o; support for GPT‑4o and/or later) via CLI flags or environment variables. |
| AI3    | Custom API URL       | Support custom API URLs (e.g., `https://api.openai.com/v1/` or `http://localhost:8000/v1/`) to accommodate self‑hosted models.                |
| AI4    | API Key Management   | Securely handle API keys via CLI (`--api-key`), environment variables (`OPENAI_API_KEY`), or a `.env` file.                                   |
| AI5    | Structured Output    | Use OpenAI’s JSON‑mode to generate tickets in a predefined schema for consistent parsing.                                                     |
| AI6    | Context Awareness    | Maintain conversation context in interactive mode to incorporate iterative user feedback effectively.                                         |

#### 2.2.1 CLI Flags for AI Configuration

- `--model <model-name>`: Specify the AI model (default: `gpt-4o`).
- `--api-url <url>`: Set a custom API URL (default: `https://api.openai.com/v1/`).
- `--api-key <key>`: Provide an API key (checked in order: CLI arg, `OPENAI_API_KEY` environment variable, then `.env` file).

#### 2.2.2 Ticket Structure

Each generated ticket will include:

- **Title:** A concise summary of the task.
- **Description:** A verbose explanation covering purpose, scope, and implementation details.
- **Dependencies:** A list of prerequisite tickets by title.
- **Risk Analysis:** Detailed risks and challenges.
- **PR Details:**
  - **Files:** List of files to be modified or created.
  - **Changes:** Detailed descriptions of the expected code modifications.

---

## 3. Non-Functional Requirements

| **ID** | **Category**            | **Description**                                                                                                                                                |
| ------ | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR1   | Exhaustiveness & Detail | Generate tickets with exhaustive detail, ensuring every aspect of the requirements is meticulously processed and documented in a pedantic and verbose manner.  |
| NFR2   | Scalability             | Handle large requirement documents by processing sections independently and warning if any section exceeds token limits.                                       |
| NFR3   | Security                | Securely manage API keys and sensitive data; do not store sensitive data in logs or memory beyond the processing period.                                       |
| NFR4   | Usability               | Provide an intuitive CLI interface with clear prompts, minimal setup (e.g., `uv venv && uv pip install -r requirements.txt`), and comprehensive built-in help. |
| NFR5   | API Resilience          | Gracefully handle OpenAI API rate limits, errors, or downtime using retries and clear error messaging.                                                         |

---

## 4. Constraints & Considerations

- **OpenAI API Rate Limits:** Implement throttling or chunking strategies to stay within API limits.
- **Cost Management:** Optimise token usage to reduce OpenAI API costs while ensuring exhaustive output.
- **Input Validation:** Validate file formats and provide clear error messages (e.g., missing HTML `<body>` tag).
- **Chunking Strategy:** For oversized inputs, process by sections while allowing the user to determine division where needed.
- **Integration Complexity:** Consider future integrations with Jira and other project management tools when structuring output.

---

## 5. Dependencies & Setup Instructions

### 5.1 Dependencies

The tool relies on the following Python packages, managed via `uv`:

```
openai          # For OpenAI API integration
mistune         # For Markdown parsing and structured extraction
beautifulsoup4  # For HTML parsing and structured extraction
lxml            # Parser for BeautifulSoup (recommended for performance)
python-dotenv   # For loading API keys from .env files
```

_Note: Versions are not locked to allow flexibility during development._

### 5.2 Setup Instructions

1. **Create a virtual environment:**
   ```bash
   uv venv
   ```
2. **Activate the virtual environment:**
   - **Linux/Mac:**
     ```bash
     source .venv/bin/activate
     ```
   - **Windows:**
     ```bash
     .venv\Scripts\activate
     ```
3. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```
4. **Run the tool:**

   ```bash
   uv run myapp.py
   ```

   - Running `uv run myapp.py` without arguments should display the project description and help with usage examples.
   - Use `--file <filename>` to provide a requirements document or enter requirements directly in the terminal.
   - Toggle between interactive and non-interactive modes with `--non-interactive` for one-shot ticket generation.
