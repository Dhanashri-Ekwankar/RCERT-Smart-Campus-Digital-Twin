import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright

def run_tests():
    print("=== STARTING RCERT NEXT-GEN SPATIAL NEXUS NAVIGATION E2E TEST ===")
    
    os.makedirs("test_screenshots/navigation", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        
        # -------------------------------------------------------------
        # Part 1: Desktop Experience (1440x900 & 1920x1080)
        # -------------------------------------------------------------
        print("\n--- PART 1: DESKTOP SPATIAL NEXUS VERIFICATION ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # 1. Load Homepage
        print("[Step 1] Loading http://127.0.0.1:5001/ ...")
        page.goto("http://127.0.0.1:5001/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Verify Spatial Nexus Bar & Identity Module
        nexus_bar = page.locator("#spatial-nexus-bar")
        assert nexus_bar.is_visible(), "FAILURE: #spatial-nexus-bar is not visible on desktop!"
        print("  PASS: Spatial Nexus Bar is pinned and visible.")

        brand_title = page.locator(".brand-title").text_content()
        assert "RCERT" in brand_title, f"Expected 'RCERT', got {brand_title}"
        brand_badge = page.locator(".brand-badge").text_content()
        assert "TWIN 2.0" in brand_badge, f"Expected 'TWIN 2.0', got {brand_badge}"
        system_status = page.locator("#system-label").text_content()
        assert "OPERATIONAL" in system_status or "ONLINE" in system_status or len(system_status) > 0
        print(f"  PASS: Identity Module verified: '{brand_title}' · '{brand_badge}' [{system_status}].")

        # 3. Verify Spatial Capsule & All 8 Navigation Targets
        nav_buttons = page.locator(".nexus-nav-capsule .nav-list .nav-link")
        assert nav_buttons.count() == 8, f"Expected 8 desktop navigation buttons, got {nav_buttons.count()}"

        expected_views = [
            ("dashboard", "Overview"),
            ("weather", "Weather"),
            ("campus", "Campus Twin"),
            ("analytics", "Analytics"),
            ("alerts", "Alerts"),
            ("about", "About RCERT"),
            ("reports", "Reports"),
            ("settings", "Settings")
        ]

        for i, (expected_target, expected_keyword) in enumerate(expected_views):
            btn = nav_buttons.nth(i)
            target = btn.get_attribute("data-view-target")
            text = btn.text_content()
            assert target == expected_target, f"Nav button {i} target expected {expected_target}, got {target}"
            assert expected_keyword in text, f"Nav button {i} text expected keyword {expected_keyword}, got {text}"
            clean_label = text.strip().encode('ascii', 'replace').decode('ascii')
            print(f"  PASS: Nav [{i+1}] {expected_target} -> '{clean_label}'")

        # 4. Verify Active Indicator Laser/Glow Tracking
        glow = page.locator("#nav-indicator-glow")
        assert glow.is_visible(), "FAILURE: #nav-indicator-glow is not visible!"
        glow_box = glow.bounding_box()
        assert glow_box is not None and glow_box["width"] > 30, f"Invalid glow width: {glow_box}"
        print(f"  PASS: Active Indicator Glow Tracker active (width={glow_box['width']:.1f}px, x={glow_box['x']:.1f}px).")

        page.screenshot(path="test_screenshots/navigation/01_desktop_overview_nexus.png")

        # 5. Test Spatial Navigation Jumps & Indicator Sliding
        for test_idx, test_target in [(1, "weather"), (3, "analytics"), (4, "alerts"), (2, "campus")]:
            btn = nav_buttons.nth(test_idx)
            btn.click()
            page.wait_for_timeout(500)
            view_elem = page.locator(f"#view-{test_target}")
            assert view_elem.is_visible(), f"FAILURE: #view-{test_target} is not visible after click!"
            assert btn.get_attribute("class").find("is-active") != -1, f"Nav button {test_target} should have is-active class"
            
            # Verify duplicate indicator is eliminated (single active indicator rule)
            assert page.locator("#page-crumb").count() == 0, "FAILURE: Duplicate #page-crumb still present!"
            print(f"  PASS: Switched to #{test_target} · Single active indicator tracked smoothly · View active.")

        # 6. Verify System Telemetry Status
        status_text = page.locator("#system-label").text_content()
        assert "API CONNECTED" in status_text or "OPERATIONAL" in status_text, f"Invalid system status: {status_text}"
        print(f"  PASS: System Telemetry status is live: {status_text}")

        # 7. Test Presentation Mode Toggle
        pres_btn = page.locator("#presentation-toggle")
        pres_btn.click()
        page.wait_for_timeout(400)
        shell = page.locator("#app-shell")
        assert "is-presentation" in (shell.get_attribute("class") or ""), "FAILURE: is-presentation class not added on #app-shell!"
        page.screenshot(path="test_screenshots/navigation/02_desktop_presentation_mode.png")
        print("  PASS: Presentation Mode toggled on (Spatial bar gracefully tucked).")

        pres_btn.click()
        page.wait_for_timeout(400)
        assert "is-presentation" not in (shell.get_attribute("class") or ""), "FAILURE: is-presentation class not removed!"
        print("  PASS: Presentation Mode toggled off.")

        # 8. Test Phase 2 Roadmap Button
        roadmap_btn = page.locator("#open-roadmap-btn")
        roadmap_btn.click()
        page.wait_for_timeout(300)
        modal = page.locator("#modal-roadmap")
        assert modal.is_visible(), "FAILURE: Phase 2 Roadmap modal did not open on #open-roadmap-btn click!"
        page.locator("#close-roadmap-btn").click()
        page.wait_for_timeout(200)
        assert not modal.is_visible(), "FAILURE: Roadmap modal failed to close via Close button!"
        print("  PASS: Phase 2 Roadmap integrated trigger operates flawlessly.")

        # -------------------------------------------------------------
        # Part 2: Mobile Spatial Dock & Command Overlay Verification
        # -------------------------------------------------------------
        print("\n--- PART 2: MOBILE SPATIAL DOCK & COMMAND OVERLAY ---")
        
        # Test on iPhone 14/15 Viewport (390x844)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)

        # In mobile view, the bottom floating dock should be visible
        mobile_dock = page.locator("#mobile-spatial-dock")
        assert mobile_dock.is_visible(), "FAILURE: #mobile-spatial-dock is not visible on 390x844 mobile!"
        print("  PASS: Mobile Spatial Bottom Dock is visible and active.")

        # Test dock navigation
        dock_weather = page.locator(".mobile-dock-surface button[data-view-target='weather']")
        dock_weather.click()
        page.wait_for_timeout(400)
        assert page.locator("#view-weather").is_visible(), "FAILURE: Weather view not shown via mobile dock!"
        print("  PASS: Mobile dock 1-tap navigation works.")

        # Open Fullscreen Command Overlay via Menu/Hub button
        hub_btn = page.locator("#mobile-hub-btn")
        hub_btn.click()
        page.wait_for_timeout(350)

        overlay = page.locator("#mobile-spatial-overlay")
        assert overlay.is_visible(), "FAILURE: #mobile-spatial-overlay did not open!"
        print("  PASS: Mobile Spatial Command Overlay opened.")

        # Verify all 8 destination tiles in the overlay
        overlay_tiles = page.locator(".overlay-destinations-grid .overlay-tile")
        assert overlay_tiles.count() == 8, f"Expected 8 overlay tiles, got {overlay_tiles.count()}"
        print("  PASS: All 8 spatial destination tiles present in overlay.")

        page.screenshot(path="test_screenshots/navigation/03_mobile_command_overlay.png")

        # Navigate to Campus 3D from overlay
        overlay_campus = page.locator(".overlay-tile[data-view-target='campus']")
        overlay_campus.click()
        page.wait_for_timeout(600)
        assert not overlay.is_visible(), "FAILURE: Overlay did not close after clicking destination tile!"
        assert page.locator("#view-campus").is_visible(), "FAILURE: Campus Twin view not visible after overlay selection!"
        print("  PASS: Overlay tile selection navigates and auto-dismisses cleanly.")

        # Test Escape dismissal of overlay
        page.locator("#menu-toggle").click()
        page.wait_for_timeout(300)
        assert overlay.is_visible(), "FAILURE: Overlay did not open via #menu-toggle!"
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        assert not overlay.is_visible(), "FAILURE: Overlay failed to close on Escape key press!"
        print("  PASS: Mobile overlay dismisses on Escape key.")

        # -------------------------------------------------------------
        # Part 3: Responsive Quality Assurance across 7 Viewports
        # -------------------------------------------------------------
        print("\n--- PART 3: 7-VIEWPORT RESPONSIVE & HORIZONTAL OVERFLOW QA ---")
        
        viewports = [
            ("Desktop 1920x1080", 1920, 1080),
            ("Laptop 1440x900", 1440, 900),
            ("Tablet Landscape 1024x768", 1024, 768),
            ("Tablet Portrait 768x1024", 768, 1024),
            ("Mobile 390x844", 390, 844),
            ("Mobile Compact 360x800", 360, 800),
            ("Mobile Landscape 844x390", 844, 390)
        ]

        # Reset to Overview via JS API
        page.evaluate("window.RCERT.showView('dashboard')")
        page.wait_for_timeout(400)

        for name, w, h in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(400)
            
            # Check horizontal overflow (zero page overflow requirement)
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width + 1, f"Horizontal overflow on {name}: scrollWidth={scroll_width}, clientWidth={client_width}"
            
            page.screenshot(path=f"test_screenshots/navigation/responsive_{w}x{h}.png")
            print(f"  PASS: {name} (scrollWidth={scroll_width} <= clientWidth={client_width}, 0px overflow).")

        # -------------------------------------------------------------
        # Part 4: Console Error Check
        # -------------------------------------------------------------
        print("\n--- PART 4: CONSOLE ERROR AUDIT ---")
        if console_errors:
            print(f"Console errors detected ({len(console_errors)}):")
            for err in console_errors:
                print(f"  - {err}")
            assert False, "Console errors detected during navigation tests!"
        else:
            print("PASS: Zero console errors logged across entire navigation test suite!")

        browser.close()
        print("\n=== ALL RCERT SPATIAL NEXUS NAVIGATION TESTS PASSED! ===")

if __name__ == "__main__":
    run_tests()
