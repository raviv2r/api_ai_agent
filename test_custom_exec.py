from custom_script_executor import CustomScriptExecutor

executor = CustomScriptExecutor(
    response_data={"data": [{"id": 1}], "status": "success", "statusCode": 200},
    status_code=200,
    response_time=0.35,
    headers={"Content-Type": "application/json"}
)

# Run default scripts
results = executor.execute_scripts(CustomScriptExecutor.DEFAULT_SCRIPTS)
print("=== DEFAULT SCRIPTS ===")
for r in results:
    status = "✅ PASS" if r["passed"] else "❌ FAIL"
    print(f"  {status} | {r['name']}")

# Run a custom user script
custom = [
    {"id": "c1", "name": "data field exists", "enabled": True,
     "script": "data = pm.response.json()\npm.test('data field exists', lambda: pm.expect(data).have_property('data'))"},
    {"id": "c2", "name": "disabled test", "enabled": False,
     "script": "pm.test('should skip', lambda: pm.expect(1).equal(99))"},
    {"id": "c3", "name": "intentional fail", "enabled": True,
     "script": "pm.test('status is 500', lambda: pm.expect(pm.response.code).equal(500))"},
]
custom_results = executor.execute_scripts(custom)
print("\n=== CUSTOM SCRIPTS ===")
for r in custom_results:
    status = "⏭️ SKIP" if r.get("skipped") else ("✅ PASS" if r["passed"] else "❌ FAIL")
    print(f"  {status} | {r['name']}")
    if not r["passed"] and not r.get("skipped"):
        print(f"    Reason: {r['failure_reason']}")

summary = executor.get_summary(custom_results)
print(f"\nSummary: {summary}")
