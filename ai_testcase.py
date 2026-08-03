import os
import httpx
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load .env file first (local development)
load_dotenv(override=True)

def _get_groq_api_key():
    """Get GROQ_API_KEY — checks .env/environment first, then Streamlit secrets (cloud)."""
    # 1. Try environment variable first (works locally via .env)
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    # 2. Fall back to Streamlit secrets (Streamlit Cloud deployment)
    try:
        import streamlit as st
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None

def generate_test_cases(api_url, method):
    # Use a custom httpx client with SSL verification disabled
    # to handle corporate proxy / SSL inspection environments
    http_client = httpx.Client(verify=False)

    llm = ChatGroq(
        temperature=0.3,
        model="llama-3.3-70b-versatile",
        api_key=_get_groq_api_key(),
        http_client=http_client,
    )

    prompt = f"""
You are a Senior QA API Tester.

Write API test cases for:

Endpoint: {api_url}
Method: {method}

Include:
1. Positive test cases
2. Negative test cases
3. Status code validation
4. Security checks
5. Performance checks

Format:
TC-01 | Title | Steps | Expected Result
"""

    response = llm.invoke(prompt)
    return response.content
