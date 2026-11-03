import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright

def run_e2e_tests():
    print("=== STARTING RCERT CINEMATIC SCROLL & DASHBOARD TRANSITION E2E TEST ===")
    os.makedirs("test_screenshots", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # 1. Test A: Initial Page Load & Cinematic Hero
        print("\n[Test A] Initial Page Load (http://127.0.0.1:5001/)...")
        page.goto("http://127.0.0.1:5001/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Check Overview visibility
        overview_view = page.locator("#view-dashboard")
        assert overview_view.is_visible(), "FAIL: Overview view not visible!"
        
        # Verify sticky viewport coordinates at scroll=0
        vp_box = page.locator(".cinematic-sticky-viewport").bounding_box()
        assert vp_box is not None, "FAIL: Sticky viewport bounding box is None!"
        print(f"  Sticky Viewport at start: x={vp_box['x']:.0f}, y={vp_box['y']:.0f}, w={vp_box['width']:.0f}, h={vp_box['height']:.0f}")
        assert abs(vp_box['y']) <= 1.0, f"FAIL: Expected sticky viewport y near 0, got {vp_box['y']}"

        # Verify Scene 1 active
        scene1 = page.locator(".narrative-scene[data-scene='1']")
        assert scene1.is_visible(), "FAIL: Scene 1 not active on load!"
        frame1 = page.locator("#cinematic-canvas").get_attribute("data-frame") or "1"
        print(f"  PASS: Scene 1 active, Frame: {frame1}")
        page.screenshot(path="test_screenshots/01_cinematic_start.png")

        # 2. Test B: Mid-Animation Progression (Frames & Scenes advance together)
        print("\n[Test B] Mid-Animation Scroll Progression...")
        win_h = 900
        stage_h = page.locator("#overview-cinematic-stage").bounding_box()["height"]
        scrollable = stage_h - win_h
        print(f"  Stage Height: {stage_h}px, Scrollable Pin Distance: {scrollable}px ({scrollable/win_h:.1f}vh)")

        checkpoints = [
            (0.20, "2", "Scene 2 Gateway"),
            (0.40, "3", "Scene 3 Facade"),
            (0.60, "4", "Scene 4 Quadrangle"),
            (0.80, "5", "Scene 5 Engineering"),
            (0.95, "6", "Scene 6 Operational Center")
        ]

        for pct, expected_scene, label in checkpoints:
            target_scroll = scrollable * pct
            page.evaluate(f"window.scrollTo(0, {target_scroll})")
            page.wait_for_timeout(300)

            cur_sticky = page.locator(".cinematic-sticky-viewport").bounding_box()
            assert abs(cur_sticky["y"]) <= 1.0, f"FAIL: Pinned viewport unpinned early! y={cur_sticky['y']}"

            cur_frame = int(page.locator("#cinematic-canvas").get_attribute("data-frame") or "1")
            active_scene = page.evaluate("document.querySelector('.narrative-scene.is-active')?.dataset.scene || 'none'")
            print(f"  Scroll {pct*100:4.0f}% ({target_scroll:5.0f}px): Frame={cur_frame:3d}/300 | Active Scene={active_scene} ({label}) | Sticky y={cur_sticky['y']:.0f}")
            assert active_scene == expected_scene, f"FAIL: Expected scene {expected_scene}, got {active_scene}"

            if pct == 0.40:
                page.screenshot(path="test_screenshots/02_cinematic_middle.png")

        # 3. Test C: Sequence Completion at 100% Progress
        print("\n[Test C] Sequence Completion at 100% (Final Frame 300)...")
        page.evaluate(f"window.scrollTo(0, {scrollable})")
        page.wait_for_timeout(400)

        final_frame = int(page.locator("#cinematic-canvas").get_attribute("data-frame") or "1")
        assert final_frame == 300, f"FAIL: Expected final frame 300, got {final_frame}"
        scene6 = page.locator(".narrative-scene[data-scene='6']")
        assert scene6.is_visible(), "FAIL: Final scene 6 not visible at 100% progress!"
        print(f"  PASS: 100% scroll progress rendered final frame 300 with Scene 6 active.")
        page.screenshot(path="test_screenshots/03_cinematic_final_frame.png")

        # 4. Test D: Immediate Dashboard Entry (No blank screens, no black gap)
        print("\n[Test D] Dashboard Entry Immediately Following Cinematic Exit...")
        # Scroll just 400px past the release point
        page.evaluate(f"window.scrollTo(0, {scrollable + 450})")
        page.wait_for_timeout(400)

        dash_box = page.locator("#overview-dashboard-content").bounding_box()
        weather_hero = page.locator(".weather-hero")
        assert weather_hero.is_visible(), "FAIL: Live weather hero not visible after pin release!"

        print(f"  Dashboard Top Position: y={dash_box['y']:.0f}px (directly in active view)")
        assert dash_box["y"] < win_h * 0.7, f"FAIL: Dashboard is too far down ({dash_box['y']}px), indicating empty gap!"
        
        temp_val = page.locator("#current-temp").text_content()
        cond_val = page.locator("#current-condition").text_content()
        print(f"  PASS: Dashboard live telemetry active: {temp_val} °C, condition: {cond_val}")
        page.screenshot(path="test_screenshots/04_dashboard_transition.png")

        # 5. Test E: Reverse Scroll Check
        print("\n[Test E] Testing Reverse Scrolling from Dashboard back up...")
        # Reverse to middle
        page.evaluate(f"window.scrollTo(0, {scrollable * 0.5})")
        page.wait_for_timeout(300)
        mid_frame = int(page.locator("#cinematic-canvas").get_attribute("data-frame") or "1")
        mid_sticky = page.locator(".cinematic-sticky-viewport").bounding_box()
        assert abs(mid_sticky["y"]) <= 1.0, f"FAIL: Sticky did not re-pin on reverse scroll! y={mid_sticky['y']}"
        assert 130 <= mid_frame <= 170, f"FAIL: Expected mid frame near 150, got {mid_frame}"
        print(f"  PASS: Reversed to middle. Re-pinned at y={mid_sticky['y']:.0f}, Frame={mid_frame}")

        # Reverse to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        top_frame = int(page.locator("#cinematic-canvas").get_attribute("data-frame") or "1")
        assert top_frame == 1, f"FAIL: Expected frame 1 at top, got {top_frame}"
        assert scene1.is_visible(), "FAIL: Scene 1 not restored at top!"
        print(f"  PASS: Reversed back to top. Frame={top_frame}, Scene 1 restored.")

        # 6. Test F: Rapid Scrolling Check
        print("\n[Test F] Testing Rapid Scrolling in both directions...")
        for _ in range(3):
            page.evaluate(f"window.scrollTo(0, {scrollable + 600})")
            page.wait_for_timeout(50)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(50)
        page.wait_for_timeout(300)
        assert scene1.is_visible(), "FAIL: Rapid scroll left sticky state broken!"
        print("  PASS: Rapid scrolling completed without stuck pinned states or glitches.")

        # 7. Test G: Multi-Viewport Responsive Validation
        print("\n[Test G] Multi-Viewport Responsive Validation...")
        viewports = [
            ("Desktop 1920x1080", 1920, 1080),
            ("Desktop 1440x900", 1440, 900),
            ("Tablet Landscape 1024x768", 1024, 768),
            ("Tablet Portrait 768x1024", 768, 1024),
            ("Mobile iPhone 390x844", 390, 844),
            ("Mobile Android 360x800", 360, 800)
        ]

        for name, w, h in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)

            scroll_w = page.evaluate("document.documentElement.scrollWidth")
            client_w = page.evaluate("document.documentElement.clientWidth")
            assert scroll_w <= client_w + 1, f"FAIL: Horizontal overflow on {name}: scrollW={scroll_w}, clientW={client_w}"

            # Check sticky pins at top on this viewport
            page.evaluate("window.scrollTo(0, 300)")
            page.wait_for_timeout(150)
            v_box = page.locator(".cinematic-sticky-viewport").bounding_box()
            assert abs(v_box["y"]) <= 1.0, f"FAIL: Not sticky on {name}: y={v_box['y']}"
            print(f"  PASS: {name} validated (0 overflow, sticky y={v_box['y']:.0f}).")

        # 8. Check for Console Errors
        print("\n[Step 8] Checking Browser Console Errors...")
        if console_errors:
            print(f"Console errors detected ({len(console_errors)}):")
            for err in console_errors:
                print(f"  - {err}")
            assert False, "Console errors detected!"
        else:
            print("  PASS: Zero browser console errors!")

        browser.close()
        print("\n=== ALL CINEMATIC SCROLL & DASHBOARD TRANSITION TESTS PASSED! ===")

if __name__ == "__main__":
    run_e2e_tests()
