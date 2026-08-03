"""
custom_script_executor.py
─────────────────────────
Executes user-defined Post-response test scripts.

Supports BOTH syntaxes:
  • Postman JavaScript  →  auto-transpiled to Python before exec
  • Python (direct)     →  executed as-is

JavaScript Postman syntax supported:
    pm.test("name", function() { ... });
    pm.expect(x).to.have.status(200)
    pm.expect(x).to.be.below(2000)
    pm.response.to.have.status(200)
    pm.response.json()
    pm.response.code / responseTime
    var x = ...  /  let x = ...  /  const x = ...
"""

import json
import re
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript → Python Transpiler
# ─────────────────────────────────────────────────────────────────────────────

def _apply_chain_transforms(code: str) -> str:
    """Apply all Postman JS chain → Python transformations to a code string."""

    # pm.response.to.have.status(N)
    code = re.sub(r'pm\.response\.to\.have\.status\s*\((\d+)\)',
                  r'pm.expect(pm.response.code).equal(\1)', code)
    # pm.response.to.have.header("x")
    code = re.sub(r'pm\.response\.to\.have\.header\s*\(([^)]+)\)',
                  r'pm.expect(pm.response.header(\1)).not_.be_null()', code)
    # pm.response.to.not.be.empty
    code = re.sub(r'pm\.response\.to\.not\.be\.empty',
                  r'pm.expect(pm.response.json()).not_.be_empty()', code)
    # pm.response.to.be.withBody
    code = re.sub(r'pm\.response\.to\.be\.withBody',
                  r'pm.expect(pm.response.json()).not_.be_null()', code)
    # pm.response.headers.get("x")
    code = re.sub(r'pm\.response\.headers\.get\s*\(([^)]+)\)',
                  r'pm.response.header(\1)', code)
    # pm.request.url.toString()  →  str(pm.request.url)
    code = re.sub(r'pm\.request\.url\.toString\s*\(\s*\)',
                  r'str(pm.request.url)', code)
    # pm.expect(function(){...}) → pm.expect(True)
    code = re.sub(r'pm\.expect\s*\(\s*function\s*\(\s*\)\s*\{[^}]*\}\s*\)',
                  r'pm.expect(True)', code, flags=re.DOTALL)
    # Also handle pm.expect(function(){ ... nested ... })  (greedy version)
    code = re.sub(r'pm\.expect\s*\(\s*function\s*\([^)]*\)\s*\{.*?\}\s*\)',
                  r'pm.expect(True)', code, flags=re.DOTALL)
    # .to.not.throw()
    code = re.sub(r'\.to\.not\.throw\s*\(\s*\)', '', code)
    # Stray closing brace lines left from nested function removal
    code = re.sub(r'^\s*\}\s*\)\s*$', '', code, flags=re.MULTILINE)
    # .to.have.status(N)
    code = re.sub(r'\.to\.have\.status\s*\((\d+)\)', r'.equal(\1)', code)
    # .to.have.property("x")
    code = re.sub(r'\.to\.have\.property\s*\(', r'.have_property(', code)
    # .to.include(x)
    code = re.sub(r'\.to\.include\s*\(', r'.include(', code)
    # .to.be.below(n)
    code = re.sub(r'\.to\.be\.below\s*\(', r'.below(', code)
    # .to.be.above(n)
    code = re.sub(r'\.to\.be\.above\s*\(', r'.above(', code)
    # .to.be.a / .to.be.an
    code = re.sub(r'\.to\.be\.an?\s*\(', r'.a(', code)
    # .to.equal / .to.eql
    code = re.sub(r'\.to\.eql?\s*\(', r'.equal(', code)
    # .to.not.be.null
    code = re.sub(r'\.to\.not\.be\.null\b', r'.not_.be_null()', code)
    # .to.be.null
    code = re.sub(r'\.to\.be\.null\b', r'.be_null()', code)
    # .not.to. / .to.not.
    code = re.sub(r'\.(not\.to|to\.not)\.', r'.not_.', code)
    # .to.be.greaterThan
    code = re.sub(r'\.to\.be\.greaterThan\s*\(', r'.above(', code)
    # .to.be.lessThan
    code = re.sub(r'\.to\.be\.lessThan\s*\(', r'.below(', code)
    # .to.be.within
    code = re.sub(r'\.to\.be\.within\s*\(', r'.within(', code)
    # .to.match
    code = re.sub(r'\.to\.match\s*\(', r'.match(', code)
    # strip stray .to. and .be. (not followed by known methods)
    code = re.sub(r'\.(to|be)\b\.', r'.', code)
    # JS || → Python or
    code = re.sub(r'\s*\|\|\s*', r' or ', code)
    # JS && → Python and
    code = re.sub(r'\s*&&\s*', r' and ', code)
    # JS comments // → #
    code = re.sub(r'(?<!["\'])//(?!["\'])', '#', code)
    # Trailing .to / .be / .have
    code = re.sub(r'\.(to|be|have)\s*$', '', code, flags=re.MULTILINE)

    return code


def transpile_js_to_python(js_code: str):
    """
    Convert Postman JavaScript Post-response script syntax to valid Python.
    Returns (python_code: str, body_registry: dict)
    Handles both JS and Python syntax — Python passes through unchanged.
    """
    code = js_code

    # ── 1. Variable declarations: var/let/const x = y  →  x = y ────────────
    code = re.sub(r'\b(var|let|const)\s+', '', code)
    # Strip bare empty declarations like "responseJson;" (no assignment)
    code = re.sub(r'^\s*([a-zA-Z_]\w*)\s*;?\s*$', '', code, flags=re.MULTILINE)

    # ── 1b. Pre-process: replace pm.expect(function(){...}) BEFORE body extraction ──
    # This prevents nested braces from breaking the outer pm.test regex
    code = re.sub(r'pm\.expect\s*\(\s*function\s*\([^)]*\)\s*\{[^}]*\}\s*\)',
                  r'pm.expect(True)', code, flags=re.DOTALL)
    code = re.sub(r'\.to\.not\.throw\s*\(\s*\)', '', code)

    # ── 2. pm.test("name", function() { body }) → _pm_test_block(...) ───────
    _body_registry = {}
    _body_counter = [0]

    def replace_pm_test(m):
        name = m.group(1)
        raw_body = m.group(2).strip()
        # Apply var/let/const stripping to body too
        raw_body = re.sub(r'\b(var|let|const)\s+', '', raw_body)
        # Convert semicolons to newlines inside body
        body = re.sub(r'\s*;\s*(?=\S)', '\n', raw_body)
        body = re.sub(r';\s*$', '', body, flags=re.MULTILINE)
        # Apply all chain transforms to body
        body = _apply_chain_transforms(body)
        # Remove bare variable name lines (e.g. "responseJson" with no assignment)
        body = re.sub(r'^\s*([a-zA-Z_]\w*)\s*$', '', body, flags=re.MULTILINE)
        # Remove empty lines
        body = '\n'.join(line for line in body.splitlines() if line.strip())
        idx = _body_counter[0]
        _body_registry[idx] = body.strip()
        _body_counter[0] += 1
        return f'_pm_test_block({name}, _bodies[{idx}])'
    code = re.sub(
        r'pm\.test\s*\(\s*(["\'][^"\']+["\'])\s*,\s*function\s*\(\s*\)\s*\{([^}]*)\}\s*\)',
        replace_pm_test,
        code,
        flags=re.DOTALL,
    )

    # ── 3. Apply all chain transforms to outer code ──────────────────────────
    code = _apply_chain_transforms(code)

    # ── 4. Convert semicolons to newlines ─────────────────────────────────────
    code = re.sub(r'\s*;\s*(?=\S)', '\n', code)
    code = re.sub(r';\s*$', '', code, flags=re.MULTILINE)

    # ── 5. Clean up orphaned JS closing braces/parens left after transforms ──
    code = re.sub(r'^\s*\}\s*\)\s*;?\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*\}\s*;?\s*$', '', code, flags=re.MULTILINE)

    return code.strip(), _body_registry


def _pm_test_block(pm_obj, name: str, body_code: str):
    """
    Execute a transpiled pm.test block.
    Called when JS function(){} syntax was used.
    body_code is passed directly from the registry — no escaping needed.
    """
    try:
        exec(body_code, {"pm": pm_obj, "json": json, "re": re})
        pm_obj._results.append({
            "name": name,
            "passed": True,
            "message": f"✅ {name}",
            "expected": "Assertion passed",
            "actual": "Passed",
            "failure_reason": "",
            "category": "Custom",
        })
    except AssertionError as e:
        pm_obj._results.append({
            "name": name,
            "passed": False,
            "message": f"❌ {name}",
            "expected": "Assertion should pass",
            "actual": str(e),
            "failure_reason": str(e),
            "category": "Custom",
        })
    except Exception as e:
        pm_obj._results.append({
            "name": name,
            "passed": False,
            "message": f"❌ {name}",
            "expected": "Script should execute without error",
            "actual": f"{type(e).__name__}: {e}",
            "failure_reason": f"Script error — check syntax: {type(e).__name__}: {e}",
            "category": "Custom",
        })


# ─────────────────────────────────────────────────────────────────────────────
# pm helper  (Postman-style assertion API — runs in Python)
# ─────────────────────────────────────────────────────────────────────────────

class _Expect:
    """Chainable assertion helper  — mirrors Chai.js / Postman pm.expect()"""

    def __init__(self, value: Any, label: str = "value"):
        self._value = value
        self._label = label
        self._negated = False

    # --- negation ---
    @property
    def not_(self):
        self._negated = True
        return self

    # allow   pm.expect(x).to.not_be_null  AND  pm.expect(x).to.not_.be.null
    def __getattr__(self, name: str):
        if name in ("to", "be", "have", "that", "and_", "is_", "a_", "an_"):
            return self
        raise AttributeError(f"_Expect has no attribute '{name}'")

    # --- assertions ---
    def equal(self, expected):
        ok = self._value == expected
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} {'not ' if self._negated else ''}to equal "
                f"{repr(expected)}, got {repr(self._value)}"
            )
        return self

    def eql(self, expected):
        return self.equal(expected)

    def include(self, substring):
        if isinstance(self._value, str):
            ok = substring in self._value
        elif isinstance(self._value, (list, dict)):
            ok = substring in self._value
        else:
            ok = False
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} {'not ' if self._negated else ''}to include {repr(substring)}, "
                f"got {repr(self._value)}"
            )
        return self

    def have_property(self, key: str):
        if isinstance(self._value, dict):
            ok = key in self._value
        else:
            ok = hasattr(self._value, key)
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected object {'not ' if self._negated else ''}to have property '{key}'"
            )
        return self

    # alias
    def prop(self, key: str):
        return self.have_property(key)

    def be_null(self):
        ok = self._value is None
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected value {'not ' if self._negated else ''}to be null, got {repr(self._value)}"
            )
        return self

    @property
    def null(self):
        return self.be_null()

    def be_a(self, type_name: str):
        type_map = {
            "string": str, "str": str,
            "number": (int, float), "int": int, "float": float,
            "boolean": bool, "bool": bool,
            "object": dict,
            "array": list, "list": list,
            "null": type(None),
        }
        expected_type = type_map.get(type_name.lower())
        ok = isinstance(self._value, expected_type) if expected_type else True
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} {'not ' if self._negated else ''}to be a '{type_name}', "
                f"got {type(self._value).__name__}"
            )
        return self

    def a(self, type_name: str):
        return self.be_a(type_name)

    def an(self, type_name: str):
        return self.be_a(type_name)

    def below(self, threshold):
        ok = self._value < threshold
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} ({self._value}) {'not ' if self._negated else ''}to be below {threshold}"
            )
        return self

    def above(self, threshold):
        ok = self._value > threshold
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} ({self._value}) {'not ' if self._negated else ''}to be above {threshold}"
            )
        return self

    def within(self, lo, hi):
        ok = lo <= self._value <= hi
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} ({self._value}) {'not ' if self._negated else ''}to be within [{lo}, {hi}]"
            )
        return self

    def greater_than(self, n):
        return self.above(n)

    def less_than(self, n):
        return self.below(n)

    def length_of(self, n: int):
        ok = len(self._value) == n
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected length {'not ' if self._negated else ''}to be {n}, got {len(self._value)}"
            )
        return self

    def match(self, pattern: str):
        ok = bool(re.search(pattern, str(self._value)))
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} {'not ' if self._negated else ''}to match pattern '{pattern}', "
                f"got {repr(self._value)}"
            )
        return self

    def be_empty(self):
        ok = (self._value is None) or (self._value == "") or (self._value == []) or (self._value == {})
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(
                f"Expected {self._label} {'not ' if self._negated else ''}to be empty, got {repr(self._value)}"
            )
        return self

    @property
    def empty(self):
        return self.be_empty()

    # status shorthand
    def status(self, code: int):
        ok = self._value == code
        if self._negated:
            ok = not ok
        if not ok:
            raise AssertionError(f"Expected status {'not ' if self._negated else ''}{code}, got {self._value}")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# pm object
# ─────────────────────────────────────────────────────────────────────────────

class _PMResponse:
    def __init__(self, response_data, status_code, response_time, headers):
        self._data = response_data
        self._status_code = status_code
        self._response_time = response_time
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}

    def json(self):
        return self._data

    def text(self):
        return json.dumps(self._data) if isinstance(self._data, (dict, list)) else str(self._data)

    @property
    def code(self):
        return self._status_code

    @property
    def status(self):
        return self._status_code

    @property
    def responseTime(self):
        return int(self._response_time * 1000)  # ms

    def header(self, name: str) -> Optional[str]:
        return self._headers.get(name.lower())

    def has_header(self, name: str) -> bool:
        return name.lower() in self._headers

    # ── Postman chained fluent API: pm.response.to.have.status(200) ──────────
    @property
    def to(self):
        return _PMResponseAssertion(self)

    # pm.response.headers.get("x") shorthand
    @property
    def headers(self):
        return _PMHeaders(self._headers)


class _PMHeaders:
    """Mirrors pm.response.headers object"""
    def __init__(self, headers_lower: dict):
        self._h = headers_lower

    def get(self, name: str, default: str = "") -> str:
        return self._h.get(name.lower(), default)

    def has(self, name: str) -> bool:
        return name.lower() in self._h


class _PMResponseAssertion:
    """
    Handles pm.response.to.have.status() / pm.response.to.be.withBody etc.
    Allows JS-style chaining that the transpiler might not catch.
    """
    def __init__(self, response: "_PMResponse"):
        self._r = response

    @property
    def have(self):
        return self

    @property
    def be(self):
        return self

    @property
    def not_(self):
        return _PMResponseAssertionNegated(self._r)

    def status(self, code: int):
        if self._r._status_code != code:
            raise AssertionError(f"Expected status {code}, got {self._r._status_code}")

    def header(self, name: str):
        if not self._r.has_header(name):
            raise AssertionError(f"Expected header '{name}' to be present")

    @property
    def withBody(self):
        if not self._r._data:
            raise AssertionError("Expected response to have a body")

    @property
    def empty(self):
        if self._r._data:
            raise AssertionError("Expected response to be empty")


class _PMResponseAssertionNegated:
    def __init__(self, response: "_PMResponse"):
        self._r = response

    @property
    def be(self):
        return self

    @property
    def empty(self):
        if not self._r._data:
            raise AssertionError("Expected response not to be empty")


class _PMRequest:
    """Mirrors Postman's pm.request object"""
    def __init__(self, url: str, method: str, headers: dict, body: Any):
        self._url = url
        self._method = method.upper() if method else "GET"
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._body = body

    @property
    def url(self):
        return _PMUrl(self._url)

    @property
    def method(self):
        return self._method

    @property
    def headers(self):
        return _PMHeaders(self._headers)

    @property
    def body(self):
        return self._body


class _PMUrl:
    """Mirrors pm.request.url"""
    def __init__(self, url: str):
        self._url = url or ""

    def toString(self) -> str:
        return self._url

    def __str__(self) -> str:
        return self._url

    def __contains__(self, item):
        return item in self._url


class _PMVariables:
    """Mirrors pm.variables / pm.environment / pm.globals — in-memory store"""
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any):
        self._store[key] = value

    def has(self, key: str) -> bool:
        return key in self._store

    def unset(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


class PMObject:
    """
    Postman-like `pm` object available inside user scripts.
    Supports both JavaScript Postman syntax (auto-transpiled) and Python.

    Available objects:
        pm.response      — response data, status, headers, time
        pm.request       — request url, method, headers, body
        pm.expect(x)     — chainable assertion helper
        pm.test("name", fn) — register and run a test
        pm.variables     — in-memory key/value store
        pm.environment   — in-memory key/value store
        pm.globals       — in-memory key/value store
        pm.info          — execution metadata
    """

    def __init__(self, response_data, status_code, response_time, headers,
                 method: str = "GET", url: str = "", request_body: Any = None):
        self.response   = _PMResponse(response_data, status_code, response_time, headers)
        self.request    = _PMRequest(url, method, headers, request_body)
        self.variables  = _PMVariables()
        self.environment = _PMVariables()
        self.globals    = _PMVariables()
        self.info       = {"eventName": "postResponse", "iteration": 1}
        self._results: List[Dict[str, Any]] = []

    def test(self, name: str, fn):
        """Register and immediately execute a test assertion."""
        try:
            fn()
            self._results.append({
                "name": name,
                "passed": True,
                "message": f"✅ {name}",
                "expected": "Assertion passed",
                "actual": "Passed",
                "failure_reason": "",
                "category": "Custom",
            })
        except AssertionError as e:
            self._results.append({
                "name": name,
                "passed": False,
                "message": f"❌ {name}",
                "expected": "Assertion should pass",
                "actual": str(e),
                "failure_reason": str(e),
                "category": "Custom",
            })
        except Exception as e:
            self._results.append({
                "name": name,
                "passed": False,
                "message": f"❌ {name}",
                "expected": "Script should execute without error",
                "actual": f"{type(e).__name__}: {e}",
                "failure_reason": f"Script error: {type(e).__name__}: {e}",
                "category": "Custom",
            })

    def expect(self, value: Any, label: str = "value") -> _Expect:
        return _Expect(value, label)

    def get_results(self) -> List[Dict[str, Any]]:
        return self._results


# ─────────────────────────────────────────────────────────────────────────────
# Script Executor
# ─────────────────────────────────────────────────────────────────────────────

class CustomScriptExecutor:
    """
    Runs a list of user-defined test script dicts against the API response.

    Each script dict:
        {
            "id":      str,
            "name":    str,
            "script":  str,   # Python code using `pm`
            "enabled": bool,
        }
    """

    # Default scripts shown when a user first opens the editor
    DEFAULT_SCRIPTS = [
        {
            "id": "default_001",
            "name": "Status code is 200",
            "script": 'pm.test("Status code is 200", lambda: pm.expect(pm.response.code).equal(200))',
            "enabled": True,
        },
        {
            "id": "default_002",
            "name": "Response time under 2000ms",
            "script": 'pm.test("Response time under 2000ms", lambda: pm.expect(pm.response.responseTime).below(2000))',
            "enabled": True,
        },
        {
            "id": "default_003",
            "name": "Response body is not empty",
            "script": (
                'data = pm.response.json()\n'
                'pm.test("Response body is not empty", lambda: pm.expect(data).not_.be_empty())'
            ),
            "enabled": True,
        },
        {
            "id": "default_004",
            "name": "Response is a valid object",
            "script": 'pm.test("Response is a valid object", lambda: pm.expect(pm.response.json()).a("object"))',
            "enabled": True,
        },
        {
            "id": "default_005",
            "name": "Status code is in valid range",
            "script": 'pm.test("Status code in valid range", lambda: pm.expect(pm.response.code).within(200, 599))',
            "enabled": True,
        },
    ]

    def __init__(self, response_data, status_code: int, response_time: float,
                 headers: Dict[str, str] = None, method: str = "GET",
                 url: str = "", request_body: Any = None):
        self.response_data = response_data
        self.status_code = status_code
        self.response_time = response_time
        self.headers = headers or {}
        self.method = method
        self.url = url
        self.request_body = request_body

    def execute_scripts(self, scripts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of script dicts and return individual results.
        Disabled scripts are skipped and marked as SKIPPED.
        """
        all_results = []

        for script_def in scripts:
            if not script_def.get("enabled", True):
                all_results.append({
                    "name": script_def.get("name", "Unnamed"),
                    "passed": True,
                    "message": f"⏭️ {script_def.get('name', 'Unnamed')} (Skipped — disabled)",
                    "expected": "N/A",
                    "actual": "Skipped",
                    "failure_reason": "",
                    "category": "Custom",
                    "skipped": True,
                })
                continue

            pm = PMObject(
                self.response_data,
                self.status_code,
                self.response_time,
                self.headers,
                method=self.method,
                url=self.url,
                request_body=self.request_body,
            )

            script_code = script_def.get("script", "").strip()
            if not script_code:
                continue

            # Auto-detect and transpile JavaScript syntax to Python
            python_code, body_registry = transpile_js_to_python(script_code)

            try:
                exec(python_code, {
                    "pm": pm,
                    "json": json,
                    "re": re,
                    "_pm_test_block": lambda name, body: _pm_test_block(pm, name, body),
                    "_bodies": body_registry,
                })
            except Exception as e:
                all_results.append({
                    "name": script_def.get("name", "Unnamed"),
                    "passed": False,
                    "message": f"❌ {script_def.get('name', 'Unnamed')} — Script Error",
                    "expected": "Script should execute without error",
                    "actual": f"{type(e).__name__}: {e}",
                    "failure_reason": f"Script error: {type(e).__name__}: {e}",
                    "category": "Custom",
                    "skipped": False,
                })
                continue

            # Collect results registered via pm.test()
            results = pm.get_results()
            if results:
                all_results.extend(results)
            else:
                # Script ran without calling pm.test() — treat as info
                all_results.append({
                    "name": script_def.get("name", "Unnamed"),
                    "passed": True,
                    "message": f"✅ {script_def.get('name', 'Unnamed')} — Executed (no assertions)",
                    "expected": "Script execution",
                    "actual": "Executed successfully",
                    "failure_reason": "",
                    "category": "Custom",
                    "skipped": False,
                })

        return all_results

    def get_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        active = [r for r in results if not r.get("skipped")]
        passed = sum(1 for r in active if r.get("passed"))
        failed = len(active) - passed
        skipped = sum(1 for r in results if r.get("skipped"))
        total = len(active)
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": round(passed / total * 100, 1) if total > 0 else 0,
        }
