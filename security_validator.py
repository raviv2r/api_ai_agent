import re
import json
from typing import Dict, Any, List
from urllib.parse import urlparse


class SecurityValidator:
    """Comprehensive security validation for API responses including penetration testing checks"""

    def __init__(self, url: str, method: str, response_data: Any, status_code: int, 
                 headers: Dict[str, str], request_body: Dict[str, Any] = None):
        self.url = url
        self.method = method.upper()
        self.response_data = response_data
        self.status_code = status_code
        self.headers = headers
        self.request_body = request_body or {}
        self.validations = []

    def validate_security(self) -> List[Dict[str, Any]]:
        """Execute all security validations"""
        self.validations = []

        # 1. HTTPS/SSL Validation
        self._test_https_usage()
        
        # 2. Authentication Testing
        self._test_authentication()
        
        # 3. Authorization Testing
        self._test_authorization()
        
        # 4. JWT/Token Validation
        self._test_jwt_token_validation()
        
        # 5. SQL Injection Testing
        self._test_sql_injection()
        
        # 6. Cross-Site Scripting (XSS)
        self._test_xss_vulnerability()
        
        # 7. Command Injection
        self._test_command_injection()
        
        # 8. Sensitive Data Exposure
        self._test_sensitive_data_exposure()
        
        # 9. Security Headers Validation
        self._test_security_headers()

        # 10. Rate Limiting / Brute Force Protection
        self._test_rate_limiting()
        
        # 11. Input Validation
        self._test_input_validation()
        
        # 12. Parameter Tampering
        self._test_parameter_tampering()
        
        # 13. IDOR (Insecure Direct Object Reference)
        self._test_idor()
        
        # 14. CSRF Validation
        self._test_csrf()
        
        # 15. API Misconfiguration Checks
        self._test_api_misconfiguration()
        
        # 16. File Upload Security
        self._test_file_upload_security()

        return self.validations

    # ─────────────────────────────────────────────────────────────────────
    # Helper
    # ─────────────────────────────────────────────────────────────────────
    def _add(self, name: str, description: str, passed: bool,
             expected: str, actual: str, message: str,
             severity: str, category: str = "Security",
             details: List[str] = None):
        self.validations.append({
            "name": name,
            "description": description,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": message,
            "severity": severity,
            "category": category,
            "details": details or [],
        })

    def _response_str(self) -> str:
        return json.dumps(self.response_data) if isinstance(self.response_data, (dict, list)) else str(self.response_data)

    def _response_headers_lower(self) -> Dict[str, str]:
        return {k.lower(): v for k, v in self.headers.items()}


    # ─────────────────────────────────────────────────────────────────────
    # 1. HTTPS / SSL Validation
    # ─────────────────────────────────────────────────────────────────────
    def _test_https_usage(self):
        is_https = self.url.startswith("https://")
        hsts = "strict-transport-security" in self._response_headers_lower()
        details = []
        if not is_https:
            details.append("API is using HTTP — all traffic is unencrypted and vulnerable to MITM attacks")
        if not hsts:
            details.append("HSTS header (Strict-Transport-Security) is missing — browsers may allow HTTP downgrade")

        self._add(
            name="HTTPS / SSL Validation",
            description="Verify API enforces HTTPS and HSTS headers",
            passed=is_https,
            expected="HTTPS protocol + HSTS header",
            actual=f"{'HTTPS' if is_https else 'HTTP'} | HSTS: {'Present' if hsts else 'Missing'}",
            message="✅ API uses HTTPS" if is_https else "❌ API uses plain HTTP — data in transit is NOT encrypted",
            severity="CRITICAL" if not is_https else ("MEDIUM" if not hsts else "INFO"),
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 2. Authentication Testing
    # ─────────────────────────────────────────────────────────────────────
    def _test_authentication(self):
        h = self._response_headers_lower()
        auth_header_present = "authorization" in h
        # Check if unauthenticated request returned 401
        unauth_protected = self.status_code in (401, 403)
        no_auth_and_success = not auth_header_present and self.status_code == 200
        details = []
        if no_auth_and_success:
            details.append("API returned 200 without any Authorization header — endpoint may be publicly accessible without credentials")
        if auth_header_present:
            details.append(f"Authorization header is present: {h.get('authorization','')[:30]}...")

        passed = auth_header_present or unauth_protected
        self._add(
            name="Authentication Header Check",
            description="Verify authentication credentials are required",
            passed=passed,
            expected="Authorization header present OR 401/403 returned for no-auth requests",
            actual=f"Auth header: {'Present' if auth_header_present else 'Missing'} | Status: {self.status_code}",
            message="✅ Authentication enforced" if passed else "❌ Endpoint accessible without authentication",
            severity="HIGH" if not passed else "INFO",
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 3. Authorization Testing
    # ─────────────────────────────────────────────────────────────────────
    def _test_authorization(self):
        response_str = self._response_str().lower()
        # Look for privilege escalation hints in response
        privilege_leak_patterns = [r"admin", r"superuser", r"role.*admin", r"is_admin.*true"]
        leaks = [p for p in privilege_leak_patterns if re.search(p, response_str)]
        proper_forbidden = self.status_code == 403
        details = []
        if leaks:
            details.append(f"Response contains privilege-related fields: {leaks} — verify these are properly access-controlled")
        if proper_forbidden:
            details.append("Server returned 403 Forbidden — authorization correctly rejected the request")

        passed = len(leaks) == 0
        self._add(
            name="Authorization / Privilege Check",
            description="Detect privilege escalation hints or unrestricted admin access in the response",
            passed=passed,
            expected="No admin/privilege fields exposed without proper authorization",
            actual=f"Privilege leaks: {leaks if leaks else 'None'} | Status: {self.status_code}",
            message="✅ No privilege escalation indicators found" if passed else f"❌ Potential privilege escalation: {leaks}",
            severity="HIGH" if not passed else "INFO",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 4. JWT / Token Validation
    # ─────────────────────────────────────────────────────────────────────
    def _test_jwt_token_validation(self):
        h = self._response_headers_lower()
        auth_value = h.get("authorization", "")
        details = []
        jwt_present = False
        jwt_issues = []

        if auth_value.lower().startswith("bearer "):
            token = auth_value.split(" ", 1)[1]
            parts = token.split(".")
            jwt_present = True
            if len(parts) == 3:
                details.append("JWT has correct 3-part structure (header.payload.signature)")
                # Check for algorithm in header
                try:
                    import base64
                    header_decoded = base64.urlsafe_b64decode(parts[0] + "==").decode()
                    if '"alg":"none"' in header_decoded or '"alg": "none"' in header_decoded:
                        jwt_issues.append("CRITICAL: JWT uses 'none' algorithm — signature bypassed!")
                    if '"alg":"HS256"' not in header_decoded and '"alg":"RS256"' not in header_decoded:
                        details.append(f"JWT header: {header_decoded[:80]}")
                except Exception:
                    details.append("Could not decode JWT header for algorithm check")
            else:
                jwt_issues.append(f"JWT does not have 3 parts — may be malformed (found {len(parts)} parts)")

        passed = jwt_present and len(jwt_issues) == 0
        not_applicable = not jwt_present

        self._add(
            name="JWT / Token Validation",
            description="Validate JWT structure, algorithm, and token format",
            passed=passed or not_applicable,
            expected="Valid 3-part JWT with secure algorithm (HS256/RS256) | Or no token used",
            actual=f"{'JWT present — ' + ('Valid' if not jwt_issues else 'Issues: ' + str(jwt_issues)) if jwt_present else 'No Bearer JWT token found'}",
            message="✅ JWT structure is valid" if (passed or not_applicable) else f"❌ JWT issues: {jwt_issues}",
            severity="CRITICAL" if jwt_issues else "INFO",
            details=details + jwt_issues,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 5. SQL Injection Testing
    # ─────────────────────────────────────────────────────────────────────
    def _test_sql_injection(self):
        response_str = self._response_str()
        
        # SQL error patterns that suggest injection vulnerability
        sql_error_patterns = [
            r"you have an error in your sql syntax",
            r"warning.*mysql",
            r"unclosed quotation mark after the character string",
            r"quoted string not properly terminated",
            r"ORA-\d{5}",          # Oracle errors
            r"PG::SyntaxError",    # PostgreSQL errors
            r"Microsoft OLE DB Provider for SQL Server",
            r"SQLiteException",
            r"sqlite3\.OperationalError",
            r"syntax error at or near",
            r"unterminated quoted string",
            r"SQLSTATE\[",
        ]
        
        found_errors = [p for p in sql_error_patterns if re.search(p, response_str, re.IGNORECASE)]
        
        # Check if URL or body contains SQLi payloads (reflection test)
        sqli_payloads = ["' OR '1'='1", "' OR 1=1--", "'; DROP TABLE", "UNION SELECT", "1' AND SLEEP"]
        url_params = self.url.lower()
        body_str = json.dumps(self.request_body).lower()
        reflected = [p for p in sqli_payloads if p.lower() in response_str.lower()]
        
        details = []
        if found_errors:
            details.append(f"SQL error messages found in response: {found_errors}")
            details.append("This indicates database errors are leaking — likely vulnerable to SQL Injection")
        if reflected:
            details.append(f"SQLi payload reflected in response: {reflected}")
        if not found_errors and not reflected:
            details.append("No SQL error signatures or payload reflections detected in response body")

        passed = len(found_errors) == 0 and len(reflected) == 0
        self._add(
            name="SQL Injection Detection",
            description="Detect SQL error messages or payload reflections in API response",
            passed=passed,
            expected="No SQL error messages or payload reflections in response",
            actual=f"SQL errors: {len(found_errors)} | Reflected payloads: {len(reflected)}",
            message="✅ No SQL injection indicators found" if passed else "❌ SQL Injection vulnerability detected!",
            severity="CRITICAL" if not passed else "INFO",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 6. Cross-Site Scripting (XSS)
    # ─────────────────────────────────────────────────────────────────────
    def _test_xss_vulnerability(self):
        response_str = self._response_str()
        h = self._response_headers_lower()
        
        # XSS payload patterns reflected in response
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"onerror\s*=",
            r"onload\s*=",
            r"eval\s*\(",
            r"document\.cookie",
            r"<img[^>]+src[^>]*onerror",
            r"alert\s*\(",
        ]
        reflected_xss = [p for p in xss_patterns if re.search(p, response_str, re.IGNORECASE)]
        
        # Check for protective headers
        csp = h.get("content-security-policy", "")
        x_content_type = h.get("x-content-type-options", "")
        
        details = []
        if reflected_xss:
            details.append(f"XSS payload patterns found in response: {reflected_xss}")
        if not csp:
            details.append("Content-Security-Policy header is missing — XSS attack surface is larger")
        else:
            details.append(f"CSP header present: {csp[:80]}")
        if x_content_type.lower() == "nosniff":
            details.append("X-Content-Type-Options: nosniff is set ✅")
        else:
            details.append("X-Content-Type-Options header missing or not set to 'nosniff'")

        passed = len(reflected_xss) == 0
        self._add(
            name="Cross-Site Scripting (XSS) Detection",
            description="Detect reflected XSS payloads and check protective headers",
            passed=passed,
            expected="No XSS payload reflections in response + CSP header present",
            actual=f"XSS patterns: {len(reflected_xss)} | CSP: {'Present' if csp else 'Missing'}",
            message="✅ No XSS payload reflections found" if passed else "❌ Reflected XSS vulnerability detected!",
            severity="CRITICAL" if reflected_xss else ("MEDIUM" if not csp else "INFO"),
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 7. Command Injection
    # ─────────────────────────────────────────────────────────────────────
    def _test_command_injection(self):
        response_str = self._response_str()
        
        # OS error patterns that indicate command injection
        cmd_error_patterns = [
            r"sh: .* not found",
            r"bash: .*: command not found",
            r"Permission denied",
            r"/bin/sh",
            r"cmd\.exe",
            r"Windows IP Configuration",
            r"uid=\d+\(.*\) gid=",       # Unix id command output
            r"root:.*:0:0",              # /etc/passwd leakage
            r"Directory of C:\\",
            r"Volume Serial Number",
        ]
        found = [p for p in cmd_error_patterns if re.search(p, response_str, re.IGNORECASE)]
        
        details = []
        if found:
            details.append(f"Command execution output patterns found: {found}")
            details.append("The server may be executing OS commands and leaking output — likely vulnerable to Command Injection")
        else:
            details.append("No OS command output signatures detected in response")

        passed = len(found) == 0
        self._add(
            name="Command Injection Detection",
            description="Detect OS command execution output in API response",
            passed=passed,
            expected="No OS command output in response",
            actual=f"Command patterns found: {len(found)}",
            message="✅ No command injection indicators" if passed else "❌ Possible command injection vulnerability!",
            severity="CRITICAL" if not passed else "INFO",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 8. Sensitive Data Exposure
    # ─────────────────────────────────────────────────────────────────────
    def _test_sensitive_data_exposure(self):
        response_str = self._response_str()
        
        patterns = {
            "Password field":        re.compile(r'"password"\s*:\s*"[^"]+"', re.IGNORECASE),
            "Private/Secret key":    re.compile(r'"(secret|private_key|api_key|apikey|client_secret)"\s*:\s*"[^"]+"', re.IGNORECASE),
            "Credit card number":    re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'),
            "SSN":                   re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "AWS Access Key":        re.compile(r'AKIA[0-9A-Z]{16}'),
            "Private RSA key":       re.compile(r'-----BEGIN RSA PRIVATE KEY-----'),
            "JWT in response body":  re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
            "Email addresses":       re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }
        
        found = {name: bool(pattern.search(response_str)) for name, pattern in patterns.items()}
        exposed = [name for name, hit in found.items() if hit]
        
        # Strict fields (always a fail)
        critical_fields = {"Password field", "Private/Secret key", "Credit card number", "SSN", "AWS Access Key", "Private RSA key"}
        critical_exposed = [f for f in exposed if f in critical_fields]
        
        details = [f"⚠️ {f} found in response" for f in exposed]
        if not exposed:
            details.append("No sensitive data patterns detected in the response body")

        passed = len(critical_exposed) == 0
        self._add(
            name="Sensitive Data Exposure",
            description="Detect passwords, keys, PII, and credentials in API response",
            passed=passed,
            expected="No sensitive data (passwords, keys, PII) exposed in response",
            actual=f"Exposed: {', '.join(exposed) if exposed else 'None'}",
            message="✅ No critical sensitive data found" if passed else f"❌ Sensitive data exposed: {critical_exposed}",
            severity="CRITICAL" if critical_exposed else ("MEDIUM" if exposed else "INFO"),
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 9. Security Headers Validation
    # ─────────────────────────────────────────────────────────────────────
    def _test_security_headers(self):
        h = self._response_headers_lower()
        
        required_headers = {
            "Content-Security-Policy":    "Prevents XSS and data injection attacks",
            "X-Content-Type-Options":     "Prevents MIME-type sniffing (must be 'nosniff')",
            "X-Frame-Options":            "Prevents clickjacking (DENY or SAMEORIGIN)",
            "Strict-Transport-Security":  "Enforces HTTPS connections (HSTS)",
            "X-XSS-Protection":           "Enables XSS filter in older browsers",
            "Referrer-Policy":            "Controls referrer information leakage",
            "Permissions-Policy":         "Controls browser features access",
        }
        
        present = [h_name for h_name in required_headers if h_name.lower() in h]
        missing = [h_name for h_name in required_headers if h_name.lower() not in h]
        
        details = [f"✅ {h_name}" for h_name in present] + [f"❌ Missing: {h_name} — {desc}" for h_name, desc in required_headers.items() if h_name in missing]

        passed = len(missing) == 0
        self._add(
            name="Security Headers Validation",
            description="Verify all 7 critical security response headers are present",
            passed=passed,
            expected=f"All {len(required_headers)} security headers present",
            actual=f"{len(present)}/{len(required_headers)} headers present",
            message=f"✅ All security headers present" if passed else f"❌ {len(missing)} security headers missing",
            severity="HIGH" if len(missing) >= 4 else ("MEDIUM" if missing else "INFO"),
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 10. Rate Limiting / Brute Force Protection
    # ─────────────────────────────────────────────────────────────────────
    def _test_rate_limiting(self):
        h = self._response_headers_lower()
        
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "retry-after",
            "ratelimit-limit",
            "ratelimit-remaining",
        ]
        
        found_rl = [rh for rh in rate_limit_headers if rh in h]
        is_rate_limited = self.status_code == 429
        
        details = []
        if found_rl:
            details += [f"Rate limit header found: {rh}: {h[rh]}" for rh in found_rl]
        if is_rate_limited:
            details.append("HTTP 429 Too Many Requests — rate limiting is actively enforced ✅")
        if not found_rl and not is_rate_limited:
            details.append("No rate limit headers detected — API may allow unlimited requests (brute force risk)")

        passed = len(found_rl) > 0 or is_rate_limited
        self._add(
            name="Rate Limiting / Brute Force Protection",
            description="Verify API enforces rate limiting via headers or HTTP 429",
            passed=passed,
            expected="Rate-Limit headers or HTTP 429 response",
            actual=f"Headers: {found_rl if found_rl else 'None'} | Status: {self.status_code}",
            message="✅ Rate limiting headers detected" if passed else "❌ No rate limiting detected — brute force attacks possible",
            severity="HIGH" if not passed else "INFO",
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 11. Input Validation
    # ─────────────────────────────────────────────────────────────────────
    def _test_input_validation(self):
        response_str = self._response_str()
        
        # Signs of good input validation: 400/422 with validation message
        validation_error_codes = {400, 422}
        has_validation_error = self.status_code in validation_error_codes
        
        # Stack trace / raw exception leakage (bad)
        stack_trace_patterns = [
            r"Traceback \(most recent call last\)",
            r"at com\.[a-z]+\.[A-Z]",        # Java stack trace
            r"System\.NullReferenceException",
            r"Exception in thread",
            r"NullPointerException",
            r"RuntimeException",
        ]
        leaking_stack = [p for p in stack_trace_patterns if re.search(p, response_str)]
        
        details = []
        if leaking_stack:
            details.append(f"Stack trace / exception details found in response: {leaking_stack}")
            details.append("Exposing stack traces reveals internal architecture — attackers can use this to craft targeted attacks")
        if has_validation_error:
            details.append(f"HTTP {self.status_code} returned — server validates input correctly")
        if not leaking_stack and not has_validation_error:
            details.append("No stack traces detected. Input validation behavior could not be fully assessed from response alone.")

        passed = len(leaking_stack) == 0
        self._add(
            name="Input Validation & Error Handling",
            description="Verify API does not leak stack traces or internal exception details",
            passed=passed,
            expected="No stack traces or exception details in response",
            actual=f"Stack traces: {'Found' if leaking_stack else 'None'} | Status: {self.status_code}",
            message="✅ No stack traces or exception leakage" if passed else "❌ Stack trace / exception details leaked in response",
            severity="HIGH" if leaking_stack else "INFO",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 12. Parameter Tampering
    # ─────────────────────────────────────────────────────────────────────
    def _test_parameter_tampering(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.url)
        params = parse_qs(parsed.query)
        
        # Look for numeric ID params that could be tampered
        tamperable_params = [k for k in params if re.search(r'(id|user_id|account|order|invoice|record)', k, re.IGNORECASE)]
        
        # Check if response contains other users' data (simple heuristic: array of objects with IDs)
        response_str = self._response_str().lower()
        multiple_ids = len(re.findall(r'"id"\s*:', response_str)) > 5
        
        details = []
        if tamperable_params:
            details.append(f"URL contains ID-like parameters: {tamperable_params} — test with different ID values to check for IDOR/parameter tampering")
        if multiple_ids:
            details.append("Response contains many 'id' fields — verify each record is scoped to the authenticated user")
        if not tamperable_params:
            details.append("No obvious tamperable ID parameters found in URL query string")

        # Pass if no tamperable params (can't test) or if proper auth status returned
        passed = len(tamperable_params) == 0 or self.status_code in (401, 403)
        self._add(
            name="Parameter Tampering Check",
            description="Detect ID-like URL parameters that may be subject to tampering attacks",
            passed=passed,
            expected="No exposed ID parameters OR proper 401/403 enforcement",
            actual=f"Tamperable params: {tamperable_params if tamperable_params else 'None'}",
            message="✅ No parameter tampering risk detected" if passed else f"⚠️ Tamperable parameters found: {tamperable_params} — manual verification recommended",
            severity="MEDIUM" if (tamperable_params and not passed) else "INFO",
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 13. IDOR (Insecure Direct Object Reference)
    # ─────────────────────────────────────────────────────────────────────
    def _test_idor(self):
        parsed = urlparse(self.url)
        path_parts = [p for p in parsed.path.split("/") if p]
        
        # Check for numeric or UUID segments in path (classic IDOR targets)
        idor_segments = [p for p in path_parts if re.match(r'^\d+$', p) or 
                         re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', p, re.IGNORECASE)]
        
        # Check response returned data without 401/403
        data_returned = bool(self.response_data) and self.status_code == 200
        
        details = []
        if idor_segments:
            details.append(f"Path contains direct object references: {idor_segments}")
            details.append("Manually test by modifying these IDs to see if you can access other users' data")
        if data_returned and idor_segments:
            details.append("API returned data (200) for a direct object reference — verify ownership check exists server-side")
        if not idor_segments:
            details.append("No direct numeric/UUID references found in URL path")

        # Flag as warning if IDOR segments exist and returns data
        passed = not (idor_segments and data_returned and "authorization" not in {k.lower() for k in self.headers})
        self._add(
            name="IDOR (Insecure Direct Object Reference)",
            description="Detect direct object references in URL path without enforced ownership checks",
            passed=passed,
            expected="Object references require proper ownership/access validation",
            actual=f"Path IDs: {idor_segments if idor_segments else 'None'} | Auth: {'Present' if 'authorization' in {k.lower() for k in self.headers} else 'Missing'} | Status: {self.status_code}",
            message="✅ No IDOR risk detected" if passed else "⚠️ Potential IDOR — unauthenticated access to object references",
            severity="HIGH" if not passed else "INFO",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 14. CSRF Validation
    # ─────────────────────────────────────────────────────────────────────
    def _test_csrf(self):
        h = self._response_headers_lower()
        
        # CSRF only applies to state-changing methods
        if self.method not in ("POST", "PUT", "PATCH", "DELETE"):
            self._add(
                name="CSRF Validation",
                description="Check CSRF protection for state-changing requests",
                passed=True,
                expected="N/A for GET requests",
                actual=f"Method is {self.method} — CSRF not applicable",
                message=f"✅ CSRF check skipped — {self.method} is not state-changing",
                severity="INFO",
                details=[f"CSRF protection is only relevant for {self.method} if it's a browser-based flow"],
            )
            return
        
        # Check for CSRF tokens or SameSite cookie
        csrf_indicators = [k for k in h if "csrf" in k or "xsrf" in k]
        set_cookie = h.get("set-cookie", "")
        samesite_set = "samesite=strict" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()
        cors_origin = h.get("access-control-allow-origin", "")
        wildcard_cors = cors_origin == "*"
        
        details = []
        if csrf_indicators:
            details.append(f"CSRF token headers found: {csrf_indicators}")
        if samesite_set:
            details.append(f"SameSite cookie attribute is set ✅ — provides CSRF protection")
        if wildcard_cors:
            details.append("CRITICAL: Access-Control-Allow-Origin: * — any origin can make cross-site requests!")
        if not csrf_indicators and not samesite_set:
            details.append("No CSRF tokens or SameSite cookie detected — may be vulnerable if used in a browser context")

        passed = (len(csrf_indicators) > 0 or samesite_set) and not wildcard_cors
        self._add(
            name="CSRF Validation",
            description="Verify CSRF protection via tokens, SameSite cookies, or CORS policy",
            passed=passed,
            expected="CSRF token or SameSite cookie + no wildcard CORS",
            actual=f"CSRF headers: {csrf_indicators if csrf_indicators else 'None'} | SameSite: {'Yes' if samesite_set else 'No'} | CORS: {cors_origin or 'Not set'}",
            message="✅ CSRF protections in place" if passed else "❌ No CSRF protection detected for state-changing endpoint",
            severity="HIGH" if not passed else "INFO",
            details=details,
        )


    # ─────────────────────────────────────────────────────────────────────
    # 15. API Misconfiguration Checks
    # ─────────────────────────────────────────────────────────────────────
    def _test_api_misconfiguration(self):
        h = self._response_headers_lower()
        response_str = self._response_str()
        issues = []
        details = []
        
        # a) Server version disclosure
        server_header = h.get("server", "")
        x_powered_by = h.get("x-powered-by", "")
        if re.search(r'[\d.]+', server_header):
            issues.append(f"Server version disclosed: {server_header}")
            details.append(f"❌ Server header reveals version: '{server_header}' — attackers can exploit known CVEs")
        if x_powered_by:
            issues.append(f"X-Powered-By header exposes technology: {x_powered_by}")
            details.append(f"❌ X-Powered-By: '{x_powered_by}' — reveals backend technology stack")
        
        # b) Debug mode / verbose errors
        debug_patterns = [r'"debug"\s*:\s*true', r'"trace"\s*:', r'"stacktrace"\s*:']
        for p in debug_patterns:
            if re.search(p, response_str, re.IGNORECASE):
                issues.append("Debug/trace information in response")
                details.append(f"❌ Debug data pattern found: {p}")
        
        # c) Wildcard CORS
        cors = h.get("access-control-allow-origin", "")
        if cors == "*":
            issues.append("Wildcard CORS (Access-Control-Allow-Origin: *)")
            details.append("❌ CORS wildcard allows ANY origin to make requests to this API")
        
        # d) Directory listing / internal paths
        internal_path_patterns = [r'/etc/passwd', r'C:\\Windows', r'app\.py', r'config\.json', r'\.env']
        for p in internal_path_patterns:
            if re.search(p, response_str, re.IGNORECASE):
                issues.append(f"Internal path exposed: {p}")
                details.append(f"❌ Internal path reference found in response: {p}")
        
        if not issues:
            details.append("✅ No server version disclosure, debug data, wildcard CORS, or internal paths detected")

        passed = len(issues) == 0
        self._add(
            name="API Misconfiguration Check",
            description="Detect server version disclosure, debug mode, wildcard CORS, and internal path leaks",
            passed=passed,
            expected="No server version, debug info, wildcard CORS, or internal paths exposed",
            actual=f"Issues found: {len(issues)}",
            message="✅ No misconfigurations detected" if passed else f"❌ {len(issues)} misconfiguration(s) found",
            severity="HIGH" if issues else "INFO",
            details=details + issues,
        )

    # ─────────────────────────────────────────────────────────────────────
    # 16. File Upload Security
    # ─────────────────────────────────────────────────────────────────────
    def _test_file_upload_security(self):
        h = self._response_headers_lower()
        response_str = self._response_str()
        content_type_req = h.get("content-type", "")
        
        # Determine if this looks like a file upload endpoint
        upload_indicators = [
            "upload" in self.url.lower(),
            "file" in self.url.lower(),
            "multipart/form-data" in content_type_req.lower(),
            "attachment" in response_str.lower(),
        ]
        is_upload_endpoint = any(upload_indicators)
        
        if not is_upload_endpoint:
            self._add(
                name="File Upload Security",
                description="Verify file upload endpoints enforce type and size restrictions",
                passed=True,
                expected="N/A — endpoint does not appear to be a file upload",
                actual="Not a file upload endpoint",
                message="✅ File upload check skipped — not applicable to this endpoint",
                severity="INFO",
                details=["No file upload indicators found in URL or headers"],
            )
            return
        
        issues = []
        details = []
        
        # Check for file type validation response (bad types should return 400/415)
        if self.status_code == 415:
            details.append("✅ HTTP 415 Unsupported Media Type — file type validation is enforced")
        
        # Check for dangerous file patterns in response (e.g., path traversal)
        dangerous_patterns = [r'\.\./', r'\.\.\\', r'/etc/', r'C:\\', r'\.php', r'\.exe', r'\.sh']
        for p in dangerous_patterns:
            if re.search(p, response_str, re.IGNORECASE):
                issues.append(f"Dangerous file path pattern in response: {p}")
                details.append(f"❌ Dangerous pattern '{p}' found — possible path traversal or executable upload")
        
        # Check content-disposition
        content_disp = h.get("content-disposition", "")
        if "attachment" in content_disp:
            details.append("✅ Content-Disposition: attachment set — prevents inline execution of uploaded files")
        else:
            issues.append("Content-Disposition: attachment missing — uploaded files may execute inline")
            details.append("❌ Content-Disposition header not set to 'attachment' — browser may execute uploaded content")
        
        if not issues:
            details.append("✅ No dangerous file upload patterns detected")

        passed = len(issues) == 0
        self._add(
            name="File Upload Security",
            description="Verify file upload endpoint enforces type restrictions and prevents path traversal",
            passed=passed,
            expected="Proper file type validation + Content-Disposition: attachment",
            actual=f"Issues: {len(issues)}",
            message="✅ File upload security checks passed" if passed else f"❌ File upload security issues: {issues}",
            severity="HIGH" if issues else "INFO",
            details=details,
        )
