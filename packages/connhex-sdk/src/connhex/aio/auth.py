import httpx

from connhex.urls import build_accounts_url

PASSWORD_LOGIN_TIMEOUT = 10.0


async def password_login(
    instance_url: str,
    identifier: str,
    password: str,
    *,
    timeout: float = PASSWORD_LOGIN_TIMEOUT,
) -> str:
    """Exchange username/password for a Connhex session token.

    Returns the bearer token suitable for `Connhex(token=...)`.
    """
    accounts_url = build_accounts_url(instance_url)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
