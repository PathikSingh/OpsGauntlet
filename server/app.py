"""FastAPI app for OpsGauntlet."""

from fastapi.responses import HTMLResponse, PlainTextResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:  # pragma: no cover
    raise ImportError("openenv-core is required to run this environment.") from exc

try:
    from ..models import OpsGauntletAction, OpsGauntletObservation
    from .environment import OpsGauntletEnvironment
except ImportError:  # pragma: no cover
    from models import OpsGauntletAction, OpsGauntletObservation  # type: ignore
    from server.environment import OpsGauntletEnvironment  # type: ignore


app = create_app(
    OpsGauntletEnvironment,
    OpsGauntletAction,
    OpsGauntletObservation,
    env_name="opsgauntlet",
    max_concurrent_envs=4,
)


@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    return HTMLResponse(
        """
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Ops Gauntlet</title>
            <style>
              :root {
                color-scheme: light;
                --bg: #f5f7fb;
                --panel: rgba(255, 255, 255, 0.88);
                --panel-border: rgba(15, 23, 42, 0.08);
                --text: #0f172a;
                --muted: #475569;
                --brand: #0f766e;
                --brand-2: #1d4ed8;
                --shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
              }

              * { box-sizing: border-box; }

              body {
                margin: 0;
                font-family: "Segoe UI", "Inter", sans-serif;
                color: var(--text);
                background:
                  radial-gradient(circle at top left, rgba(29, 78, 216, 0.14), transparent 28%),
                  radial-gradient(circle at top right, rgba(15, 118, 110, 0.14), transparent 22%),
                  linear-gradient(180deg, #eef4ff 0%, var(--bg) 45%, #ffffff 100%);
              }

              .page {
                max-width: 1120px;
                margin: 0 auto;
                padding: 56px 24px 80px;
              }

              .hero {
                display: grid;
                grid-template-columns: 1.4fr 1fr;
                gap: 24px;
                align-items: stretch;
              }

              .panel {
                background: var(--panel);
                border: 1px solid var(--panel-border);
                border-radius: 28px;
                box-shadow: var(--shadow);
                backdrop-filter: blur(12px);
              }

              .hero-copy {
                padding: 40px;
              }

              .eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                padding: 10px 14px;
                border-radius: 999px;
                background: rgba(15, 118, 110, 0.08);
                color: var(--brand);
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
              }

              h1 {
                margin: 20px 0 16px;
                font-size: clamp(42px, 7vw, 72px);
                line-height: 0.95;
                letter-spacing: -0.04em;
              }

              .lead {
                margin: 0;
                max-width: 62ch;
                font-size: 18px;
                line-height: 1.7;
                color: var(--muted);
              }

              .hero-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 14px;
                margin-top: 30px;
              }

              .button {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 13px 18px;
                border-radius: 14px;
                font-weight: 600;
                text-decoration: none;
                transition: transform 0.16s ease, box-shadow 0.16s ease;
              }

              .button.primary {
                background: linear-gradient(135deg, var(--brand), var(--brand-2));
                color: #fff;
                box-shadow: 0 18px 40px rgba(29, 78, 216, 0.22);
              }

              .button.secondary {
                color: var(--text);
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(15, 23, 42, 0.08);
              }

              .button:hover {
                transform: translateY(-1px);
              }

              .metrics {
                padding: 26px;
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
              }

              .metric {
                padding: 18px;
                border-radius: 20px;
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(241,245,249,0.94));
                border: 1px solid rgba(15, 23, 42, 0.06);
              }

              .metric-label {
                color: var(--muted);
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
              }

              .metric-value {
                margin-top: 10px;
                font-size: 34px;
                font-weight: 700;
                letter-spacing: -0.04em;
              }

              .section-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-top: 24px;
              }

              .card {
                padding: 24px;
              }

              .card h2 {
                margin: 0 0 10px;
                font-size: 20px;
              }

              .card p,
              .card li {
                color: var(--muted);
                line-height: 1.65;
              }

              .card ul {
                margin: 12px 0 0;
                padding-left: 18px;
              }

              a {
                color: var(--brand-2);
              }

              .footer {
                margin-top: 22px;
                color: var(--muted);
                font-size: 14px;
              }

              @media (max-width: 920px) {
                .hero,
                .section-grid {
                  grid-template-columns: 1fr;
                }

                .hero-copy,
                .metrics,
                .card {
                  padding: 24px;
                }
              }
            </style>
          </head>
          <body>
            <main class="page">
              <section class="hero">
                <div class="panel hero-copy">
                  <div class="eyebrow">OpenEnv Benchmark</div>
                  <h1>Ops Gauntlet</h1>
                  <p class="lead">
                    A release-engineering benchmark for agents that must diagnose incidents, choose rollback versus
                    fix-forward, validate CI, deploy safely, verify recovery, and close the loop with incident hygiene.
                  </p>
                  <div class="hero-actions">
                    <a class="button primary" href="/docs">Open API Docs</a>
                    <a class="button secondary" href="/schema">View Schema</a>
                    <a class="button secondary" href="/health">Check Health</a>
                  </div>
                  <p class="footer">
                    Live Hugging Face Space for the Meta PyTorch OpenEnv Hackathon submission.
                  </p>
                </div>
                <div class="panel metrics">
                  <div class="metric">
                    <div class="metric-label">Tasks</div>
                    <div class="metric-value">12</div>
                  </div>
                  <div class="metric">
                    <div class="metric-label">Tools</div>
                    <div class="metric-value">17</div>
                  </div>
                  <div class="metric">
                    <div class="metric-label">Baseline Solve Rate</div>
                    <div class="metric-value">100%</div>
                  </div>
                  <div class="metric">
                    <div class="metric-label">Focus</div>
                    <div class="metric-value">Safe Ops</div>
                  </div>
                </div>
              </section>

              <section class="section-grid">
                <article class="panel card">
                  <h2>What It Evaluates</h2>
                  <p>
                    Agents are scored on diagnosis, containment, remediation choice, canary safety, recovery
                    verification, and customer-facing incident closure.
                  </p>
                </article>
                <article class="panel card">
                  <h2>Scenario Families</h2>
                  <ul>
                    <li>Rollback-first incidents</li>
                    <li>Fix-forward CI hotfixes</li>
                    <li>Customer-facing sev incidents</li>
                    <li>Full lifecycle postmortem tasks</li>
                  </ul>
                </article>
                <article class="panel card">
                  <h2>Quick Links</h2>
                  <ul>
                    <li><a href="/docs">FastAPI documentation</a></li>
                    <li><a href="/schema">Environment schema</a></li>
                    <li><a href="/health">Health endpoint</a></li>
                  </ul>
                </article>
              </section>
            </main>
          </body>
        </html>
        """
    )


@app.get("/robots.txt", include_in_schema=False)
def robots() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nAllow: /\n")


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
