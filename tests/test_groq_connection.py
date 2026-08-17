"""
Test Groq API Connection
Phase 2: Tests for Groq API connectivity and model access

This test module verifies:
- Groq API key is set
- Simple completion works
- llama-3.1-8b-instant model is accessible
"""

import os
import pytest
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()


def test_groq_api_key_set():
    """
    Test that Groq API key is set in environment variables.
    """
    api_key = os.getenv("GROQ_API_KEY")
    assert api_key is not None, "GROQ_API_KEY not set in environment"
    assert len(api_key) > 0, "GROQ_API_KEY is empty"


def test_groq_simple_completion():
    """
    Test that a simple completion works with Groq API.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        pytest.skip("GROQ_API_KEY not set")
    
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            api_key=api_key
        )
        
        response = llm.invoke("Say 'Hello, World!'")
        
        assert response is not None, "No response from Groq API"
        assert response.content is not None, "Response content is None"
        assert len(response.content) > 0, "Response content is empty"
        
    except Exception as e:
        pytest.fail(f"Groq API completion failed: {str(e)}")


def test_groq_model_accessible():
    """
    Test that llama-3.1-8b-instant model is accessible.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        pytest.skip("GROQ_API_KEY not set")
    
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            api_key=api_key
        )
        
        # Test with a simple prompt
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="What is 2+2?")])
        
        assert response is not None, "No response from model"
        assert response.content is not None, "Response content is None"
        
        # Check that response contains something reasonable
        content = response.content.lower()
        assert "4" in content or "four" in content, f"Unexpected response: {response.content}"
        
    except Exception as e:
        pytest.fail(f"Model access failed: {str(e)}")


if __name__ == "__main__":
    # Run tests manually
    print("Running Groq connection tests...")
    
    test_groq_api_key_set()
    print("✓ API key test passed")
    
    test_groq_simple_completion()
    print("✓ Simple completion test passed")
    
    test_groq_model_accessible()
    print("✓ Model accessibility test passed")
    
    print("\nAll Groq connection tests passed!")
