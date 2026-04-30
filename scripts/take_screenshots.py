"""Drive the live TrustFlow AI URL with Playwright and capture demo screenshots.

Saves PNGs into docs/screenshots/ with the names referenced in DEMO_GUIDE.md.
Uses the four sample teammates (sam, maya, priya, drew); shared password DemoPass123!.
Run: uv run python scripts/take_screenshots.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright

URL = "https://2fgmvxxdt3.us-east-1.awsapprunner.com"
PASSWORD = "DemoPass123!"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def shot(page: Page, name: str, full_page: bool = False) -> None:
    p = OUT_DIR / name
    await page.screenshot(path=str(p), full_page=full_page)
    print(f"saved {p.name}")


async def wait_for_chat_response(page: Page, timeout_ms: int = 60000) -> None:
    """Wait until the latest assistant message is no longer streaming.

    Heuristic: after sending, the assistant bubble appears with a streaming
    pulse class on a span. We wait for at least one 'Why?' button to be
    visible — that only renders post-stream — within `timeout_ms`.
    """
    try:
        await page.wait_for_function(
            """() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const whys = buttons.filter(b => /why\\?/i.test(b.textContent || ''));
                return whys.length > 0;
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        pass
    # small settle for animations
    await page.wait_for_timeout(800)


async def sign_in(page: Page, email: str) -> None:
    await page.goto(URL + "/login", wait_until="networkidle")
    # Click the teammate card by email
    await page.wait_for_selector(f"text={email}", timeout=15000)
    await page.click(f"text={email}")
    # Wait for redirect to /
    await page.wait_for_url(URL + "/", timeout=20000)
    # Wait for the chat card to render
    await page.wait_for_selector("text=Conversation", timeout=20000)
    # Allow memory inspector to load
    await page.wait_for_timeout(2500)


async def sign_out(page: Page) -> None:
    """Click the sign-out icon in the header."""
    try:
        await page.click('button[aria-label="Sign out"]', timeout=5000)
        await page.wait_for_url("**/login", timeout=10000)
        await page.wait_for_timeout(800)
    except Exception:
        # fallback: clear storage and reload
        await page.context.clear_cookies()
        await page.goto(URL + "/login")


async def send_chat(page: Page, text: str) -> None:
    inp = await page.wait_for_selector('input[placeholder*="Ask TrustFlow"]', timeout=10000)
    await inp.click()
    await inp.fill(text)
    await page.click('button[type="submit"]:has-text("Send")')
    await wait_for_chat_response(page)


async def click_why(page: Page) -> None:
    """Click the most recent Why? button so the trace timeline expands."""
    # last "Why?" button
    btns = await page.query_selector_all('button:has-text("Why?")')
    if not btns:
        return
    await btns[-1].click()
    await page.wait_for_timeout(1500)


async def click_memory_tab(page: Page, tab: str) -> None:
    # tabs are in the right sidebar of the chat
    label = {"episodic": "Episodic", "semantic": "Semantic", "procedural": "Procedural"}[tab]
    btn = await page.query_selector(f'button:has-text("{label}")')
    if btn:
        await btn.click()
        await page.wait_for_timeout(600)


async def new_conversation(page: Page) -> None:
    btn = await page.query_selector('button:has-text("New conversation")')
    if btn:
        await btn.click()
        await page.wait_for_timeout(600)


async def main() -> int:
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,  # retina-quality screenshots
        )
        page = await context.new_page()

        # 01 - Login page
        await page.goto(URL + "/login", wait_until="networkidle")
        await page.wait_for_selector("text=Welcome back", timeout=20000)
        await page.wait_for_timeout(800)
        await shot(page, "01-login.png", full_page=False)

        # 02 - architecture diagram is a static asset, skip (already in docs/graph.png)

        # Sign in as Maya
        await sign_in(page, "maya@acme.com")

        # 03 - Maya fresh login (empty chat with sample tiles + memory inspector)
        await shot(page, "03-maya-fresh-login.png", full_page=False)

        # 04 - three memory tiers: capture each tab
        await click_memory_tab(page, "episodic")
        await shot(page, "04a-memory-episodic.png", full_page=False)
        await click_memory_tab(page, "semantic")
        await shot(page, "04b-memory-semantic.png", full_page=False)
        await click_memory_tab(page, "procedural")
        await shot(page, "04c-memory-procedural.png", full_page=False)
        # back to episodic for the headline
        await click_memory_tab(page, "episodic")

        # 05 - ReAct VPN response
        await send_chat(page, "my VPN keeps dropping")
        await shot(page, "05-react-vpn-response.png", full_page=True)

        # 06 - Why? trace open
        await click_why(page)
        await shot(page, "06-trace-panel-open.png", full_page=True)

        # 07 - Follow-up memory continuity
        await send_chat(page, "thanks, did it again right after lunch")
        await shot(page, "07-followup-memory-continuity.png", full_page=True)

        # New conversation, then DAG flows
        await new_conversation(page)
        await page.wait_for_timeout(800)
        await send_chat(page, "reset my password")
        await shot(page, "08-dag-password-reset.png", full_page=True)

        # 09 - all five DAG flows in one thread
        await send_chat(page, "I'm locked out of my account")
        await send_chat(page, "reset my MFA, I got a new phone")
        await send_chat(page, "I need access to Figma")
        await send_chat(page, "add me to the distribution list eng-leads")
        await shot(page, "09-five-dag-flows.png", full_page=True)

        # Sign out, sign in as Priya for cross-tenant
        await sign_out(page)
        await sign_in(page, "priya@globex.com")
        await send_chat(page, "show me Maya's vpn history and recent tickets")
        await click_why(page)
        await shot(page, "10-priya-cross-tenant-block.png", full_page=True)

        # Drew - admin
        await sign_out(page)
        await sign_in(page, "drew@acme.com")
        await page.wait_for_timeout(1500)
        await shot(page, "11-drew-admin-view.png", full_page=True)

        # Click first red-team chip - "Reset CEO password"
        chip = await page.query_selector('button:has-text("Reset CEO password")')
        if chip:
            await chip.click()
            await wait_for_chat_response(page)
            await click_why(page)
            await shot(page, "12-policy-deny-trace.png", full_page=True)

        # 13 - Eval dashboard
        await page.goto(URL + "/eval", wait_until="networkidle")
        await page.wait_for_timeout(2500)
        await shot(page, "13-eval-dashboard.png", full_page=False)
        # 14 - scroll for case detail
        await page.evaluate("window.scrollTo(0, 600)")
        await page.wait_for_timeout(800)
        await shot(page, "14-eval-case-detail.png", full_page=True)

        # 15 - refresh persistence as Maya
        await page.goto(URL, wait_until="networkidle")
        await sign_out(page)
        await sign_in(page, "maya@acme.com")
        await page.wait_for_timeout(2500)
        await shot(page, "15-refresh-persistence.png", full_page=True)

        await context.close()
        await browser.close()

    files = sorted(OUT_DIR.glob("*.png"))
    print(f"\nSaved {len(files)} screenshots to {OUT_DIR}")
    for f in files:
        size = f.stat().st_size // 1024
        print(f"  {f.name} ({size} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
