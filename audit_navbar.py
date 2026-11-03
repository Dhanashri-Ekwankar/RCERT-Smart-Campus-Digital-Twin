import os
from playwright.sync_api import sync_playwright

def inspect_viewports():
    os.makedirs("navbar_audit_screenshots", exist_ok=True)
    viewports = [
        ("1920x1080", 1920, 1080),
        ("1600x900",  1600, 900),
        ("1440x900",  1440, 900),
        ("1366x768",  1366, 768),
        ("1280x800",  1280, 800),
        ("1140x800",  1140, 800),
        ("1024x768",  1024, 768),
        ("768x1024",  768, 1024),
        ("390x844",   390, 844),
        ("360x800",   360, 800)
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.goto("http://127.0.0.1:5001/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        for name, w, h in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(300)

            # Check overlaps and bounding boxes
            data = page.evaluate('''() => {
                const navBar = document.querySelector(".spatial-nexus-bar");
                const identity = document.querySelector(".nexus-identity-pod");
                const navCapsule = document.querySelector(".nexus-nav-capsule");
                const telemetry = document.querySelector(".nexus-telemetry-pod");
                const navLinks = [...document.querySelectorAll(".nexus-nav-capsule .nav-link")];
                const dock = document.querySelector(".mobile-spatial-dock");

                const idRect = identity ? identity.getBoundingClientRect() : null;
                const capRect = navCapsule && window.getComputedStyle(navCapsule).display !== "none" ? navCapsule.getBoundingClientRect() : null;
                const telemRect = telemetry ? telemetry.getBoundingClientRect() : null;
                const dockVisible = dock ? window.getComputedStyle(dock).display !== "none" : false;

                const linkData = navLinks.map(btn => {
                    const r = btn.getBoundingClientRect();
                    const text = btn.querySelector(".nav-text")?.textContent || "";
                    const scrollW = btn.scrollWidth;
                    const clientW = btn.clientWidth;
                    return {
                        text,
                        w: r.width,
                        clipped: scrollW > clientW + 1
                    };
                });

                let overlapIdCapsule = false;
                let overlapCapsuleTelem = false;
                if (idRect && capRect) {
                    overlapIdCapsule = capRect.left < idRect.right;
                }
                if (capRect && telemRect) {
                    overlapCapsuleTelem = capRect.right > telemRect.left;
                }

                return {
                    dockVisible,
                    capsuleVisible: !!capRect,
                    overlapIdCapsule,
                    overlapCapsuleTelem,
                    linkData,
                    navBarWidth: navBar ? navBar.getBoundingClientRect().width : 0
                };
            }''')

            # Screenshot
            page.screenshot(path=f"navbar_audit_screenshots/nav_{name}.png")
            print(f"Viewport {name:9s}: DesktopNav={data['capsuleVisible']}, MobileDock={data['dockVisible']}, OverlapBrand={data['overlapIdCapsule']}, OverlapTelem={data['overlapCapsuleTelem']}")
            if data['capsuleVisible']:
                clipped = [l['text'] for l in data['linkData'] if l['clipped']]
                total_w = sum(l['w'] for l in data['linkData'])
                print(f"   Links total width: {total_w:.1f}px. Clipped links: {clipped if clipped else 'None'}")

        browser.close()

if __name__ == "__main__":
    inspect_viewports()
