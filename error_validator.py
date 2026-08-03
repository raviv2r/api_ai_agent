from typing import Dict, Any, List

class ErrorValidator:
    """Validate error responses and error handling"""

    def __init__(self, response_data: Dict[str, Any], status_code: int):
        self.response_data = response_data
        self.status_code = status_code
        self.validations = []

    def validate_errors(self) -> List[Dict[str, Any]]:
        """Execute error validations"""
        self.validations = []

        if 400 <= self.status_code < 600:
            self._validate_error_response()
        else:
            # Success response
            self._validate_success_response()

        return self.validations

    def _validate_error_response(self) -> None:
        """Validate error response structure"""
        response_str = str(self.response_data).lower()

        # Check for error code
        has_error_code = "error" in response_str or "code" in response_str or "status" in response_str
        result_error_code = {
            "name": "Error Code Present",
            "description": "Verify error response contains error code",
            "passed": has_error_code,
            "expected": "Error response should contain error code",
            "actual": "Error code found" if has_error_code else "Error code missing",
            "message": "Error code is present" if has_error_code else "Warning: Error code not found"
        }
        self.validations.append(result_error_code)

        # Check for error message
        has_error_message = "message" in response_str or "error" in response_str or "description" in response_str
        result_error_msg = {
            "name": "Error Message Present",
            "description": "Verify error response contains message",
            "passed": has_error_message,
            "expected": "Error response should contain descriptive message",
            "actual": "Error message found" if has_error_message else "Error message missing",
            "message": "Error message is present" if has_error_message else "Warning: Error message not found"
        }
        self.validations.append(result_error_msg)

        # Status code specific validations
        if self.status_code == 400:
            self._validate_bad_request()
        elif self.status_code == 401:
            self._validate_unauthorized()
        elif self.status_code == 403:
            self._validate_forbidden()
        elif self.status_code == 404:
            self._validate_not_found()
        elif self.status_code == 500:
            self._validate_server_error()

    def _validate_success_response(self) -> None:
        """Validate success response"""
        response_str = str(self.response_data).lower()
        
        # Check if response has data
        has_data = bool(self.response_data)
        result = {
            "name": "Success Response Data",
            "description": "Verify success response contains data",
            "passed": has_data,
            "expected": "Success response should contain data",
            "actual": "Data present" if has_data else "No data",
            "message": "Success response contains data" if has_data else "Warning: Success response is empty"
        }
        self.validations.append(result)

    def _validate_bad_request(self) -> None:
        """Validate 400 Bad Request"""
        result = {
            "name": "400 Bad Request Validation",
            "description": "Verify 400 error indicates client error",
            "passed": True,
            "expected": "Status code 400 indicates bad request",
            "actual": "400 Bad Request",
            "message": "Bad Request error (400) is correct for invalid input"
        }
        self.validations.append(result)

    def _validate_unauthorized(self) -> None:
        """Validate 401 Unauthorized"""
        result = {
            "name": "401 Unauthorized Validation",
            "description": "Verify 401 error for missing authentication",
            "passed": True,
            "expected": "Status code 401 indicates authentication required",
            "actual": "401 Unauthorized",
            "message": "Unauthorized error (401) indicates authentication is required"
        }
        self.validations.append(result)

    def _validate_forbidden(self) -> None:
        """Validate 403 Forbidden"""
        result = {
            "name": "403 Forbidden Validation",
            "description": "Verify 403 error for insufficient permissions",
            "passed": True,
            "expected": "Status code 403 indicates access denied",
            "actual": "403 Forbidden",
            "message": "Forbidden error (403) indicates insufficient permissions"
        }
        self.validations.append(result)

    def _validate_not_found(self) -> None:
        """Validate 404 Not Found"""
        result = {
            "name": "404 Not Found Validation",
            "description": "Verify 404 error for missing resource",
            "passed": True,
            "expected": "Status code 404 indicates resource not found",
            "actual": "404 Not Found",
            "message": "Not Found error (404) indicates resource does not exist"
        }
        self.validations.append(result)

    def _validate_server_error(self) -> None:
        """Validate 500 Internal Server Error"""
        result = {
            "name": "500 Server Error Validation",
            "description": "Verify 500 error indicates server issue",
            "passed": True,
            "expected": "Status code 500 indicates server error",
            "actual": "500 Internal Server Error",
            "message": "Internal Server Error (500) indicates server-side issue"
        }
        self.validations.append(result)
