from custom_script_executor import CustomScriptExecutor, transpile_js_to_python

# Test the transpiler output first
js_scripts = [
    'pm.test("Status code is 200", function() { pm.response.to.have.status(200); });',
    'pm.test("Response time under 2000ms", function() { pm.expect(pm.response.responseTime).to.be.below(2000); });',
    'pm.test("Cohort List Should Not Be Empty", function() { var jsonData = pm.response.json(); pm.expect(jsonData).to.be.an("object"); });',
    'pm.test("Validate Required Fields", function() { var jsonData = pm.response.json(); pm.expect(jsonData).to.have.property("data"); });',
    'pm.test("ID Validation", function() { var jsonData = pm.response.json(); pm.expect(jsonData).to.have.property("statusCode"); });',
    'pm.test("Content-Type is JSON", function() { pm.expect(pm.response.headers.get("Content-Type") || "").to.include("application/json"); });',
    'pm.test("Response is valid JSON", function() { var responseJson; pm.expect(function() { responseJson = pm.response.json(); }).to.not.throw(); });',
]

print("=== TRANSPILER OUTPUT ===")
for js in js_scripts:
    print(f"\nJS:     {js[:60]}...")
    py = transpile_js_to_python(js)
    print(f"Python: {py[:80]}")

print("\n\n=== EXECUTION RESULTS ===")
executor = CustomScriptExecutor(
    response_data={"data": [{"id": 1, "cohortId": "C001"}], "status": "success", "statusCode": 200},
    status_code=200,
    response_time=0.22,
    headers={"Content-Type": "application/json", "Authorization": "Bearer token123"}
)

scripts = [{"id": f"t{i}", "name": js.split('"')[1], "script": js, "enabled": True}
           for i, js in enumerate(js_scripts)]

results = executor.execute_scripts(scripts)
for r in results:
    icon = "✅ PASS" if r["passed"] else "❌ FAIL"
    print(f"  {icon} | {r['name']}")
    if not r["passed"]:
        print(f"    Reason: {r['failure_reason'][:120]}")
