from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:5001/", wait_until="networkidle")

    clipped_found = []
    for w in range(1120, 1600, 20):
        page.set_viewport_size({"width": w, "height": 800})
        page.wait_for_timeout(50)

        res = page.evaluate('''() => {
            const navLinks = [...document.querySelectorAll(".nexus-nav-capsule .nav-link")];
            const clipped = [];
            for (const btn of navLinks) {
                const text = btn.querySelector(".nav-text")?.textContent || "";
                if (btn.scrollWidth > btn.clientWidth + 1) {
                    clipped.push({ text, scrollW: btn.scrollWidth, clientW: btn.clientWidth });
                }
            }
            return clipped;
        }''')
        if res:
            clipped_found.append((w, res))

    print(f"Clipped instances across 1120px-1600px: {len(clipped_found)}")
    for w, c in clipped_found:
        print(f"  At width {w}px: {c}")

    browser.close()
