# Force Railway to use Python 3.11
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the project files
COPY . /app/

# Install pip and dependencies
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

# Expose the port
EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
