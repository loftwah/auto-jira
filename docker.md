# Docker

## Docker Deployment for AI-Powered Jira Ticket Generator

This document provides a comprehensive guide to deploying the **AI-Powered Jira Ticket Generator** using Docker and Docker Compose. It includes:

- A multi-stage Dockerfile for building an efficient and secure container.
- A Docker Compose configuration for simplified container management.
- Instructions for handling environment variables securely using a `.env` file.
- Step-by-step commands for building and running the application in both interactive and non-interactive modes.

By following this guide, you can set up a consistent, containerized environment with minimal effort, even if you're new to Docker.

---

## Dockerfile

The Dockerfile below uses a multi-stage build to create an optimized container. It leverages the Astral `uv` Docker image for dependency management and ensures the final image is lightweight and secure.

```dockerfile
# Builder stage: Use uv-enabled image to install dependencies and the project
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set environment variables for uv optimization
ENV UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Set working directory
WORKDIR /app

# Copy lockfile and project metadata for dependency installation
COPY uv.lock pyproject.toml ./

# Install dependencies without the project (for caching)
RUN uv sync --frozen --no-install-project

# Copy the entire project
COPY . .

# Install the project in non-editable mode
RUN uv sync --frozen --no-editable

# Runtime stage: Use a slim image for the final container
FROM python:3.12-slim

# Create a non-root user for security
RUN useradd --create-home appuser

# Set working directory
WORKDIR /home/appuser

# Switch to non-root user
USER appuser

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Set PATH to include the virtual environment's binaries
ENV PATH="/app/.venv/bin:$PATH"

# Set the entrypoint to run the application
# Assumes 'jira-ticket-generator' is defined in pyproject.toml under [project.scripts]
ENTRYPOINT ["jira-ticket-generator"]
```

### Explanation

- **Builder Stage**:

  - Uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`, a Debian-based image with Python 3.12 and `uv` pre-installed.
  - Sets environment variables to optimize `uv` by compiling bytecode and avoiding unnecessary Python downloads.
  - Installs dependencies first (without the project) for better caching, then installs the project in non-editable mode.

- **Runtime Stage**:
  - Uses `python:3.12-slim` for a lightweight final image.
  - Creates a non-root user (`appuser`) to enhance security.
  - Copies the virtual environment from the builder stage and updates the `PATH` to include its binaries.
  - Sets the entrypoint to `jira-ticket-generator`, assuming this script is defined in `pyproject.toml`. If your entrypoint differs, adjust it (e.g., `["uv", "run", "myapp.py"]`).

---

## Docker Compose Configuration

The `docker-compose.yml` file below simplifies container management and securely loads environment variables from a `.env` file.

```yaml
version: "3.8"

services:
  jira-ticket-generator:
    build: .
    image: jira-ticket-generator
    env_file:
      - .env
    stdin_open: true
    tty: true
```

- **`build: .`**: Builds the image from the Dockerfile in the current directory.
- **`image`**: Names the resulting image `jira-ticket-generator`.
- **`env_file`**: Loads environment variables from the `.env` file.
- **`stdin_open` and `tty`**: Enable interactive mode for CLI tools.

---

## Environment Variable Management

To securely manage sensitive information like the OpenAI API key, use a `.env` file.

### Step 1: Create a `.env` File

1. In the same directory as your `docker-compose.yml`, create a file named `.env`.
2. Add the following line, replacing `your_api_key_here` with your actual OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Optionally, add other variables as needed:
   ```
   OPENAI_MODEL=gpt-4-turbo
   OPENAI_API_URL=https://api.openai.com/v1/
   ```

### Why This Approach Works

- Keeps sensitive data out of command-line history and source code.
- Uses a simple `KEY=VALUE` format that’s easy to understand.
- Automatically loaded by Docker Compose, requiring no extra steps.

---

## Building and Running the Application

### Prerequisites

- Install Docker and Docker Compose on your system.
- Ensure the following files are in your project directory: `Dockerfile`, `docker-compose.yml`, `uv.lock`, `pyproject.toml`, and your project files.

### Step 1: Build the Docker Image

Run the following command to build the image:

```bash
docker build -t jira-ticket-generator .
```

This creates an image named `jira-ticket-generator` using the multi-stage Dockerfile.

### Step 2: Run the Application Using Docker Compose

The application supports multiple modes. Choose the one that fits your needs:

#### **Interactive Mode**

- Use this to manually input requirements via the terminal.
- Command:
  ```bash
  docker compose run --rm jira-ticket-generator
  ```
- Opens an interactive session for entering requirements and refining tickets.
- The `--rm` flag removes the container after execution to avoid clutter.

#### **Non-Interactive Mode with a File**

- Use this to process a file (e.g., `requirements.md`) without interaction.
- Command:
  ```bash
  docker compose run --rm -v $(pwd):/app jira-ticket-generator --file /app/requirements.md --non-interactive
  ```
- Mounts the current directory (`$(pwd)`) into `/app` in the container and processes the specified file.
- Output appears in the terminal (redirect with `> tickets.md` if desired).

#### **Non-Interactive Mode with Stdin**

- Use this to pipe input directly to the application.
- Command:
  ```bash
  echo "Build a login page" | docker compose run --rm jira-ticket-generator --non-interactive
  ```
- Sends the input ("Build a login page") for one-time ticket generation.

---

## Additional Notes

### **Security**

- **`.env` File**: Do not commit it to version control (add `.env` to `.gitignore`) to keep your API key secure.
- **Non-Root User**: The container runs as `appuser`, reducing the risk of privilege escalation.

### **Customization**

- Add more environment variables to `.env` as needed (e.g., `OPENAI_MODEL`, `OPENAI_API_URL`).
- Change the Python version in the Dockerfile if required (e.g., `python3.11-slim`).

### **Volume Mounting**

- Use `-v $(pwd):/app` when providing file inputs to make local files accessible in the container.
- This is optional and only needed for file-based operations.

### **Cleanup**

- The `--rm` flag ensures containers are removed after execution, keeping your system tidy.

### **Dependencies**

- The Dockerfile uses `uv` for dependency management in the build stage.
- The runtime image includes all dependencies via the copied virtual environment.

---

## Troubleshooting

### **Missing API Key**

- **Error**: "Missing `OPENAI_API_KEY`."
- **Fix**:
  1. Verify the `.env` file exists in the same directory as `docker-compose.yml`.
  2. Ensure it contains `OPENAI_API_KEY=your_api_key_here` with your actual key.
  3. Check for typos or extra spaces.

### **Interactive Mode Not Working**

- **Issue**: No terminal input.
- **Fix**: Use `docker compose run` (not `up`) and confirm `stdin_open: true` and `tty: true` are in `docker-compose.yml`.

### **File Not Found**

- **Error**: "Cannot find file."
- **Fix**:
  1. Ensure the file (e.g., `requirements.md`) exists in your current directory.
  2. Use `-v $(pwd):/app` to mount the directory correctly.
