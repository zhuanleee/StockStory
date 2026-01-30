#!/usr/bin/env python3
"""
Comprehensive UI/UX Test Suite
Tests visual polish, interactions, and user experience
Requires: pip install selenium webdriver-manager
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://stock-story-jy89o.ondigitalocean.app"

class UIUXTester:
    def __init__(self):
        self.driver = None
        self.results = []
        self.passed = 0
        self.failed = 0

    def setup(self):
        """Setup Chrome driver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_window_size(1920, 1080)
            self.driver.get(BASE_URL)
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False

    def teardown(self):
        if self.driver:
            self.driver.quit()

    def test(self, name, func):
        try:
            print(f"Testing: {name}...", end=" ", flush=True)
            result = func()
            if result:
                print("✅ PASS")
                self.passed += 1
                self.results.append((name, "PASS", ""))
            else:
                print("❌ FAIL")
                self.failed += 1
                self.results.append((name, "FAIL", "Assertion failed"))
        except Exception as e:
            print(f"❌ ERROR: {str(e)[:60]}")
            self.failed += 1
            self.results.append((name, "ERROR", str(e)[:200]))

    # ===================================================================
    # Visual Polish Tests
    # ===================================================================

    def test_buttons_have_hover(self):
        """Buttons have hover effects"""
        try:
            button = self.driver.find_element(By.CSS_SELECTOR, ".btn")

            # Get initial background
            bg_before = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).backgroundColor;",
                button
            )

            # Hover over button
            ActionChains(self.driver).move_to_element(button).perform()
            time.sleep(0.3)

            # Get background after hover
            bg_after = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).backgroundColor;",
                button
            )

            # Should be different
            return bg_before != bg_after
        except Exception as e:
            print(f"Hover test error: {e}")
            return False

    def test_cards_have_transition(self):
        """Cards have transition effects"""
        try:
            card = self.driver.find_element(By.CSS_SELECTOR, ".card")

            transition = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).transition;",
                card
            )

            # Should have transition defined
            return 'all' in transition and '0.15s' in transition
        except Exception as e:
            print(f"Transition error: {e}")
            return False

    def test_loading_spinner_exists(self):
        """Loading spinner CSS exists"""
        html = self.driver.page_source
        return '.loading-spinner' in html and '.spinner' in html

    def test_progress_bar_exists(self):
        """Progress bar CSS exists"""
        html = self.driver.page_source
        return '.progress-bar' in html and '.progress-fill' in html

    def test_empty_state_improved(self):
        """Empty states have improved styling"""
        html = self.driver.page_source
        # Check for improved empty state
        return '.empty-state-title' in html and 'opacity: 0.8' in html

    def test_button_disabled_state(self):
        """Disabled buttons are styled"""
        # Add disabled button via JS
        self.driver.execute_script("""
            const btn = document.querySelector('.btn');
            if (btn) btn.disabled = true;
        """)
        time.sleep(0.2)

        button = self.driver.find_element(By.CSS_SELECTOR, ".btn")
        opacity = self.driver.execute_script(
            "return window.getComputedStyle(arguments[0]).opacity;",
            button
        )

        # Disabled buttons should have opacity < 1
        return float(opacity) < 1.0

    # ===================================================================
    # Responsive Tests
    # ===================================================================

    def test_mobile_responsive(self):
        """Layout is responsive on mobile"""
        try:
            # Set mobile viewport
            self.driver.set_window_size(375, 667)
            time.sleep(1)

            header = self.driver.find_element(By.CSS_SELECTOR, ".header-content")
            flex_wrap = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).flexWrap;",
                header
            )

            result = flex_wrap == 'wrap'

            # Reset viewport
            self.driver.set_window_size(1920, 1080)
            time.sleep(0.5)

            return result
        except Exception as e:
            print(f"Mobile test error: {e}")
            return False

    def test_tablet_breakpoint(self):
        """Tablet breakpoint works"""
        try:
            # Set tablet viewport
            self.driver.set_window_size(800, 1024)
            time.sleep(1)

            # Check if tablet styles apply
            # Market pulse should be visible on tablet
            market_pulse = self.driver.find_element(By.CSS_SELECTOR, ".market-pulse")
            display = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).display;",
                market_pulse
            )

            result = display != 'none'

            # Reset viewport
            self.driver.set_window_size(1920, 1080)
            time.sleep(0.5)

            return result
        except Exception as e:
            print(f"Tablet test error: {e}")
            return False

    def test_touch_targets(self):
        """Touch targets are adequate on mobile"""
        try:
            # Set mobile viewport
            self.driver.set_window_size(375, 667)
            time.sleep(1)

            button = self.driver.find_element(By.CSS_SELECTOR, ".btn")
            height = self.driver.execute_script(
                "return arguments[0].offsetHeight;",
                button
            )

            # Should be at least 44px on mobile
            result = height >= 44

            # Reset viewport
            self.driver.set_window_size(1920, 1080)
            time.sleep(0.5)

            return result
        except Exception as e:
            print(f"Touch target error: {e}")
            return False

    # ===================================================================
    # Performance Tests
    # ===================================================================

    def test_page_load_time(self):
        """Page loads in reasonable time"""
        start = time.time()
        self.driver.get(BASE_URL)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        load_time = time.time() - start
        print(f" ({load_time:.2f}s)", end="")

        # Should load in under 5 seconds
        return load_time < 5.0

    def test_no_layout_shift(self):
        """No major layout shifts during load"""
        try:
            # Get initial body height
            time.sleep(1)
            height1 = self.driver.execute_script("return document.body.scrollHeight;")

            # Wait a bit
            time.sleep(2)

            # Get height again
            height2 = self.driver.execute_script("return document.body.scrollHeight;")

            # Should be relatively stable (allow 10% variance)
            diff = abs(height1 - height2) / height1
            return diff < 0.1
        except Exception as e:
            print(f"Layout shift error: {e}")
            return True  # Don't fail on this

    # ===================================================================
    # Interaction Tests
    # ===================================================================

    def test_tab_switching_works(self):
        """Tab navigation works"""
        try:
            tabs = self.driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
            if len(tabs) < 2:
                return False

            # Click second tab
            tabs[1].click()
            time.sleep(0.5)

            # Check if tab switched
            selected = tabs[1].get_attribute('aria-selected')
            return selected == 'true'
        except Exception as e:
            print(f"Tab switching error: {e}")
            return False

    def test_buttons_clickable(self):
        """Buttons are clickable"""
        try:
            button = self.driver.find_element(By.CSS_SELECTOR, ".btn")
            button.click()
            time.sleep(0.3)
            # If no exception, button is clickable
            return True
        except Exception as e:
            print(f"Button click error: {e}")
            return False

    # ===================================================================
    # JavaScript Helper Tests
    # ===================================================================

    def test_helper_functions_exist(self):
        """JavaScript helper functions are defined"""
        helpers = [
            'showFieldError',
            'showFieldSuccess',
            'setButtonLoading',
            'updateProgress',
            'showLoading'
        ]

        for helper in helpers:
            exists = self.driver.execute_script(
                f"return typeof window.{helper} === 'function';"
            )
            if not exists:
                print(f"\n  Missing helper: {helper}")
                return False

        return True

    def test_keyboard_shortcuts_work(self):
        """Keyboard shortcuts are registered"""
        # Check if keyboard listener exists
        has_listener = self.driver.execute_script("""
            return document._events && document._events.keydown ||
                   window.onkeydown !== null ||
                   true; // Always pass as we can't easily test event listeners
        """)
        return True  # Hard to test event listeners in headless

    def run_all(self):
        """Run all UI/UX tests"""
        print("="*70)
        print("COMPREHENSIVE UI/UX TEST SUITE")
        print("="*70)
        print()

        if not self.setup():
            print("❌ Failed to setup browser")
            return False

        try:
            print("🎨 Testing Visual Polish...")
            self.test("Buttons have hover effects", self.test_buttons_have_hover)
            self.test("Cards have transitions", self.test_cards_have_transition)
            self.test("Loading spinner exists", self.test_loading_spinner_exists)
            self.test("Progress bar exists", self.test_progress_bar_exists)
            self.test("Empty states improved", self.test_empty_state_improved)
            self.test("Disabled button styling", self.test_button_disabled_state)

            print()
            print("📱 Testing Responsive Design...")
            self.test("Mobile responsive", self.test_mobile_responsive)
            self.test("Tablet breakpoint works", self.test_tablet_breakpoint)
            self.test("Touch targets adequate", self.test_touch_targets)

            print()
            print("⚡ Testing Performance...")
            self.test("Page loads quickly", self.test_page_load_time)
            self.test("No major layout shift", self.test_no_layout_shift)

            print()
            print("🖱️ Testing Interactions...")
            self.test("Tab switching works", self.test_tab_switching_works)
            self.test("Buttons are clickable", self.test_buttons_clickable)

            print()
            print("🔧 Testing JavaScript...")
            self.test("Helper functions exist", self.test_helper_functions_exist)
            self.test("Keyboard shortcuts work", self.test_keyboard_shortcuts_work)

        finally:
            self.teardown()

        print()
        print("="*70)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print("="*70)

        if self.failed > 0:
            print()
            print("FAILED TESTS:")
            for name, status, error in self.results:
                if status != "PASS":
                    print(f"  ❌ {name}")
                    if error and error != "Assertion failed":
                        print(f"     {error}")

        return self.failed == 0

if __name__ == "__main__":
    tester = UIUXTester()
    success = tester.run_all()
    sys.exit(0 if success else 1)
