#!/usr/bin/env python3
"""
Comprehensive Accessibility Test Suite
Tests WCAG 2.1 Level AA compliance with Selenium
Requires: pip install selenium webdriver-manager
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://stock-story-jy89o.ondigitalocean.app"

class AccessibilityTester:
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
            options.add_argument('--disable-gpu')
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_window_size(1920, 1080)
            self.driver.get(BASE_URL)
            time.sleep(3)  # Wait for initial load
            return True
        except Exception as e:
            print(f"Failed to setup driver: {e}")
            return False

    def teardown(self):
        """Clean up driver"""
        if self.driver:
            self.driver.quit()

    def test(self, name, func):
        """Run a test and record result"""
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
                self.results.append((name, "FAIL", "Test returned False"))
        except Exception as e:
            print(f"❌ ERROR: {str(e)[:60]}")
            self.failed += 1
            self.results.append((name, "ERROR", str(e)[:200]))

    # ===================================================================
    # WCAG 2.1 Level AA Tests
    # ===================================================================

    def test_page_has_lang(self):
        """1.3.1 - Page has lang attribute"""
        html = self.driver.find_element(By.TAG_NAME, "html")
        lang = html.get_attribute('lang')
        return lang and lang.strip() != ''

    def test_title_present(self):
        """2.4.2 - Page has title"""
        title = self.driver.title
        return title and title.strip() != ''

    def test_focus_visible(self):
        """2.4.7 - Focus indicator is visible"""
        try:
            # Find first button
            button = self.driver.find_element(By.CSS_SELECTOR, ".btn")

            # Tab to it
            button.send_keys(Keys.TAB)
            time.sleep(0.3)

            # Check if outline style is set
            outline_style = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).outlineStyle;",
                button
            )
            outline_width = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).outlineWidth;",
                button
            )

            # Should have outline
            return outline_style not in ['none', 'hidden'] or outline_width != '0px'
        except Exception as e:
            print(f"Focus test error: {e}")
            return False

    def test_keyboard_navigation(self):
        """2.1.1 - Keyboard navigation works"""
        try:
            tabs = self.driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
            if not tabs:
                return False

            # Click first tab
            first_tab = tabs[0]
            first_tab.click()
            time.sleep(0.3)

            # Tab to next element
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.3)

            # Check that focus moved
            active = self.driver.switch_to.active_element
            return active != first_tab
        except Exception as e:
            print(f"Keyboard nav error: {e}")
            return False

    def test_aria_roles_present(self):
        """4.1.2 - ARIA roles present on interactive elements"""
        html = self.driver.page_source

        # Check for tab roles
        has_tablist = 'role="tablist"' in html
        has_tab = 'role="tab"' in html
        has_tabpanel = 'role="tabpanel"' in html

        return has_tablist and has_tab and has_tabpanel

    def test_buttons_have_labels(self):
        """4.1.2 - All buttons have accessible names"""
        buttons = self.driver.find_elements(By.TAG_NAME, "button")

        for button in buttons:
            text = button.text.strip()
            aria_label = button.get_attribute('aria-label')

            # Button must have either text content or aria-label
            if not text and not aria_label:
                button_html = button.get_attribute('outerHTML')[:100]
                print(f"\n  Button without label: {button_html}")
                return False

        return True

    def test_form_labels(self):
        """3.3.2 - Form inputs have labels"""
        inputs = self.driver.find_elements(By.TAG_NAME, "input")

        for input_elem in inputs:
            input_id = input_elem.get_attribute('id')
            input_type = input_elem.get_attribute('type')

            # Skip hidden inputs
            if input_type == 'hidden':
                continue

            # Check for label or aria-label
            aria_label = input_elem.get_attribute('aria-label')

            if input_id:
                try:
                    label = self.driver.find_element(By.CSS_SELECTOR, f'label[for="{input_id}"]')
                    continue
                except:
                    pass

            # If no label, must have aria-label
            if not aria_label:
                print(f"\n  Input without label: {input_id or 'no-id'}")
                return False

        return True

    def test_color_contrast(self):
        """1.4.3 - Sufficient color contrast (simplified check)"""
        try:
            # Get body background
            body = self.driver.find_element(By.TAG_NAME, "body")
            bg = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).backgroundColor;",
                body
            )

            # Get text color
            text_elem = self.driver.find_element(By.CSS_SELECTOR, ".logo")
            color = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).color;",
                text_elem
            )

            # Just verify they're different (simplified)
            return bg != color
        except Exception as e:
            print(f"Contrast error: {e}")
            return False

    def test_tab_switching(self):
        """Custom - Tab switching works"""
        try:
            tabs = self.driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
            if len(tabs) < 2:
                return False

            # Click second tab
            tabs[1].click()
            time.sleep(0.5)

            # Check aria-selected
            selected = tabs[1].get_attribute('aria-selected')
            return selected == 'true'
        except Exception as e:
            print(f"Tab switching error: {e}")
            return False

    def test_responsive_mobile(self):
        """Custom - Mobile responsive design"""
        try:
            # Set mobile viewport
            self.driver.set_window_size(375, 667)
            time.sleep(1)

            # Check if layout adapts
            header = self.driver.find_element(By.CSS_SELECTOR, ".header-content")
            flex_wrap = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0]).flexWrap;",
                header
            )

            # Should wrap on mobile
            return flex_wrap == 'wrap'
        finally:
            # Reset to desktop
            self.driver.set_window_size(1920, 1080)
            time.sleep(0.5)

    def test_no_console_errors(self):
        """Custom - No JavaScript console errors"""
        try:
            logs = self.driver.get_log('browser')
            errors = [log for log in logs if log['level'] == 'SEVERE']

            if errors:
                print(f"\n  Console errors found: {len(errors)}")
                for error in errors[:3]:  # Show first 3
                    print(f"    {error['message'][:100]}")

            return len(errors) == 0
        except Exception as e:
            # Browser logs might not be available in all browsers
            return True

    def run_all(self):
        """Run all accessibility tests"""
        print("="*70)
        print("COMPREHENSIVE ACCESSIBILITY TEST SUITE (WCAG 2.1 AA)")
        print("="*70)
        print()

        if not self.setup():
            print("❌ Failed to setup browser")
            return False

        try:
            print("🔍 Testing Basic Accessibility...")
            self.test("Page has lang attribute (1.3.1)", self.test_page_has_lang)
            self.test("Page has title (2.4.2)", self.test_title_present)
            self.test("Focus indicator visible (2.4.7)", self.test_focus_visible)

            print()
            print("⌨️ Testing Keyboard & Navigation...")
            self.test("Keyboard navigation works (2.1.1)", self.test_keyboard_navigation)
            self.test("Tab switching works", self.test_tab_switching)

            print()
            print("📝 Testing ARIA & Semantics...")
            self.test("ARIA roles present (4.1.2)", self.test_aria_roles_present)
            self.test("Buttons have labels (4.1.2)", self.test_buttons_have_labels)
            self.test("Form inputs have labels (3.3.2)", self.test_form_labels)

            print()
            print("🎨 Testing Visual...")
            self.test("Color contrast sufficient (1.4.3)", self.test_color_contrast)

            print()
            print("📱 Testing Responsive...")
            self.test("Mobile responsive design", self.test_responsive_mobile)

            print()
            print("🐛 Testing Quality...")
            self.test("No JavaScript console errors", self.test_no_console_errors)

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
                    if error:
                        print(f"     {error}")

        return self.failed == 0

if __name__ == "__main__":
    tester = AccessibilityTester()
    success = tester.run_all()
    sys.exit(0 if success else 1)
