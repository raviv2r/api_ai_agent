import json
from typing import Dict, Any, List, Tuple

class SchemaValidator:
    """Generate and validate JSON schema"""

    def __init__(self, response_data: Dict[str, Any]):
        self.response_data = response_data
        self.schema = None

    def generate_schema(self) -> Dict[str, Any]:
        """Generate JSON schema from response"""
        self.schema = self._infer_schema(self.response_data)
        return self.schema

    def _infer_schema(self, data: Any, required: bool = False) -> Dict[str, Any]:
        """Infer JSON schema from data"""
        if data is None:
            return {"type": "null"}
        elif isinstance(data, bool):
            return {"type": "boolean"}
        elif isinstance(data, int):
            return {"type": "integer"}
        elif isinstance(data, float):
            return {"type": "number"}
        elif isinstance(data, str):
            return {"type": "string"}
        elif isinstance(data, list):
            if data:
                # Infer from first item
                item_schema = self._infer_schema(data[0])
                return {
                    "type": "array",
                    "items": item_schema,
                    "minItems": 0
                }
            return {"type": "array", "items": {}}
        elif isinstance(data, dict):
            properties = {}
            required_fields = []
            
            for key, value in data.items():
                properties[key] = self._infer_schema(value, True)
                required_fields.append(key)
            
            return {
                "type": "object",
                "properties": properties,
                "required": required_fields if required_fields else []
            }
        else:
            return {"type": "string"}

    def validate_schema(self) -> Tuple[bool, List[str]]:
        """Validate response against generated schema"""
        if not self.schema:
            self.generate_schema()
        
        errors = self._validate_against_schema(self.response_data, self.schema)
        return len(errors) == 0, errors

    def _validate_against_schema(self, data: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
        """Recursively validate data against schema"""
        errors = []
        
        if "type" not in schema:
            return errors
        
        expected_type = schema["type"]
        
        # Type validation
        if expected_type == "null" and data is not None:
            errors.append(f"{path}: Expected null but got {type(data).__name__}")
        elif expected_type == "boolean" and not isinstance(data, bool):
            errors.append(f"{path}: Expected boolean but got {type(data).__name__}")
        elif expected_type == "integer" and not isinstance(data, int):
            errors.append(f"{path}: Expected integer but got {type(data).__name__}")
        elif expected_type == "number" and not isinstance(data, (int, float)):
            errors.append(f"{path}: Expected number but got {type(data).__name__}")
        elif expected_type == "string" and not isinstance(data, str):
            errors.append(f"{path}: Expected string but got {type(data).__name__}")
        elif expected_type == "array" and not isinstance(data, list):
            errors.append(f"{path}: Expected array but got {type(data).__name__}")
        elif expected_type == "object" and not isinstance(data, dict):
            errors.append(f"{path}: Expected object but got {type(data).__name__}")
        
        # Object properties validation
        if expected_type == "object" and isinstance(data, dict):
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Check required fields
            for field in required:
                if field not in data:
                    errors.append(f"{path}.{field}: Required field missing")
            
            # Validate each property
            for key, value in data.items():
                if key in properties:
                    prop_errors = self._validate_against_schema(value, properties[key], f"{path}.{key}")
                    errors.extend(prop_errors)
        
        # Array items validation
        if expected_type == "array" and isinstance(data, list):
            items_schema = schema.get("items", {})
            for i, item in enumerate(data):
                item_errors = self._validate_against_schema(item, items_schema, f"{path}[{i}]")
                errors.extend(item_errors)
        
        return errors

    def get_schema_string(self) -> str:
        """Get schema as formatted JSON string"""
        if not self.schema:
            self.generate_schema()
        return json.dumps(self.schema, indent=2)
