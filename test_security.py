from security_validator import SecurityValidator

v = SecurityValidator(
    url='https://ws-api.wscubetech.com/webapi/cohorts/list',
    method='GET',
    response_data={'data': [{'id': 1, 'name': 'Test'}], 'status': 'success'},
    status_code=200,
    headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.test', 'Content-Type': 'application/json'},
    request_body={}
)
results = v.validate_security()
print(f'Total security tests: {len(results)}')
for r in results:
    status = '✅ PASS' if r['passed'] else '❌ FAIL'
    sev = r.get('severity', '')
    print(f'  {status} [{sev}] {r["name"]}')
