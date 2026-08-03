import json
from typing import Dict, Any, List, Tuple
from schema_validator import SchemaValidator
from security_validator import SecurityValidator
from error_validator import ErrorValidator

class TestExecutor:
    """Execute comprehensive validations against API response"""

    def __init__(self, response_data: Dict[str, Any], status_code: int, response_time: float,
                 url: str = "", headers: Dict[str, str] = None,
                 method: str = "GET", request_body: Dict[str, Any] = None):
        self.response_data = response_data
        self.status_code = status_code
        self.response_time = response_time
        self.url = url
        self.headers = headers or {}
        self.method = method
        self.request_body = request_body or {}
        self.test_results = []

    def execute_all_tests(self) -> List[Dict[str, Any]]:
        """Execute all test categories"""
        self.test_results = []

        # Functional Tests
        self._execute_functional_tests()

        # Schema Validation
        self._execute_schema_validation()

        # Security Tests
        self._execute_security_tests()

        # Error Tests
        self._execute_error_tests()

        return self.test_results

    def _execute_functional_tests(self):
        """Execute functional validations"""
        # Status Code
        self._test_status_code()

        # Response Time
        self._test_response_time()

        # Content Type
        self._test_content_type()

        # Response Body
        self._test_response_body()

        # JSON Format
        self._test_json_format()

        # Required Fields
        self._test_required_fields()

        # Data Types
        self._test_data_types()

        # Null Values
        self._test_null_values()

        # Arrays
        self._test_arrays()

        # Nested Objects
        self._test_nested_objects()

    def _execute_schema_validation(self):
        """Execute JSON schema validation"""
        try:
            schema_validator = SchemaValidator(self.response_data)
            is_valid, errors = schema_validator.validate_schema()

            result = {
                "name": "JSON Schema Validation",
                "description": "Validate response against auto-generated JSON schema",
                "passed": is_valid,
                "expected": "Response should match generated schema",
                "actual": "Valid" if is_valid else f"Invalid - {len(errors)} errors",
                "message": "Response matches schema" if is_valid else f"Schema validation failed with {len(errors)} errors",
                "details": errors[:5] if errors else [],
                "category": "Schema"
            }
            self.test_results.append(result)
        except Exception as e:
            result = {
                "name": "JSON Schema Validation",
                "passed": False,
                "message": f"Schema validation error: {str(e)}",
                "category": "Schema"
            }
            self.test_results.append(result)

    def _execute_security_tests(self):
        """Execute security validations"""
        security_validator = SecurityValidator(
            self.url, self.method, self.response_data,
            self.status_code, self.headers, self.request_body
        )
        security_results = security_validator.validate_security()

        for result in security_results:
            result["category"] = "Security"
            self.test_results.append(result)

    def _execute_error_tests(self):
        """Execute error validations"""
        error_validator = ErrorValidator(self.response_data, self.status_code)
        error_results = error_validator.validate_errors()

        for result in error_results:
            result["category"] = "Error"
            self.test_results.append(result)

    def _test_status_code(self):
        """Status code validation"""
        is_valid_code = isinstance(self.status_code, int) and 100 <= self.status_code < 600
        is_success = 200 <= self.status_code < 300

        result = {
            "name": "HTTP Status Code Valid",
            "description": "Verify HTTP status code is valid",
            "passed": is_valid_code,
            "expected": "Valid HTTP status code (100-599)",
            "actual": str(self.status_code),
            "message": f"Status code {self.status_code} is valid",
            "category": "Functional"
        }
        self.test_results.append(result)

        # Success status validation
        if self.status_code >= 400:
            result = {
                "name": "Error Response Status",
                "description": f"Verify error status code {self.status_code}",
                "passed": True,
                "expected": f"HTTP {self.status_code}",
                "actual": f"HTTP {self.status_code}",
                "message": f"Error response received: {self.status_code}",
                "category": "Functional"
            }
        else:
            result = {
                "name": "Success Response Status",
                "description": f"Verify success status code {self.status_code}",
                "passed": is_success,
                "expected": "2xx Status Code",
                "actual": f"{self.status_code}",
                "message": f"Success response: {self.status_code}" if is_success else f"Unexpected status: {self.status_code}",
                "category": "Functional"
            }
        self.test_results.append(result)

    def _test_response_time(self):
        """Response time validation"""
        threshold = 2.0  # 2 seconds
        is_acceptable = self.response_time <= threshold

        result = {
            "name": "Response Time Performance",
            "description": f"Verify response time under {threshold}s",
            "passed": is_acceptable,
            "expected": f"< {threshold}s",
            "actual": f"{self.response_time}s",
            "message": f"Response time: {self.response_time}s" if is_acceptable else f"Slow response: {self.response_time}s (exceeds {threshold}s)",
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_content_type(self):
        """Content type validation"""
        headers_lower = {k.lower(): v for k, v in self.headers.items()}
        content_type = headers_lower.get("content-type", "")
        is_json = "application/json" in content_type.lower()

        result = {
            "name": "Content-Type Header",
            "description": "Verify Content-Type is application/json",
            "passed": is_json,
            "expected": "application/json",
            "actual": content_type if content_type else "Not set",
            "message": "Content-Type is JSON" if is_json else "Content-Type is not JSON",
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_response_body(self):
        """Response body validation"""
        is_not_empty = bool(self.response_data)

        result = {
            "name": "Response Body Not Empty",
            "description": "Verify response body contains data",
            "passed": is_not_empty,
            "expected": "Non-empty response",
            "actual": "Empty" if not is_not_empty else f"Contains {len(str(self.response_data))} characters",
            "message": "Response body contains data" if is_not_empty else "Response body is empty",
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_json_format(self):
        """JSON format validation"""
        try:
            if isinstance(self.response_data, dict):
                json_str = json.dumps(self.response_data)
                json.loads(json_str)
                is_valid = True
            else:
                is_valid = False
        except:
            is_valid = False

        result = {
            "name": "Valid JSON Format",
            "description": "Verify response is valid JSON",
            "passed": is_valid,
            "expected": "Valid JSON",
            "actual": "Valid" if is_valid else "Invalid",
            "message": "Response is valid JSON" if is_valid else "Response is not valid JSON",
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_required_fields(self):
        """Required fields validation"""
        if isinstance(self.response_data, dict):
            field_count = len(self.response_data)
            has_fields = field_count > 0

            result = {
                "name": "Required Fields Present",
                "description": "Verify response contains required fields",
                "passed": has_fields,
                "expected": "Response should have fields",
                "actual": f"Has {field_count} fields",
                "message": f"Response contains {field_count} required fields" if has_fields else "No fields in response",
                "category": "Functional"
            }
            self.test_results.append(result)

    def _test_data_types(self):
        """Data types validation"""
        if not isinstance(self.response_data, dict):
            return

        type_info = []
        issues = []

        for key, value in list(self.response_data.items())[:10]:
            data_type = type(value).__name__
            type_info.append({"field": key, "type": data_type})

            # Validate expected types
            if value is None:
                issues.append(f"Field '{key}' is null")

        result = {
            "name": "Data Type Validation",
            "description": "Verify all fields have valid data types",
            "passed": len(issues) == 0,
            "expected": "All fields should have non-null types",
            "actual": f"Checked {len(type_info)} fields",
            "message": f"Validated {len(type_info)} fields" if len(issues) == 0 else f"Found {len(issues)} type issues",
            "details": type_info,
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_null_values(self):
        """Null values validation"""
        if not isinstance(self.response_data, dict):
            return

        null_fields = [k for k, v in self.response_data.items() if v is None]
        all_fields = len(self.response_data)
        non_null_fields = all_fields - len(null_fields)

        result = {
            "name": "Null Values Check",
            "description": "Check for null values in response",
            "passed": len(null_fields) == 0,
            "expected": "No null values in required fields",
            "actual": f"{non_null_fields}/{all_fields} non-null fields",
            "message": f"All {all_fields} fields are non-null" if len(null_fields) == 0 else f"Found {len(null_fields)} null fields: {null_fields}",
            "category": "Functional"
        }
        self.test_results.append(result)

    def _test_arrays(self):
        """Array validation"""
        if not isinstance(self.response_data, dict):
            return

        arrays = {k: v for k, v in self.response_data.items() if isinstance(v, list)}
        if not arrays:
            return

        for field_name, array_value in list(arrays.items())[:5]:
            result = {
                "name": f"Array '{field_name}' Validation",
                "description": f"Verify array field '{field_name}' is valid",
                "passed": True,
                "expected": "Valid array",
                "actual": f"Array with {len(array_value)} items",
                "message": f"Array '{field_name}' has {len(array_value)} items",
                "category": "Functional"
            }
            self.test_results.append(result)

    def _test_nested_objects(self):
        """Nested objects validation"""
        if not isinstance(self.response_data, dict):
            return

        nested_objects = {k: v for k, v in self.response_data.items() if isinstance(v, dict)}
        if not nested_objects:
            return

        for field_name, nested_obj in list(nested_objects.items())[:5]:
            nested_fields = len(nested_obj)
            result = {
                "name": f"Nested Object '{field_name}' Validation",
                "description": f"Verify nested object '{field_name}' is valid",
                "passed": nested_fields > 0,
                "expected": "Nested object with fields",
                "actual": f"Nested object with {nested_fields} properties",
                "message": f"Nested object '{field_name}' has {nested_fields} properties",
                "category": "Functional"
            }
            self.test_results.append(result)

    def get_summary(self) -> Dict[str, Any]:
        """Get test execution summary"""
        if not self.test_results:
            return {}

        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test.get("passed", False))
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Group by category
        by_category = {}
        for test in self.test_results:
            category = test.get("category", "Other")
            if category not in by_category:
                by_category[category] = {"passed": 0, "failed": 0}
            if test.get("passed"):
                by_category[category]["passed"] += 1
            else:
                by_category[category]["failed"] += 1

        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": round(success_rate, 2),
            "status": "✅ ALL PASSED" if failed_tests == 0 else f"❌ {failed_tests} FAILED",
            "by_category": by_category
        }

    def get_failed_tests(self) -> List[Dict[str, Any]]:
        """Get list of failed tests"""
        return [test for test in self.test_results if not test.get("passed", False)]

    def get_tests_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tests by category"""
        return [test for test in self.test_results if test.get("category") == category]
