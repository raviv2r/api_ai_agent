from custom_script_executor import CustomScriptExecutor

executor = CustomScriptExecutor(
    response_data={"data": [{"id": 1}], "status": "success", "statusCode": 200},
    status_code=200,
    response_time=0.22,
    headers={"Content-Type": "application/json", "Authorization": "Bearer token123"},
    method="GET",
    url="https://ws-api.wscubetech.com/webapi/cohorts/list",
    request_body={}
)

# Scripts that use pm.request — the exact pattern causing the error
scripts = [
    {
        "id": "t1", "enabled": True,
        "name": "Request uses HTTPS",
        "script": 'pm.test("Request uses HTTPS", function () { pm.expect(pm.request.url.toString()).to.include("https://"); });',
    },
    {
        "id": "t2", "enabled": True,
        "name": "Request method is GET",
        "script": 'pm.test("Request method is GET", function () { pm.expect(pm.request.method).to.equal("GET"); });',
    },
    {
        "id": "t3", "enabled": True,
        "name": "Auth header present in request",
        "script": 'pm.test("Auth header present", function () { pm.expect(pm.request.headers.get("authorization")).to.include("Bearer"); });',
    },
    {
        "id": "t4", "enabled": True,
        "name": "pm.response.to.have.status",
        "script": 'pm.test("Status is 200", function () { pm.response.to.have.status(200); });',
    },
    {
        "id": "t5", "enabled": True,
        "name": "pm.variables.set/get",
        "script": 'pm.variables.set("myKey", "hello")\npm.test("variable works", lambda: pm.expect(pm.variables.get("myKey")).equal("hello"))',
    },
]

results = executor.execute_scripts(scripts)
print("=== pm.request Tests ===")
for r in results:
    icon = "✅ PASS" if r["passed"] else "❌ FAIL"
    print(f"  {icon} | {r['name']}")
    if not r["passed"]:
        print(f"    Reason: {r['failure_reason']}")
