import os
import httpx
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv(override=True)

def generate_test_cases(api_url, method):
    # Use a custom httpx client with SSL verification disabled
    # to handle corporate proxy / SSL inspection environments
    http_client = httpx.Client(verify=False)

    llm = ChatGroq(
        temperature=0.3,
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
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
