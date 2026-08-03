import streamlit as st
import json
import uuid
from urllib.parse import urlparse, parse_qs

from ai_testcase import generate_test_cases
from api_runner import run_api
from report import save_report
from script_generator import PostmanScriptGenerator, TestCaseGenerator
from test_executor import TestExecutor
from schema_validator import SchemaValidator
from security_validator import SecurityValidator
from error_validator import ErrorValidator
from excel_reporter import ExcelReportGenerator
from custom_script_executor import CustomScriptExecutor

st.title("🚀 AI API Testing Agent V1")

url = st.text_input("Enter API URL")
method = st.selectbox("Select Method", ["GET", "POST", "PUT", "DELETE"])

# Auth Type Selection
auth_type = st.selectbox(
    "Auth Type",
    [
        "No Auth",
        "Bearer Token",
        "Basic Auth",
        "API Key",
        "JWT Bearer",
        "OAuth 2.0",
        "Custom Header",
    ],
)


def get_default_headers_template(method_value):
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer <token>",
    }

    if method_value in {"POST", "PUT"}:
        headers["Content-Type"] = "application/json"

    return json.dumps(headers, indent=2)


default_headers_template = get_default_headers_template(method)

st.text_area(
    "Header Template (copy this as a starting point)",
    default_headers_template,
    height=120,
    disabled=True,
)

# Dynamic Auth Input Based on Auth Type
auth_value = None
if auth_type == "Bearer Token":
    auth_value = st.text_input("Enter Bearer Token", placeholder="your-token-here")
elif auth_type == "Basic Auth":
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username", placeholder="username")
    with col2:
        password = st.text_input("Password", placeholder="password", type="password")
    if username and password:
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        auth_value = f"Basic {credentials}"
elif auth_type == "API Key":
    api_key = st.text_input("Enter API Key", placeholder="your-api-key")
    api_key_header = st.text_input("Header Name", value="X-API-Key", placeholder="X-API-Key")
    if api_key:
        auth_value = (api_key_header, api_key)
elif auth_type == "JWT Bearer":
    auth_value = st.text_area("Enter JWT Token", placeholder="your-jwt-token", height=100)
elif auth_type == "OAuth 2.0":
    auth_value = st.text_input("Enter Access Token", placeholder="your-access-token")
elif auth_type == "Custom Header":
    header_name = st.text_input("Header Name", placeholder="X-Custom-Auth")
    header_value = st.text_input("Header Value", placeholder="your-value")
    if header_name and header_value:
        auth_value = (header_name, header_value)

headers_text = st.text_area("Enter Additional JSON Headers (Optional)", "{}")
body_text = st.text_area("Enter JSON Body (Optional)", "{}")

# ─────────────────────────────────────────────────────────────────────────────
# 📝 Post-response Script Editor  (Postman-style)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📝 Post-response Test Scripts")
st.caption(
    "Write Python assertions using the `pm` helper — works just like Postman's Post-response scripts. "
    "Default scripts run automatically. Add, edit, enable/disable, or delete custom scripts below."
)

# Initialise session state for scripts
if "custom_scripts" not in st.session_state:
    st.session_state.custom_scripts = [s.copy() for s in CustomScriptExecutor.DEFAULT_SCRIPTS]

# ── Tabs: Default Scripts  |  Custom Scripts ──────────────────────────────
tab_default, tab_custom, tab_help = st.tabs(["⚙️ Default Scripts", "✏️ Custom Scripts", "📖 Help & Examples"])

# ── Tab 1: View / toggle default scripts ──────────────────────────────────
with tab_default:
    st.info("Default scripts are auto-generated and always executed. You can enable/disable individual ones.")
    default_scripts = [s for s in st.session_state.custom_scripts if s["id"].startswith("default_")]
    for i, script in enumerate(default_scripts):
        col_en, col_name, col_script = st.columns([0.08, 0.25, 0.67])
        with col_en:
            enabled = st.checkbox("", value=script["enabled"], key=f"def_en_{script['id']}", label_visibility="collapsed")
            # sync back
            for s in st.session_state.custom_scripts:
                if s["id"] == script["id"]:
                    s["enabled"] = enabled
        with col_name:
            st.markdown(f"**{script['name']}**")
        with col_script:
            st.code(script["script"], language="python")

# ── Tab 2: Add / edit / delete custom scripts ─────────────────────────────
with tab_custom:
    custom_scripts = [s for s in st.session_state.custom_scripts if not s["id"].startswith("default_")]

    # Add new script form
    with st.expander("➕ Add New Custom Script", expanded=len(custom_scripts) == 0):
        new_name = st.text_input("Script Name", placeholder="e.g. Check data field exists", key="new_script_name")
        new_code = st.text_area(
            "Script Code",
            height=120,
            placeholder=(
                '# Example:\n'
                'data = pm.response.json()\n'
                'pm.test("data field exists", lambda: pm.expect(data).have_property("data"))\n'
                'pm.test("status is 200", lambda: pm.expect(pm.response.code).equal(200))'
            ),
            key="new_script_code",
        )
        if st.button("➕ Add Script", key="btn_add_script"):
            if new_name.strip() and new_code.strip():
                st.session_state.custom_scripts.append({
                    "id": f"custom_{uuid.uuid4().hex[:8]}",
                    "name": new_name.strip(),
                    "script": new_code.strip(),
                    "enabled": True,
                })
                st.success(f"✅ Script '{new_name}' added!")
                st.rerun()
            else:
                st.warning("Please enter both a script name and code.")

    # List existing custom scripts
    if not custom_scripts:
        st.info("No custom scripts yet. Use the form above to add one.")
    else:
        st.markdown(f"**{len(custom_scripts)} custom script(s):**")
        for i, script in enumerate(custom_scripts):
            with st.expander(
                f"{'✅' if script['enabled'] else '⏸️'}  {script['name']}",
                expanded=False,
            ):
                col_en, col_del = st.columns([0.5, 0.5])
                with col_en:
                    new_enabled = st.checkbox(
                        "Enabled",
                        value=script["enabled"],
                        key=f"cust_en_{script['id']}",
                    )
                with col_del:
                    delete = st.button("🗑️ Delete", key=f"del_{script['id']}")

                edited_name = st.text_input(
                    "Script Name",
                    value=script["name"],
                    key=f"name_{script['id']}",
                )
                edited_code = st.text_area(
                    "Script Code",
                    value=script["script"],
                    height=130,
                    key=f"code_{script['id']}",
                )

                col_save, _ = st.columns([0.3, 0.7])
                with col_save:
                    save_btn = st.button("💾 Save Changes", key=f"save_{script['id']}")

                if save_btn:
                    for s in st.session_state.custom_scripts:
                        if s["id"] == script["id"]:
                            s["name"] = edited_name.strip()
                            s["script"] = edited_code.strip()
                            s["enabled"] = new_enabled
                    st.success(f"✅ '{edited_name}' saved!")
                    st.rerun()

                if delete:
                    st.session_state.custom_scripts = [
                        s for s in st.session_state.custom_scripts if s["id"] != script["id"]
                    ]
                    st.warning(f"🗑️ Script deleted.")
                    st.rerun()

                # sync enable toggle even without save
                for s in st.session_state.custom_scripts:
                    if s["id"] == script["id"]:
                        s["enabled"] = new_enabled

# ── Tab 3: Help ───────────────────────────────────────────────────────────
with tab_help:
    st.markdown("""
### 📖 How to write Post-response Scripts

Scripts run **after** each API call. Use the `pm` object (same concept as Postman):

---

#### `pm.response` properties
| Property | Description |
|---|---|
| `pm.response.code` | HTTP status code (int) |
| `pm.response.responseTime` | Response time in ms (int) |
| `pm.response.json()` | Parsed response body (dict/list) |
| `pm.response.text()` | Raw response as string |
| `pm.response.header("name")` | Get a response header value |

---

#### `pm.expect()` assertions
```python
pm.expect(value).equal(expected)          # exact match
pm.expect(value).not_.equal(unexpected)   # negation
pm.expect(value).include("substring")     # contains
pm.expect(value).a("string")              # type check: string/number/boolean/object/array
pm.expect(value).below(2000)              # less than
pm.expect(value).above(0)                 # greater than
pm.expect(value).within(200, 299)         # range
pm.expect(value).have_property("key")     # dict key exists
pm.expect(value).match(r"regex")          # regex match
pm.expect(value).not_.be_empty()          # not empty
```

---

#### Full script examples

```python
# ── Example 1: Status code check ──
pm.test("Status is 200", lambda: pm.expect(pm.response.code).equal(200))

# ── Example 2: Response time ──
pm.test("Fast response", lambda: pm.expect(pm.response.responseTime).below(2000))

# ── Example 3: Field existence ──
data = pm.response.json()
pm.test("data field present", lambda: pm.expect(data).have_property("data"))

# ── Example 4: Field value ──
data = pm.response.json()
pm.test("status is success", lambda: pm.expect(data.get("status")).equal("success"))

# ── Example 5: Array not empty ──
data = pm.response.json()
items = data.get("data", [])
pm.test("items list not empty", lambda: pm.expect(items).not_.be_empty())

# ── Example 6: Nested field check ──
data = pm.response.json()
pm.test("nested id exists", lambda: pm.expect(data.get("user", {}).get("id")).not_.be_null())

# ── Example 7: Type check ──
data = pm.response.json()
pm.test("id is a number", lambda: pm.expect(data.get("id")).a("number"))
```
""")

st.markdown("---")


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

    # Add auth header based on auth_type
    if auth_type != "No Auth":
        if auth_type == "Bearer Token" and auth_value:
            headers["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "API Key" and isinstance(auth_value, tuple):
            header_name, header_val = auth_value
            headers[header_name] = header_val
        elif auth_type == "Custom Header" and isinstance(auth_value, tuple):
            header_name, header_val = auth_value
            headers[header_name] = header_val
        elif auth_value and not isinstance(auth_value, tuple):
            headers["Authorization"] = auth_value

    if headers_text.strip():
        try:
            additional_headers = json.loads(headers_text)
            if isinstance(additional_headers, dict):
                headers.update(additional_headers)
        except Exception:
            st.error("Additional headers must be valid JSON.")
            st.stop()

    if body_text.strip():
        try:
            body = json.loads(body_text)
        except Exception:
            st.error("Body must be valid JSON.")
            st.stop()

    # Skip auto-detection if manual auth is selected
    if auth_type == "No Auth":
        headers, auth_note = detect_authorization(url, headers, body)
    else:
        auth_note = None

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

    # Extract response data for script generation and testing
    response_data = result.get("response", {})
    status_code = result.get("status_code", 0)
    response_time = result.get("response_time", 0)

    # Initialize variables for report generation
    test_results = []
    test_cases = []
    summary = {}

    # Generate Postman Test Script
    st.subheader("📝 Generated Postman Test Script")
    try:
        script_generator = PostmanScriptGenerator(response_data, status_code, response_time, url, headers)
        postman_script = script_generator.generate_test_script()
        
        # Display script in a code block
        st.code(postman_script, language="javascript")
        
        # Copy button
        st.write("Copy the script above to use in Postman")
    except Exception as e:
        st.error(f"Error generating script: {str(e)}")

    # Execute Tests
    st.subheader("✅ Auto-Generated Test Results")
    try:
        test_executor = TestExecutor(response_data, status_code, response_time, url, headers,
                                     method=method, request_body=body or {})
        test_results = test_executor.execute_all_tests()
        summary = test_executor.get_summary()

        # Display Summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tests", summary.get("total_tests", 0))
        with col2:
            st.metric("Passed", summary.get("passed", 0))
        with col3:
            st.metric("Failed", summary.get("failed", 0))
        with col4:
            st.metric("Success Rate", f"{summary.get('success_rate', 0)}%")

        st.markdown(f"### {summary.get('status', 'N/A')}")

        # Display tests by category
        categories = {}
        for test in test_results:
            category = test.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append(test)

        # Display each category
        for category in ["Functional", "Schema", "Security", "Error"]:
            if category in categories:
                with st.expander(f"🔍 {category} Tests ({len(categories[category])} tests)", expanded=True):
                    for test in categories[category]:
                        severity = test.get("severity", "")
                        severity_badge = ""
                        if severity == "CRITICAL":
                            severity_badge = " 🔴 CRITICAL"
                        elif severity == "HIGH":
                            severity_badge = " 🟠 HIGH"
                        elif severity == "MEDIUM":
                            severity_badge = " 🟡 MEDIUM"

                        if test.get("passed"):
                            st.success(f"✅ {test.get('name')}{severity_badge}: {test.get('message')}")
                        else:
                            st.error(f"❌ {test.get('name')}{severity_badge}: {test.get('message')}")
                            st.write(f"  - Expected: {test.get('expected')}")
                            st.write(f"  - Actual: {test.get('actual')}")

                        # Show details if available
                        if "details" in test and test.get("details"):
                            with st.expander(f"Details for {test.get('name')}"):
                                if isinstance(test.get("details"), list):
                                    for detail in test.get("details", []):
                                        st.write(detail)
                                else:
                                    st.write(test.get("details"))

        # Show failed tests summary
        failed_tests = test_executor.get_failed_tests()
        if failed_tests:
            st.subheader("❌ Failed Test Summary")
            failure_df_data = []
            for failed_test in failed_tests:
                failure_df_data.append({
                    "Test Name": failed_test.get('name'),
                    "Expected": failed_test.get('expected'),
                    "Actual": failed_test.get('actual'),
                    "Category": failed_test.get('category', 'Other')
                })
            if failure_df_data:
                import pandas as pd
                failure_df = pd.DataFrame(failure_df_data)
                st.dataframe(failure_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error executing tests: {str(e)}")

    # ── Custom Post-response Script Results ─────────────────────────────────
    st.subheader("🧪 Post-response Script Results")
    custom_script_results = []
    try:
        executor = CustomScriptExecutor(response_data, status_code, response_time, headers,
                                        method=method, url=url, request_body=body or {})
        scripts_to_run = st.session_state.get("custom_scripts", CustomScriptExecutor.DEFAULT_SCRIPTS)
        custom_script_results = executor.execute_scripts(scripts_to_run)
        csr_summary = executor.get_summary(custom_script_results)

        # Summary metrics
        cs_col1, cs_col2, cs_col3, cs_col4 = st.columns(4)
        with cs_col1:
            st.metric("Total Scripts", csr_summary["total"])
        with cs_col2:
            st.metric("Passed", csr_summary["passed"])
        with cs_col3:
            st.metric("Failed", csr_summary["failed"])
        with cs_col4:
            st.metric("Skipped", csr_summary["skipped"])

        if csr_summary["total"] > 0:
            rate = csr_summary["success_rate"]
            bar_color = "green" if rate == 100 else ("orange" if rate >= 50 else "red")
            st.progress(int(rate) / 100, text=f"Pass Rate: {rate}%")

        # Individual results
        default_results = [r for r in custom_script_results if not r.get("skipped") and
                           any(r["name"] == s["name"] for s in scripts_to_run if s["id"].startswith("default_"))]
        user_results    = [r for r in custom_script_results if r not in default_results]

        with st.expander(f"⚙️ Default Script Results ({len([r for r in default_results if not r.get('skipped')])} ran)", expanded=True):
            for r in custom_script_results:
                if r.get("skipped"):
                    st.info(f"⏭️ {r['name']} — Skipped (disabled)")
                elif r["passed"]:
                    st.success(f"✅ {r['name']}")
                else:
                    st.error(f"❌ **{r['name']}**")
                    col_e, col_a = st.columns(2)
                    with col_e:
                        st.markdown(f"**Expected:** {r.get('expected', 'N/A')}")
                    with col_a:
                        st.markdown(f"**Actual:** {r.get('actual', 'N/A')}")
                    st.markdown(f"**Failure Reason:** `{r.get('failure_reason', 'N/A')}`")

    except Exception as e:
        st.error(f"Error executing custom scripts: {str(e)}")

    # Display JSON Schema
    st.subheader("📊 Auto-Generated JSON Schema")
    try:
        schema_validator = SchemaValidator(response_data)
        schema = schema_validator.generate_schema()
        
        with st.expander("View Generated Schema"):
            st.json(schema)
        
        st.write("This schema was automatically generated from the API response and is used for validation.")
    except Exception as e:
        st.error(f"Error generating schema: {str(e)}")
    st.subheader("📋 Auto-Generated Test Cases")
    try:
        test_case_generator = TestCaseGenerator(url, method, response_data, status_code)
        test_cases = test_case_generator.generate_test_cases()

        for tc in test_cases:
            with st.expander(f"{tc['id']}: {tc['name']}"):
                st.write(f"**Description:** {tc['description']}")
                st.write(f"**Steps:**")
                for i, step in enumerate(tc['steps'], 1):
                    st.write(f"{i}. {step}")
                st.write(f"**Expected Result:** {tc['expected_result']}")

    except Exception as e:
        st.error(f"Error generating test cases: {str(e)}")

    # Generate Excel Report
    st.subheader("📊 Export Test Report")
    try:
        # Prepare execution details
        execution_details = {
            "url": url,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
        }

        # Generate Excel report
        excel_generator = ExcelReportGenerator(test_results, test_cases, execution_details, custom_script_results)
        excel_filename = excel_generator.generate_report()

        # Read the file for download
        with open(excel_filename, "rb") as f:
            excel_data = f.read()

        # Provide download button
        st.download_button(
            label="📥 Download Excel Report",
            data=excel_data,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel"
        )

        st.success(f"✅ Excel report generated: {excel_filename}")

    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")

    save_report({
        "url": url,
        "method": method,
        "status": result.get("status_code"),
        "time": result.get("response_time"),
        "summary": summary if 'summary' in locals() else None,
        "test_passed": summary.get("passed", 0) if 'summary' in locals() else 0,
        "test_failed": summary.get("failed", 0) if 'summary' in locals() else 0,
    })

    st.success("✅ Report Saved")
