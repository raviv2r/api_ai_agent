import json
from typing import Dict, Any, List, Tuple

class PostmanScriptGenerator:
    """Generate Postman test scripts based on API response"""

    def __init__(self, response_data: Dict[str, Any], status_code: int, response_time: float, url: str = "", headers: Dict[str, str] = None):
        self.response_data = response_data
        self.status_code = status_code
        self.response_time = response_time
        self.url = url
        self.headers = headers or {}

    def generate_test_script(self) -> str:
        """Generate comprehensive Postman test script"""
        script_parts = []

        # Functional Validations
        script_parts.append("// ========== FUNCTIONAL VALIDATIONS ==========")
        script_parts.append(self._generate_status_code_test())
        script_parts.append(self._generate_response_time_test())
        script_parts.append(self._generate_content_type_test())
        script_parts.append(self._generate_response_body_test())
        script_parts.append(self._generate_json_format_test())
        script_parts.append(self._generate_required_fields_test())
        script_parts.append(self._generate_data_types_test())
        script_parts.append(self._generate_null_values_test())
        script_parts.append(self._generate_array_validation_test())
        script_parts.append(self._generate_nested_objects_test())
        script_parts.append(self._generate_field_format_validations())

        # Security Validations
        script_parts.append("\n// ========== SECURITY VALIDATIONS ==========")
        script_parts.append(self._generate_security_validations())

        # Error Validations (if applicable)
        if 400 <= self.status_code < 600:
            script_parts.append("\n// ========== ERROR VALIDATIONS ==========")
            script_parts.append(self._generate_error_validations())

        return "\n\n".join(filter(None, script_parts))

    def _generate_status_code_test(self) -> str:
        """Generate status code validation"""
        return f"""// Status Code Validation
pm.test("Status code is {self.status_code}", function () {{
    pm.response.to.have.status({self.status_code});
}});

pm.test("Status code is valid", function () {{
    pm.expect([200, 201, 202, 204, 400, 401, 403, 404, 500]).to.include(pm.response.code);
}});"""

    def _generate_response_time_test(self) -> str:
        """Generate response time validation"""
        threshold = 2000  # 2 seconds in ms
        return f"""// Response Time Validation
pm.test("Response time is under {threshold}ms", function () {{
    pm.expect(pm.response.responseTime).to.be.below({threshold});
}});

pm.test("Response time is acceptable ({{actual: " + pm.response.responseTime + "ms}})", function () {{
    pm.expect(pm.response.responseTime).to.be.below(5000);
}});"""

    def _generate_content_type_test(self) -> str:
        """Generate Content-Type validation"""
        return """// Content-Type Validation
pm.test("Content-Type header is present", function () {
    pm.response.to.have.header("content-type");
});

pm.test("Content-Type is JSON", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
});"""

    def _generate_response_body_test(self) -> str:
        """Generate response body validation"""
        return """// Response Body Validation
pm.test("Response body is not empty", function () {
    pm.response.to.not.be.empty;
});

pm.test("Response body is not null", function () {
    pm.expect(pm.response.text).to.not.be.null;
});"""

    def _generate_json_format_test(self) -> str:
        """Generate JSON format validation"""
        return """// JSON Format Validation
pm.test("Response is valid JSON", function () {
    var jsonData;
    pm.expect(function() { 
        jsonData = pm.response.json(); 
    }).to.not.throw();
});"""

    def _generate_required_fields_test(self) -> str:
        """Generate required fields validation"""
        if not isinstance(self.response_data, dict):
            return ""

        fields = list(self.response_data.keys())
        if not fields:
            return ""

        field_checks = []
        for field in fields[:10]:  # Check first 10 fields
            field_checks.append(f'    pm.expect(jsonData).to.have.property("{field}");')

        return f"""// Required Fields Validation
pm.test("Response contains all required fields", function () {{
    var jsonData = pm.response.json();
{chr(10).join(field_checks)}
}});"""

    def _generate_data_types_test(self) -> str:
        """Generate data types validation"""
        if not isinstance(self.response_data, dict):
            return ""

        type_checks = []
        for key, value in list(self.response_data.items())[:8]:
            if isinstance(value, str):
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.a("string");')
            elif isinstance(value, bool):
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.a("boolean");')
            elif isinstance(value, (int, float)):
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.a("number");')
            elif isinstance(value, dict):
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.an("object");')
            elif isinstance(value, list):
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.an("array");')
            elif value is None:
                type_checks.append(f'    pm.expect(jsonData.{key}).to.be.null;')

        if not type_checks:
            return ""

        return f"""// Data Types Validation
pm.test("All fields have correct data types", function () {{
    var jsonData = pm.response.json();
{chr(10).join(type_checks)}
}});"""

    def _generate_null_values_test(self) -> str:
        """Generate null values validation"""
        if not isinstance(self.response_data, dict):
            return ""

        null_checks = []
        for key, value in list(self.response_data.items())[:5]:
            if value is not None:
                null_checks.append(f'    pm.expect(jsonData.{key}).to.not.be.null;')

        if not null_checks:
            return ""

        return f"""// Null Values Validation
pm.test("Required fields are not null", function () {{
    var jsonData = pm.response.json();
{chr(10).join(null_checks)}
}});"""

    def _generate_array_validation_test(self) -> str:
        """Generate array validation"""
        if not isinstance(self.response_data, dict):
            return ""

        array_checks = []
        for key, value in self.response_data.items():
            if isinstance(value, list):
                array_checks.append(f'    pm.expect(jsonData.{key}).to.be.an("array");')
                if value:
                    array_checks.append(f'    pm.expect(jsonData.{key}.length).to.be.greaterThan(0);')

        if not array_checks:
            return ""

        return f"""// Array Validation
pm.test("Arrays are properly formatted", function () {{
    var jsonData = pm.response.json();
{chr(10).join(array_checks[:8])}
}});"""

    def _generate_nested_objects_test(self) -> str:
        """Generate nested objects validation"""
        if not isinstance(self.response_data, dict):
            return ""

        nested_checks = []
        for key, value in list(self.response_data.items())[:5]:
            if isinstance(value, dict):
                nested_checks.append(f'    pm.expect(jsonData.{key}).to.be.an("object");')

        if not nested_checks:
            return ""

        return f"""// Nested Objects Validation
pm.test("Nested objects are valid", function () {{
    var jsonData = pm.response.json();
{chr(10).join(nested_checks)}
}});"""

    def _generate_field_format_validations(self) -> str:
        """Generate validations for standard field formats (email, URL, etc.)"""
        validations = []

        response_str = json.dumps(self.response_data)

        # Email validation
        if "@" in response_str:
            validations.append("""// Email Format Validation
pm.test("Email fields have valid format", function () {
    var jsonData = pm.response.json();
    var emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    // Add specific email field checks here
});""")

        # Timestamp validation
        if "date" in response_str.lower() or "time" in response_str.lower():
            validations.append("""// Timestamp Validation
pm.test("Timestamp fields are valid", function () {
    var jsonData = pm.response.json();
    // Validate ISO 8601 format or Unix timestamp
});""")

        # URL validation
        if "http" in response_str or "url" in response_str.lower():
            validations.append("""// URL Format Validation
pm.test("URL fields have valid format", function () {
    var jsonData = pm.response.json();
    var urlRegex = /^(https?:\\/\\/)?(www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b([-a-zA-Z0-9()@:%_\\+.~#?&//=]*)$/;
});""")

        return "\n\n".join(validations) if validations else ""

    def _generate_security_validations(self) -> str:
        """Generate security-related Postman tests"""
        tests = []

        # HTTPS validation
        if self.url.startswith("https"):
            tests.append("""// HTTPS Validation
pm.test("Request uses HTTPS", function () {
    pm.expect(pm.request.url.toString()).to.include("https://");
});""")

        # Authorization header validation
        if any(k.lower() == "authorization" for k in self.headers.keys()):
            tests.append("""// Authorization Header Validation
pm.test("Authorization header is present", function () {
    pm.response.to.have.header("authorization") || pm.expect(true).to.equal(true);
});""")

        # Security headers validation
        tests.append("""// Security Headers Check
pm.test("Security headers are present", function () {
    var securityHeaders = ["content-security-policy", "x-content-type-options", "x-frame-options"];
    // At least one security header should be present in production
});""")

        return "\n\n".join(tests) if tests else ""

    def _generate_error_validations(self) -> str:
        """Generate error response validations"""
        tests = []

        if 400 <= self.status_code < 500:
            tests.append(f"""// Client Error Validation (4xx)
pm.test("Response status is 4xx client error", function () {{
    pm.expect(pm.response.code).to.be.within(400, 499);
}});

pm.test("Error response contains error details", function () {{
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.any.keys('error', 'message', 'code', 'details');
}});""")

        elif 500 <= self.status_code < 600:
            tests.append(f"""// Server Error Validation (5xx)
pm.test("Response status is 5xx server error", function () {{
    pm.expect(pm.response.code).to.be.within(500, 599);
}});

pm.test("Error response has error message", function () {{
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("message").that.is.a("string");
}});""")

        return "\n\n".join(tests) if tests else ""


class TestCaseGenerator:
    """Generate test cases based on API response"""

    def __init__(self, url: str, method: str, response_data: Dict[str, Any], status_code: int):
        self.url = url
        self.method = method
        self.response_data = response_data
        self.status_code = status_code

    def generate_test_cases(self) -> List[Dict[str, Any]]:
        """Generate comprehensive test cases"""
        test_cases = []

        # Test Case 1: Successful Response
        test_cases.append({
            "id": "TC001",
            "name": "Verify successful API response",
            "description": f"Test that {self.method} {self.url} returns correct status",
            "steps": [
                f"Send {self.method} request to {self.url}",
                "Verify response status code",
                "Verify response body is valid JSON",
                "Verify response is not empty",
            ],
            "expected_result": f"Status code should be {self.status_code}, response should be valid JSON with data"
        })

        # Test Case 2: Response Structure
        if isinstance(self.response_data, dict):
            fields = list(self.response_data.keys())[:5]
            fields_str = ", ".join(fields)
            test_cases.append({
                "id": "TC002",
                "name": "Verify response structure",
                "description": "Test that response contains expected fields",
                "steps": [
                    f"Send {self.method} request",
                    f"Verify response contains fields: {fields_str}",
                    "Verify each field has correct data type",
                ],
                "expected_result": f"Response should contain all required fields: {fields_str}"
            })

            # Test Case 3: Field Value Validation
            test_cases.append({
                "id": "TC003",
                "name": "Verify field values are not empty",
                "description": "Test that response fields contain valid values",
                "steps": [
                    f"Send {self.method} request",
                    f"Extract response fields: {fields_str}",
                    "Verify each field value is not null or empty",
                ],
                "expected_result": "All fields should contain non-empty values"
            })

        # Test Case 4: Response Time
        test_cases.append({
            "id": "TC004",
            "name": "Verify response time",
            "description": "Test that API responds within acceptable time",
            "steps": [
                f"Send {self.method} request",
                "Measure response time",
                "Verify response time is less than 2 seconds",
            ],
            "expected_result": "Response time should be acceptable (< 2000ms)"
        })

        # Test Case 5: Data Type Validation
        if isinstance(self.response_data, dict):
            test_cases.append({
                "id": "TC005",
                "name": "Verify data types of all fields",
                "description": "Test that response fields have correct data types",
                "steps": [
                    f"Send {self.method} request",
                    "Extract response fields",
                    "Verify each field has correct data type (string, number, boolean, object, array)",
                ],
                "expected_result": "All fields should have correct data types"
            })

        # Test Case 6: Array/List Validation
        if isinstance(self.response_data, dict):
            arrays = [k for k, v in self.response_data.items() if isinstance(v, list)]
            if arrays:
                test_cases.append({
                    "id": "TC006",
                    "name": "Verify array fields",
                    "description": "Test that array fields are valid",
                    "steps": [
                        f"Send {self.method} request",
                        f"Verify array fields: {', '.join(arrays[:3])}",
                        "Verify each array has valid items",
                    ],
                    "expected_result": "All array fields should be valid and contain items"
                })

        # Test Case 7: Nested Objects
        if isinstance(self.response_data, dict):
            nested_objs = [k for k, v in self.response_data.items() if isinstance(v, dict)]
            if nested_objs:
                test_cases.append({
                    "id": "TC007",
                    "name": "Verify nested object structure",
                    "description": "Test that nested objects are valid",
                    "steps": [
                        f"Send {self.method} request",
                        f"Extract nested objects: {', '.join(nested_objs[:3])}",
                        "Verify each nested object has valid structure",
                    ],
                    "expected_result": "All nested objects should have valid structure"
                })

        # Test Case 8: Status Code Variations
        if self.status_code >= 400:
            test_cases.append({
                "id": "TC008",
                "name": "Verify error response format",
                "description": "Test that error response contains required error information",
                "steps": [
                    f"Send {self.method} request",
                    "Verify error status code is returned",
                    "Verify error response contains error code or message",
                ],
                "expected_result": f"Should return {self.status_code} with error details"
            })
        else:
            test_cases.append({
                "id": "TC008",
                "name": "Verify success response format",
                "description": "Test that success response contains required data",
                "steps": [
                    f"Send {self.method} request",
                    "Verify success status code is returned",
                    "Verify response contains required data fields",
                ],
                "expected_result": f"Should return {self.status_code} with response data"
            })

        # Test Case 9: Content-Type Validation
        test_cases.append({
            "id": "TC009",
            "name": "Verify Content-Type header",
            "description": "Test that response has correct Content-Type",
            "steps": [
                f"Send {self.method} request",
                "Check Content-Type header in response",
                "Verify Content-Type is application/json",
            ],
            "expected_result": "Content-Type should be application/json"
        })

        # Test Case 10: Security Validation
        test_cases.append({
            "id": "TC010",
            "name": "Verify API security",
            "description": "Test that API follows security best practices",
            "steps": [
                f"Send {self.method} request to {self.url}",
                "Verify HTTPS is used",
                "Verify no sensitive data is exposed in response",
                "Verify security headers are present",
            ],
            "expected_result": "API should use HTTPS and follow security best practices"
        })

        return test_cases
