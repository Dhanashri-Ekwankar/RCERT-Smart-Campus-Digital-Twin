from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:5001/", wait_until="networkidle")

    for w in [1440, 1366, 1280, 1200, 1140, 1125, 1115]:
        page.set_viewport_size({"width": w, "height": 800})
        page.wait_for_timeout(200)

        data = page.evaluate('''() => {
            const id = document.querySelector(".nexus-identity-pod").getBoundingClientRect();
            const cap = document.querySelector(".nexus-nav-capsule");
            const telem = document.querySelector(".nexus-telemetry-pod").getBoundingClientRect();
            const isCapVisible = cap && window.getComputedStyle(cap).display !== "none";
            const capRect = isCapVisible ? cap.getBoundingClientRect() : null;

            return {
                idRight: id.right,
                capLeft: capRect ? capRect.left : null,
                capRight: capRect ? capRect.right : null,
                telemLeft: telem.left,
                gapLeft: capRect ? (capRect.left - id.right).toFixed(1) : null,
                gapRight: capRect ? (telem.left - capRect.right).toFixed(1) : null,
                isCapVisible
            };
        }''')
        print(f"Width={w}px: Visible={data['isCapVisible']} | gapLeft={data['gapLeft']}px | gapRight={data['gapRight']}px")

    browser.close()
