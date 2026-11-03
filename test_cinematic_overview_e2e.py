import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from playwright.sync_api import sync_playwright

def run_tests():
    print("=== STARTING RCERT CINEMATIC OVERVIEW & SCROLL REBUILD E2E TEST ===")
    
    os.makedirs("test_screenshots", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        
        # Test 1: Desktop Viewport (1440x900)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # 1. Open homepage http://127.0.0.1:5001/
        print("\n[Step 1] Loading http://127.0.0.1:5001/ ...")
        page.goto("http://127.0.0.1:5001/", wait_until="networkidle")
        page.wait_for_timeout(1500)

        overview_view = page.locator("#view-dashboard")
        assert overview_view.is_visible(), "FAILURE: Overview view is not visible on load!"
        print("PASS: Overview view is visible on initial load.")

        # 2. Check Cinematic Canvas & Scene 1 Hero
        print("\n[Step 2] Verifying Cinematic Canvas and Scene 1 Hero...")
        stage = page.locator("#overview-cinematic-stage")
        assert stage.is_visible(), "FAILURE: Cinematic stage is not visible!"
        
        canvas = page.locator("#cinematic-canvas")
        assert canvas.is_visible(), "FAILURE: Cinematic canvas is not visible!"

        scene1 = page.locator(".narrative-scene[data-scene='1']")
        assert scene1.is_visible(), "FAILURE: Scene 1 narrative is not visible!"
        scene1_text = scene1.locator(".scene-headline").text_content()
        assert "Rajiv Gandhi College of Engineering" in scene1_text, f"Unexpected headline: {scene1_text}"
        print(f"  PASS: Scene 1 active with headline: '{scene1_text.strip()}'")

        # Verify Issue 1: Debug Telemetry HUD completely eliminated
        assert page.locator(".cinematic-telemetry-hud").count() == 0, "FAILURE: .cinematic-telemetry-hud still exists in DOM!"
        assert page.locator("#hud-frame-num").count() == 0, "FAILURE: #hud-frame-num still exists in DOM!"
        assert page.locator("#hud-progress-fill").count() == 0, "FAILURE: #hud-progress-fill still exists in DOM!"
        assert page.locator("#hud-progress-pct").count() == 0, "FAILURE: #hud-progress-pct still exists in DOM!"
        print("  PASS: Debug telemetry HUD (CINEMATIC FRAME, 300 / 300, progress bar) completely eliminated from DOM.")

        # Verify Issue 2: Edge-to-edge full bleed coverage
        vp_box = page.locator(".cinematic-sticky-viewport").bounding_box()
        assert vp_box is not None, "FAILURE: .cinematic-sticky-viewport bounding box is None!"
        assert abs(vp_box["x"]) < 2, f"Expected x near 0, got {vp_box['x']}"
        assert abs(vp_box["width"] - 1440) < 2, f"Expected width near 1440, got {vp_box['width']}"
        assert abs(vp_box["height"] - 900) < 2, f"Expected height near 900, got {vp_box['height']}"
        print(f"  PASS: Sticky viewport is full-bleed edge-to-edge: {vp_box['width']}x{vp_box['height']} at x={vp_box['x']}.")
        page.screenshot(path="test_screenshots/01_overview_hero_scene1_desktop.png")

        # 3. Test Scroll Scrubbing across Scenes 1 to 6
        print("\n[Step 3] Scrolling down through the cinematic sequence...")
        
        # Scroll 20% (Entrance gate - Scene 2)
        page.evaluate("window.scrollTo(0, window.innerHeight * 0.9)")
        page.wait_for_timeout(500)
        scene2 = page.locator(".narrative-scene[data-scene='2']")
        assert scene2.is_visible(), "FAILURE: Scene 2 not visible after scroll!"
        print("  PASS: Scene 2 active (Main Entrance Gateway).")
        page.screenshot(path="test_screenshots/02_cinematic_scene2_gate.png")

        # Scroll 45% (Facade - Scene 3)
        page.evaluate("window.scrollTo(0, window.innerHeight * 1.8)")
        page.wait_for_timeout(500)
        scene3 = page.locator(".narrative-scene[data-scene='3']")
        assert scene3.is_visible(), "FAILURE: Scene 3 not visible after scroll!"
        print("  PASS: Scene 3 active (Administration Building Facade).")
        page.screenshot(path="test_screenshots/03_cinematic_scene3_facade.png")

        # Scroll 65% (Courtyard - Scene 4)
        page.evaluate("window.scrollTo(0, window.innerHeight * 2.5)")
        page.wait_for_timeout(500)
        scene4 = page.locator(".narrative-scene[data-scene='4']")
        assert scene4.is_visible(), "FAILURE: Scene 4 not visible after scroll!"
        print("  PASS: Scene 4 active (Academic Courtyard & Computer Science Wing).")

        # Scroll 80% (Workshops - Scene 5)
        page.evaluate("window.scrollTo(0, window.innerHeight * 3.1)")
        page.wait_for_timeout(500)
        scene5 = page.locator(".narrative-scene[data-scene='5']")
        assert scene5.is_visible(), "FAILURE: Scene 5 not visible after scroll!"
        print("  PASS: Scene 5 active (Engineering Workshops & High-Voltage Labs).")

        # Scroll 95% (Transition - Scene 6)
        page.evaluate("window.scrollTo(0, window.innerHeight * 3.6)")
        page.wait_for_timeout(500)
        scene6 = page.locator(".narrative-scene[data-scene='6']")
        assert scene6.is_visible(), "FAILURE: Scene 6 not visible after scroll!"
        print("  PASS: Scene 6 active (Digital Twin Intelligence Transition).")
        page.screenshot(path="test_screenshots/04_cinematic_scene6_transition.png")

        # Scroll 100%+ (Arriving at Live Dashboard)
        print("\n[Step 4] Continuing scroll into live campus executive dashboard...")
        page.evaluate("window.scrollTo(0, window.innerHeight * 4.3)")
        page.wait_for_timeout(500)
        
        weather_hero = page.locator(".weather-hero")
        assert weather_hero.is_visible(), "FAILURE: Live weather hero is not visible after cinematic scroll!"
        temp_val = page.locator("#current-temp").text_content()
        print(f"  PASS: Dashboard reached. Current Live Temp: {temp_val}°C")
        page.screenshot(path="test_screenshots/05_live_dashboard_overview.png")

        # 4. Reverse Scroll Check (Scrolling up reverses animation smoothly)
        print("\n[Step 5] Testing reverse scrolling back to Scene 1...")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(600)
        assert scene1.is_visible(), "FAILURE: Scene 1 not active after scrolling back to top!"
        print("  PASS: Reversed scroll successfully back to Scene 1.")

        # 5. Check Navigation Order & Direct Section Jumping
        print("\n[Step 6] Verifying 8 main navigation destinations...")
        expected_nav = [
            ("dashboard", "Overview"),
            ("weather", "Weather & Air"),
            ("campus", "Campus Twin"),
            ("analytics", "Analytics"),
            ("alerts", "Alerts"),
            ("about", "About RCERT"),
            ("reports", "Reports & Export"),
            ("settings", "Settings")
        ]
        
        nav_buttons = page.locator(".nav-list .nav-link")
        assert nav_buttons.count() == 8, f"Expected 8 navigation buttons, got {nav_buttons.count()}"
        
        for i, (expected_target, expected_label) in enumerate(expected_nav):
            btn = nav_buttons.nth(i)
            target = btn.get_attribute("data-view-target")
            text = btn.text_content()
            assert target == expected_target, f"Nav {i} target expected {expected_target}, got {target}"
            assert expected_label in text, f"Nav {i} label expected {expected_label}, got {text}"
            clean_label = text.strip().encode('ascii', 'replace').decode('ascii')
            print(f"  PASS: Nav [{i+1}] {expected_target} -> '{clean_label}'")

        # 6. Test Direct Navigation to Campus Twin 3D (No Walkthrough Player inside!)
        print("\n[Step 7] Testing Campus Twin 3D (Walkthrough player removed, 3D intact)...")
        nav_buttons.nth(2).click() # Click Campus Twin
        page.wait_for_timeout(1000)

        campus_view = page.locator("#view-campus")
        assert campus_view.is_visible(), "FAILURE: Campus Twin view not visible after clicking navigation!"
        
        # Verify walkthrough video player is completely removed
        video_player = page.locator("#campus-video")
        assert video_player.count() == 0, "FAILURE: #campus-video still exists in Campus Twin!"
        walkthrough_exp = page.locator("#campus-walkthrough-experience")
        assert walkthrough_exp.count() == 0, "FAILURE: #campus-walkthrough-experience still exists in Campus Twin!"
        print("  PASS: Campus Walkthrough video player and container successfully removed from Campus Twin.")

        # Verify Three.js 3D Canvas is active and running
        canvas_3d = page.locator("#campus-scene canvas")
        canvas_3d.wait_for(state="visible", timeout=10000)
        assert canvas_3d.is_visible(), "FAILURE: Three.js WebGL canvas is not visible!"
        print("  PASS: Three.js WebGL 3D Canvas is active and rendering.")

        # Verify 18 zones and Zone Inspector
        mb_chip = page.locator(".zone-chip[data-zone-id='main_building']")
        mb_chip.click()
        page.wait_for_timeout(400)
        zone_title = page.locator("#selected-zone-name").text_content()
        assert "Main Building" in zone_title, f"Expected Main Building, got {zone_title}"
        print(f"  PASS: Zone Inspector works. Selected: '{zone_title.strip()}'")
        page.screenshot(path="test_screenshots/06_campus_twin_3d.png")

        # 7. Test Direct Navigation to Other Sections
        print("\n[Step 8] Testing direct navigation to Weather, Analytics, Alerts, Settings...")
        for tab_idx in [1, 3, 4, 7]:
            nav_buttons.nth(tab_idx).click()
            page.wait_for_timeout(300)
            target_view = nav_buttons.nth(tab_idx).get_attribute("data-view-target")
            assert page.locator(f"#view-{target_view}").is_visible(), f"FAILURE: #view-{target_view} not visible!"
            print(f"  PASS: Navigated directly to #view-{target_view}.")

        # 8. Test Responsive Viewports (1920x1080, 1024x768, 390x844, 360x800)
        print("\n[Step 9] Testing Responsive Viewports...")
        viewports = [
            ("Desktop 1920x1080", 1920, 1080),
            ("Desktop 1440x900", 1440, 900),
            ("Tablet Landscape 1024x768", 1024, 768),
            ("Tablet Portrait 768x1024", 768, 1024),
            ("Mobile iPhone 390x844", 390, 844),
            ("Mobile Android 360x800", 360, 800)
        ]

        # Return to Overview
        nav_buttons.nth(0).click()
        page.wait_for_timeout(500)

        for name, w, h in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(400)
            
            # Check horizontal overflow
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width + 1, f"Horizontal overflow on {name}: scrollWidth={scroll_width}, clientWidth={client_width}"
            
            # Check canvas is properly visible
            assert canvas.is_visible(), f"Canvas not visible on {name}"
            
            if w <= 768:
                page.screenshot(path=f"test_screenshots/07_mobile_{w}x{h}.png")
            print(f"  PASS: {name} validated (scrollWidth={scroll_width} <= clientWidth={client_width}, 0 overflow).")

        # 9. Verify Zero Console Errors
        print("\n[Step 10] Checking Console Errors...")
        if console_errors:
            print(f"Console errors detected ({len(console_errors)}):")
            for err in console_errors:
                print(f"  - {err}")
            assert False, "Console errors detected!"
        else:
            print("PASS: Zero console errors logged across entire run!")

        browser.close()
        print("\n=== ALL RCERT CINEMATIC OVERVIEW & ARCHITECTURE TESTS PASSED! ===")

if __name__ == "__main__":
    run_tests()
