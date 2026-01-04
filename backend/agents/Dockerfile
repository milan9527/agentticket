# Dockerfile for AgentCore Data Agent
FROM --platform=linux/arm64 python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code and models
COPY agentcore_data_agent.py .
COPY models/ ./models/
COPY __init__.py .

# Expose port 8000 for MCP
EXPOSE 8000

# Set the entrypoint
CMD ["python", "agentcore_data_agent.py"]