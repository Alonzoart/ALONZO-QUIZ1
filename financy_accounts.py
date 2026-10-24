#!/usr/bin/env python3
"""Read-only summary of linked bank accounts via the Financy API.

Credentials are read only from the .env file next to this script.
Only GET requests are made against the data API (no payments, deletes or refreshes).
"""
import json
import os
import sys
import urllib.error
import urllib.request

AUTH_URL = "https://api.open-finance.ai/oauth/token"
API_URL = "https://api.open-finance.ai/v2"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_env(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request(method, url, token=None, body=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        # Print status and error body only; never the request (it carries credentials).
        sys.exit(f"HTTP {e.code} from {url}: {e.read().decode(errors='replace')[:500]}")


def get_token(env):
    resp = request("POST", AUTH_URL, body={
        "userId": env["FINANCY_USER_ID"],
        "clientId": env["FINANCY_CLIENT_ID"],
        "clientSecret": env["FINANCY_CLIENT_SECRET"],
    })
    return resp["accessToken"]


def items(resp):
    if isinstance(resp, list):
        return resp
    for key in ("data", "items", "results", "connections", "accounts"):
        if isinstance(resp, dict) and isinstance(resp.get(key), list):
            return resp[key]
    return []


def main():
    env = load_env(ENV_PATH)
    token = get_token(env)
    print("Authenticated OK.")

    connections = items(request("GET", f"{API_URL}/connections", token))
    print(f"Connections: {len(connections)}")
    for conn in connections:
        conn_id = conn.get("id") or conn.get("connectionId")
        name = conn.get("providerName") or conn.get("provider") or conn_id
        print(f"\n== {name} (status: {conn.get('status', '?')})")
        accounts = items(request("GET", f"{API_URL}/connections/{conn_id}/accounts", token))
        for acc in accounts:
            label = acc.get("name") or acc.get("displayName") or acc.get("type") or "account"
            number = str(acc.get("accountNumber") or acc.get("iban") or "")
            masked = f"****{number[-4:]}" if number else ""
            balance = acc.get("balance") or acc.get("balances")
            print(f"  - {label} {masked} | balance: {json.dumps(balance, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
