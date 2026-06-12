"""
Pytest configuration for the Nexus Agent test suite.
"""
import pytest
import os

# Ensure GROQ_API_KEY is set for tests
# In CI, set this as an environment variable
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")


@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:8000"
