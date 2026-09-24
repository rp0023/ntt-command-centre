"""Real-browser smoke test against a temporary local API + built frontend.

Run after npm run build and account setup:
  python -m api.scripts.verify_login_browser
Requires requirements-dev.txt and installed Chrome. No external model calls.
"""
import os
os.environ["NTT_LLM_ENABLED"] = "0"
os.environ["NTT_AS_OF"] = "2026-09-15"

import socket
import threading
import time
import uvicorn
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright, expect
from api.config import ROOT
from api.main import app


def main():
    accounts = []
    for line in (ROOT.parent / "Context/Plans/DEMO_CREDENTIALS.local.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and "@" in line:
            accounts.append([v.strip().strip("`") for v in line.split("|")[1:-1]])
    static = StaticFiles(directory=ROOT / "web/dist", html=True)
    async def application(scope, receive, send):
        if scope["type"] == "http" and not scope["path"].startswith("/api/"):
            await static(scope, receive, send)
        else:
            await app(scope, receive, send)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(application, log_level="error", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20
    while not server.started and time.monotonic() < deadline:
        time.sleep(.05)
    if not server.started:
        raise RuntimeError("Test server did not start")
    artifacts = ROOT / "web/.test-artifacts"
    artifacts.mkdir(exist_ok=True)
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base)
            expect(page.get_by_role("heading", name="Sign in to Deal Intelligence.")).to_be_visible()
            page.screenshot(path=str(artifacts / "login-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(artifacts / "login-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_label("Email address").fill(accounts[0][1])
            page.get_by_label("Password", exact=True).fill("incorrect-password")
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Email or password is incorrect")
            homes = {"ae": "my-day", "manager": "pod-pulse", "executive": "tldr"}
            counts = {"ae": 4, "manager": 5, "executive": 6}
            filter_counts = {"ae": 6, "manager": 6, "executive": 7}
            contextual_pages = {"ae": "my-deals", "manager": "pod-pulse", "executive": "performance"}
            checked_filter_roles = set()
            for name, email, password, role, identity in accounts:
                page.get_by_label("Email address").fill(email)
                page.get_by_label("Password", exact=True).fill(password)
                page.get_by_role("button", name="Sign in", exact=True).click()
                expect(page.locator(".who-name")).to_have_text(name, timeout=60000)
                expect(page.locator("#pv-question")).to_be_visible(timeout=120000)
                expect(page.locator(".metric-banner")).to_have_count(3)
                assert page.locator(".metric-banner__metric").count() >= 5
                assert f"page={homes[role]}" in page.url
                assert "as=" not in page.url and "id=" not in page.url
                # Scope and page count are delivered by the live API.
                data = page.evaluate("""async () => {
                  const s=JSON.parse(sessionStorage.getItem('ntt.session.v2'));
                  return (await fetch('/api/meta', {headers:{Authorization:'Bearer '+s.token}})).json();
                }""")
                assert data["persona"]["active"]["identity"] == identity
                assert len(data["pages"]) == counts[role]
                if role not in checked_filter_roles:
                    checked_filter_roles.add(role)
                    # The compact popover owns dimensions with no chart on the
                    # current page and restores focus when Escape dismisses it.
                    more = page.get_by_role("button", name="More filters", exact=True)
                    more.click()
                    expect(page.get_by_role("dialog", name="More page filters")).to_be_visible()
                    labels = page.locator(".filter-field__label").all_text_contents()
                    assert len(labels) == filter_counts[role] and len(labels) == len(set(labels)), labels
                    page.keyboard.press("Escape")
                    expect(page.get_by_role("dialog", name="More page filters")).to_have_count(0)
                    assert more.evaluate("element => element === document.activeElement")

                    # A page with represented dimensions exposes those options
                    # in its chart header. The selection remains page-wide and
                    # is confirmed by the server-applied chip after refetch.
                    page.goto(base + f"?page={contextual_pages[role]}")
                    expect(page.locator("#pv-question")).to_be_visible(timeout=60000)
                    local_select = page.locator(".card-filters select").first
                    expect(local_select).to_be_visible(timeout=60000)
                    local_select.select_option(index=1)
                    removable = page.locator(".pv-filters__chip:not(.pv-filters__chip--fixed)")
                    expect(removable).to_have_count(1, timeout=60000)
                    page.locator(".pv-filters__clear").click()
                    expect(removable).to_have_count(0, timeout=60000)

                    # The measure switch now belongs to the page heading and
                    # retains the existing URL-backed page-wide behavior.
                    page.get_by_role("button", name="Revenue", exact=True).click()
                    page.wait_for_function("() => location.search.includes('measure=revenue')")
                    expect(page.locator("#pv-question")).to_be_visible(timeout=60000)
                    page.get_by_role("button", name="Profit", exact=True).click()
                    page.wait_for_function("() => !location.search.includes('measure=revenue')")
                    print(f"PASS {role}: contextual filter, active chip, More filters and measure switch")
                if name == accounts[0][0]:
                    first_metric = page.locator(".metric-banner__metric").first
                    first_metric.focus()
                    page.keyboard.press("Enter")
                    expect(page.get_by_role("dialog")).to_be_visible()
                    page.keyboard.press("Escape")
                    expect(page.get_by_role("dialog")).to_have_count(0)
                    theme_button = page.locator(
                        'button[aria-label="Use dark theme"], button[aria-label="Use light theme"]')
                    if theme_button.get_attribute("aria-label") == "Use light theme":
                        page.screenshot(path=str(artifacts / "metric-banners-desktop-dark.png"), full_page=True)
                        theme_button.click()
                    page.screenshot(path=str(artifacts / "metric-banners-desktop-light.png"), full_page=True)
                    theme_button.click()
                    page.screenshot(path=str(artifacts / "metric-banners-desktop-dark.png"), full_page=True)
                    theme_button.click()
                    page.set_viewport_size({"width": 390, "height": 844})
                    banners_fit = page.evaluate("""() => {
                      const group=document.querySelector('.metric-banners');
                      if (!group) return false;
                      const edge=group.getBoundingClientRect().right;
                      return group.scrollWidth <= group.clientWidth + 1 &&
                        [...group.querySelectorAll('.metric-banner')]
                          .every(e => e.getBoundingClientRect().right <= edge + 1);
                    }""")
                    assert banners_fit
                    page.screenshot(path=str(artifacts / "metric-banners-mobile.png"), full_page=True)
                    page.set_viewport_size({"width": 1440, "height": 1000})
                if role == "ae":
                    page.goto(base + "?as=executive&id=north-america&page=performance")
                    expect(page.locator("#pv-question")).to_be_visible(timeout=60000)
                    assert "page=my-day" in page.url and "as=" not in page.url
                    page.reload()
                    expect(page.locator(".who-name")).to_have_text(name, timeout=60000)
                    expect(page.locator("#pv-question")).to_be_visible(timeout=60000)
                page.locator(".who").click()
                expect(page.get_by_role("button", name="Sign out")).to_be_visible()
                if name == accounts[0][0]:
                    page.screenshot(path=str(artifacts / "signed-in-profile.png"), full_page=True)
                page.get_by_role("button", name="Sign out").click()
                expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()
                assert page.evaluate("sessionStorage.getItem('ntt.session.v2')") is None
                assert page.locator(".who").count() == 0
                print(f"PASS {name}: login, scope, landing and logout")
            # Keyboard sign-in restores an authorized deep link and its filter.
            page.goto(base + "?page=my-deals&stage=Qualification")
            expect(page.get_by_label("Email address")).to_be_visible()
            page.get_by_label("Email address").focus()
            page.keyboard.type(accounts[0][1])
            page.keyboard.press("Tab")
            page.keyboard.type(accounts[0][2])
            page.keyboard.press("Enter")
            expect(page.locator("#pv-question")).to_be_visible(timeout=60000)
            assert "page=my-deals" in page.url and "stage=Qualification" in page.url
            page.evaluate("""() => {
              const s=JSON.parse(sessionStorage.getItem('ntt.session.v2'));
              s.expiresAt='2000-01-01T00:00:00Z';
              sessionStorage.setItem('ntt.session.v2', JSON.stringify(s));
            }""")
            page.reload()
            expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()
            assert page.locator(".who").count() == 0
            print("PASS keyboard sign-in, allowed deep link and expired-session gate", flush=True)
            # Server outage is distinct from wrong credentials and retry remains possible.
            page.route("**/api/auth/login", lambda route: route.abort())
            page.get_by_label("Email address").fill(accounts[0][1])
            page.get_by_label("Password", exact=True).fill(accounts[0][2])
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("could not reach the server")
            page.unroute("**/api/auth/login")
            assert not errors, errors
            browser.close()
            print("PASS mobile layout, refresh, unauthorized deep links, invalid credentials, connection error and no browser exceptions")
            print(f"Screenshots: {artifacts}")
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


if __name__ == "__main__":
    main()
