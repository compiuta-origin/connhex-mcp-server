import html as _html


def render_login_page(flow_id: str, error: str | None = None) -> str:
    error_html = ""
    if error:
        error_html = f"""
        <div class="error">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
                <path d="M8 4.5V9" stroke="currentColor"
                    stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
            </svg>
            <span>{_html.escape(error)}</span>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sign in to Connhex</title>
    <link rel="icon" href="/favicon.ico">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                         Roboto, sans-serif;
            background: #0a0a0f;
            color: #e4e4e7;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}
        .card {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 2rem;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
        }}
        .logo {{
            text-align: center;
            margin-bottom: 1.5rem;
        }}
        .logo h1 {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #fafafa;
        }}
        .logo p {{
            font-size: 0.875rem;
            color: #71717a;
            margin-top: 0.25rem;
        }}
        .error {{
            background: #450a0a;
            border: 1px solid #7f1d1d;
            color: #fca5a5;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        label {{
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            color: #a1a1aa;
            margin-bottom: 0.375rem;
        }}
        input[type="email"], input[type="password"] {{
            width: 100%;
            padding: 0.625rem 0.75rem;
            background: #09090b;
            border: 1px solid #3f3f46;
            border-radius: 8px;
            color: #fafafa;
            font-size: 0.9375rem;
            outline: none;
            transition: border-color 0.15s;
        }}
        input:focus {{
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
        }}
        .field {{ margin-bottom: 1rem; }}
        button {{
            width: 100%;
            padding: 0.625rem 1rem;
            background: #6366f1;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 0.9375rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
            margin-top: 0.5rem;
        }}
        button:hover {{ background: #4f46e5; }}
        button:active {{ background: #4338ca; }}
        .footer {{
            text-align: center;
            margin-top: 1.25rem;
            font-size: 0.75rem;
            color: #52525b;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <h1>Sign in to Connhex</h1>
            <p>Authorize MCP access to your account</p>
        </div>
        {error_html}
        <form method="POST" action="/oauth/login">
            <input type="hidden" name="flow_id" value="{_html.escape(flow_id)}">
            <div class="field">
                <label for="identifier">Email</label>
                <input type="email" id="identifier" name="identifier"
                       required autocomplete="email" autofocus>
            </div>
            <div class="field">
                <label for="password">Password</label>
                <input type="password" id="password" name="password"
                       required autocomplete="current-password">
            </div>
            <button type="submit">Sign in</button>
        </form>
        <div class="footer">
            Your credentials are sent directly to Connhex and are not stored.
        </div>
    </div>
</body>
</html>"""


def render_error_page(message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Error — Connhex MCP</title>
    <link rel="icon" href="/favicon.ico">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                         Roboto, sans-serif;
            background: #0a0a0f;
            color: #e4e4e7;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}
        .card {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 2rem;
            width: 100%;
            max-width: 400px;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
        }}
        h1 {{
            font-size: 1.125rem;
            color: #fca5a5;
            margin-bottom: 0.75rem;
        }}
        p {{
            font-size: 0.875rem;
            color: #a1a1aa;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Something went wrong</h1>
        <p>{_html.escape(message)}</p>
    </div>
</body>
</html>"""
