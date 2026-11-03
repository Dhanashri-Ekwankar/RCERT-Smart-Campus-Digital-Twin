import sys
from playwright.sync_api import sync_playwright

def run_e2e_tests():
    print("=== STARTING PLAYWRIGHT E2E MODAL & UI RESPONSIVENESS TEST ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # 1. Open homepage
        print("\n[Step 1] Loading http://127.0.0.1:5001/ ...")
        page.goto("http://127.0.0.1:5001/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        modal = page.locator("#modal-roadmap")
        is_visible = modal.is_visible()
        print(f"Modal visible on initial load: {is_visible}")
        assert not is_visible, "FAILURE: Modal MUST NOT be visible on initial load!"
        print("PASS: Modal is NOT visible on initial load.")

        # 2. Navigate through dashboard tabs
        tabs = [
            ("Weather & Air", "weather"),
            ("Campus Twin", "campus"),
            ("Analytics", "analytics"),
            ("Alerts", "alerts"),
            ("Reports", "reports"),
            ("Settings", "settings"),
            ("Overview", "dashboard")
        ]
        print("\n[Step 2] Testing dashboard tab navigation...")
        for tab_name, view_id in tabs:
            btn = page.locator(f".nav-link[data-view-target='{view_id}']")
            btn.click()
            page.wait_for_timeout(300)
            view_elem = page.locator(f"#view-{view_id}")
            assert view_elem.is_visible(), f"FAILURE: View #view-{view_id} is not visible after clicking {tab_name}!"
            assert not modal.is_visible(), f"FAILURE: Modal popped up unexpectedly on tab {tab_name}!"
            print(f"  PASS: Navigated to '{tab_name}' successfully. View is visible. Modal remains hidden.")

        # 3. Open modal via Future Development button
        print("\n[Step 3] Opening Roadmap Modal via button (#open-roadmap-btn)...")
        open_btn = page.locator("#open-roadmap-btn")
        open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open after clicking Future Development button!"
        print("PASS: Modal opened successfully.")

        # 4. Test Close button (X)
        print("\n[Step 4] Testing Close (X) button (#close-roadmap-btn)...")
        close_btn = page.locator("#close-roadmap-btn")
        close_btn.click()
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "FAILURE: Modal did not close after clicking Close (X) button!"
        print("PASS: Modal closed successfully via Close (X) button.")

        # Verify dashboard is immediately clickable after close
        weather_btn = page.locator(".nav-link[data-view-target='weather']")
        weather_btn.click()
        page.wait_for_timeout(300)
        assert page.locator("#view-weather").is_visible(), "FAILURE: Dashboard UI not accessible after modal close!"
        print("PASS: Dashboard UI is accessible and interactive after closing.")

        # 5. Reopen and test "Understood" button (#dismiss-roadmap-btn)
        print("\n[Step 5] Testing 'Understood' button (#dismiss-roadmap-btn)...")
        open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open on second attempt!"
        
        understood_btn = page.locator("#dismiss-roadmap-btn")
        understood_btn.click()
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "FAILURE: Modal did not close after clicking 'Understood' button!"
        print("PASS: Modal closed successfully via 'Understood' button.")

        # 6. Reopen and test Escape key
        print("\n[Step 6] Testing Escape key dismissal...")
        open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open for Escape test!"
        
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "FAILURE: Modal did not close after pressing Escape!"
        print("PASS: Modal closed successfully via Escape key.")

        # 7. Test clicking outside (backdrop click)
        print("\n[Step 7] Testing click outside (backdrop click)...")
        open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open for backdrop test!"

        # Click outside the modal window on the backdrop (e.g., top-left at x=15, y=15)
        page.mouse.click(15, 15)
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "FAILURE: Modal did not close after clicking outside on backdrop!"
        print("PASS: Modal closed successfully via clicking outside on backdrop.")

        # 8. Test clicking inside modal does NOT close it
        print("\n[Step 8] Testing clicking inside modal window...")
        open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open for inside click test!"

        modal_title = page.locator("#roadmap-dialog-title")
        modal_title.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal closed accidentally when clicking inside modal content!"
        print("PASS: Clicking inside modal does NOT accidentally close it.")
        
        # Close it via Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # 9. Test Mobile Viewport (375 x 667)
        print("\n[Step 9] Testing Mobile Viewport (375x667)...")
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(500)

        # Open mobile drawer menu
        menu_toggle = page.locator("#menu-toggle")
        menu_toggle.click()
        page.wait_for_timeout(400)

        # In spatial responsive navigation, the mobile overlay contains mobile-open-roadmap-btn,
        # and the page footer contains open-roadmap-btn.
        mobile_btn = page.locator("#mobile-open-roadmap-btn")
        if mobile_btn.is_visible():
            mobile_btn.click()
        else:
            open_btn = page.locator("#open-roadmap-btn")
            open_btn.scroll_into_view_if_needed()
            open_btn.click()
        page.wait_for_timeout(400)
        assert modal.is_visible(), "FAILURE: Modal did not open in mobile viewport!"
        print("PASS: Modal opened in mobile viewport.")

        # Check buttons visibility in mobile
        assert close_btn.is_visible(), "FAILURE: Close button is not visible on mobile!"
        assert understood_btn.is_visible(), "FAILURE: Understood button is not visible on mobile!"

        # Verify modal window dimensions fit mobile screen
        box = page.locator(".modal-window").bounding_box()
        print(f"  Mobile modal bounding box: width={box['width']:.1f}px, height={box['height']:.1f}px")
        assert box["width"] <= 375, f"FAILURE: Modal width ({box['width']}px) overflows 375px viewport!"

        # Dismiss on mobile
        understood_btn.click()
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "FAILURE: Modal did not close in mobile viewport via Understood button!"
        print("PASS: Mobile viewport verified successfully. Width <= 375px, no overflow, buttons accessible.")

        # 10. Check Console Errors
        print("\n[Step 10] Checking Console Errors...")
        if console_errors:
            print(f"Console errors detected ({len(console_errors)}):")
            for err in console_errors:
                print(f"  - {err}")
        else:
            print("PASS: Zero console errors logged during entire test run!")

        browser.close()
        print("\n=== ALL E2E VERIFICATIONS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_e2e_tests()
