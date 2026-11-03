import os
from playwright.sync_api import sync_playwright

def capture_nav_viewports():
    dest_dir = r"C:\Users\samya\.gemini\antigravity\brain\79adb0ac-7ca7-4c2c-b026-74f62a78576b"
    os.makedirs(dest_dir, exist_ok=True)
    
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
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            
            out_path = os.path.join(dest_dir, f"navbar_verified_{name}.png")
            page.screenshot(path=out_path)
            print(f"Captured: {out_path}")

        browser.close()

if __name__ == "__main__":
    capture_nav_viewports()
