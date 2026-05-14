import httpx

KRATOS_TIMEOUT = 10.0


async def kratos_password_login(
    accounts_url: str,
    identifier: str,
    password: str,
) -> str:
    """Two-step Kratos API login. Returns the ory_st_* session token."""
    async with httpx.AsyncClient(timeout=KRATOS_TIMEOUT) as client:
        flow_resp = await client.get(
            f"{accounts_url}/auth/self-service/login/api",
            headers={"Accept": "application/json"},
        )
        flow_resp.raise_for_status()
        action_url = flow_resp.json()["ui"]["action"]

        login_resp = await client.post(
            action_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "identifier": identifier,
                "password": password,
                "method": "password",
            },
        )

        if login_resp.status_code != 200:
            error_data = login_resp.json()
            messages = error_data.get("ui", {}).get("messages", [])
            if messages:
                raise ValueError(messages[0].get("text", "Login failed"))
            raise ValueError("Invalid credentials")

        return login_resp.json()["session_token"]
