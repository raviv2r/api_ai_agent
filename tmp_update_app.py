from pathlib import Path

content = '''import streamlit as st
import json
from urllib.parse import urlparse, parse_qs

from ai_testcase import generate_test_cases
from api_runner import run_api
from report import save_report

st.title("🚀 AI API Testing Agent V1")

url = st.text_input("Enter API URL")
method = st.selectbox("Select Method", ["GET", "POST", "PUT", "DELETE"])

default_headers_template = json.dumps(
    {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer <token>",
    },
    indent=2,
)

st.text_area(
    "Header Template (copy this as a starting point)",
    default_headers_template,
    height=120,
    disabled=True,
)
headers_text = st.text_area("Enter JSON Headers (Optional)", "{}")
body_text = st.text_area("Enter JSON Body (Optional)", "{}")


def detect_authorization(url_value, headers_value, body_value):
    if headers_value:
        for key in headers_value:
            if key.lower() == "authorization":
                return headers_value, "provided in headers"

    token_fields = [
        "authorization",
        "auth",
        "token",
        "access_token",
        "accessToken",
        "bearer_token",
        "bearerToken",
    ]

    if isinstance(body_value, dict):
        for field in token_fields:
            if field in body_value and body_value[field]:
                raw_token = body_value[field]
                if isinstance(raw_token, str):
                    token = raw_token
                else:
                    token = json.dumps(raw_token)

                if token.lower().startswith("bearer ") or token.lower().startswith("basic "):
                    headers_value = headers_value or {}
                    headers_value["Authorization"] = token
                else:
                    headers_value = headers_value or {}
                    headers_value["Authorization"] = f"Bearer {token}"

                return headers_value, f"auto-detected from body field '{field}'"

    parsed_url = urlparse(url_value)
    query_values = parse_qs(parsed_url.query)
    for field in token_fields:
        if field in query_values and query_values[field]:
            token = query_values[field][0]
            headers_value = headers_value or {}
            headers_value["Authorization"] = f"Bearer {token}"
            return headers_value, f"auto-detected from URL query parameter '{field}'"

    return headers_value, None


if st.button("Run API Agent"):
    if not url:
        st.error("Enter a valid API URL before running the agent.")
        st.stop()

    headers = {}
    body = None

    if headers_text.strip():
        try:
            headers = json.loads(headers_text)
            if not isinstance(headers, dict):
                raise ValueError
        except Exception:
            st.error("Headers must be a valid JSON object.")
            st.stop()

    if body_text.strip():
        try:
            body = json.loads(body_text)
        except Exception:
            st.error("Body must be valid JSON.")
            st.stop()

    headers, auth_note = detect_authorization(url, headers, body)
    if auth_note:
        st.info(f"Authorization header set {auth_note}.")

    diagnostics = {
        "url": url,
        "method": method,
        "headers": headers,
        "body": body,
    }

    st.subheader("🧠 AI Generated Test Cases")
    tc = generate_test_cases(url, method)
    st.write(tc)

    st.subheader("⚙️ API Execution Result")
    result = run_api(method, url, body, headers)

    st.json(result)

    st.subheader("🔍 Production-like Request Diagnostics")
    st.markdown("Use these details to compare your agent request with production.")
    st.json(diagnostics)
    if auth_note:
        st.markdown(f"**Authorization auto-detection:** {auth_note}")
    else:
        st.markdown("**Authorization auto-detection:** Not detected")

    save_report({
        "url": url,
        "method": method,
        "status": result.get("status_code"),
        "time": result.get("response_time"),
    })

    st.success("✅ Report Saved")
'''

Path('app.py').write_text(content, encoding='utf-8')
print('app.py successfully updated')
