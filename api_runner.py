import requests
import urllib3
import time

# Suppress SSL verification warnings caused by corporate proxy / SSL inspection
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run_api(method, url, body=None, headers=None):

    start = time.time()

    try:
        method = method.upper()

        if method == "GET":
            r = requests.get(url, headers=headers, verify=False)

        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, verify=False)

        elif method == "PUT":
            r = requests.put(url, json=body, headers=headers, verify=False)

        elif method == "DELETE":
            r = requests.delete(url, headers=headers, verify=False)

        else:
            return {"error": "Invalid Method"}

        end = time.time()

        try:
            parsed_response = r.json()
        except ValueError:
            parsed_response = r.text

        return {
            "status_code": r.status_code,
            "response_time": round(end - start, 2),
            "response": parsed_response
        }

    except Exception as e:
        return {"error": str(e)}