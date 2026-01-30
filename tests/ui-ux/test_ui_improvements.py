#!/usr/bin/env python3
"""
Quick UI/UX Improvements Test
Tests the CSS improvements made in Phase 1-3
"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://stock-story-jy89o.ondigitalocean.app"

class UIImprovementsTester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def test(self, name, func):
        try:
            print(f"Testing: {name}...", end=" ")
            result = func()
            if result:
                print("✅ PASS")
                self.passed += 1
                self.results.append((name, "PASS", ""))
                return True
            else:
                print("❌ FAIL")
                self.failed += 1
                self.results.append((name, "FAIL", "Test returned False"))
                return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)[:60]}")
            self.failed += 1
            self.results.append((name, "ERROR", str(e)[:200]))
            return False

    # Test 1: Check yellow color was updated
    def test_yellow_contrast(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        # Check for updated yellow color
        return '#fbbf24' in html and 'WCAG AA' in html

    # Test 2: Check focus indicators added
    def test_focus_indicators(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return ':focus-visible' in html and 'outline: 2px solid var(--blue)' in html

    # Test 3: Check screen reader class added
    def test_screen_reader_class(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '.sr-only' in html

    # Test 4: Check button states added
    def test_button_states(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '.btn:disabled' in html or '.btn[disabled]' in html

    # Test 5: Check modal animations added
    def test_modal_animations(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return 'transform: scale(0.95)' in html or 'modal-overlay.active .modal' in html

    # Test 6: Check loading spinner added
    def test_loading_spinner(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '.loading-spinner' in html and '.spinner' in html

    # Test 7: Check progress bar added
    def test_progress_bar(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '.progress-bar' in html and '.progress-fill' in html

    # Test 8: Check hover effects added
    def test_hover_effects(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        has_transition = 'transition: all 0.15s ease' in html
        has_transform = 'transform: translateX(4px)' in html or 'transform: translateY(-2px)' in html
        return has_transition and has_transform

    # Test 9: Check tablet breakpoint added
    def test_tablet_breakpoint(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '@media (min-width: 768px) and (max-width: 1024px)' in html

    # Test 10: Check mobile improvements added
    def test_mobile_improvements(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        has_touch_targets = 'min-height: 44px' in html
        has_prevent_zoom = 'font-size: 16px;  /* prevent iOS zoom */' in html
        return has_touch_targets and has_prevent_zoom

    # Test 11: Check form validation styles added
    def test_form_validation(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return '.input-error' in html and '.error-message' in html

    # Test 12: Check empty state improvements
    def test_empty_state_improvements(self):
        response = requests.get(BASE_URL, timeout=10)
        html = response.text
        return 'opacity: 0.8' in html and '.empty-state-title' in html

    def run_all(self):
        print("="*70)
        print("UI/UX IMPROVEMENTS TEST SUITE")
        print("="*70)
        print()

        print("🎨 Testing Accessibility Fixes...")
        self.test("Yellow contrast fixed (WCAG AA)", self.test_yellow_contrast)
        self.test("Focus indicators added", self.test_focus_indicators)
        self.test("Screen reader class added", self.test_screen_reader_class)

        print()
        print("✨ Testing Visual Polish...")
        self.test("Button states added", self.test_button_states)
        self.test("Modal animations added", self.test_modal_animations)
        self.test("Loading spinner added", self.test_loading_spinner)
        self.test("Progress bar added", self.test_progress_bar)
        self.test("Hover effects added", self.test_hover_effects)
        self.test("Empty state improvements", self.test_empty_state_improvements)

        print()
        print("📱 Testing Responsive Design...")
        self.test("Tablet breakpoint added", self.test_tablet_breakpoint)
        self.test("Mobile improvements added", self.test_mobile_improvements)

        print()
        print("📝 Testing Form Enhancements...")
        self.test("Form validation styles added", self.test_form_validation)

        print()
        print("="*70)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print("="*70)

        if self.failed > 0:
            print()
            print("FAILED TESTS:")
            for name, status, error in self.results:
                if status != "PASS":
                    print(f"  ❌ {name}: {error}")

        return self.failed == 0

if __name__ == "__main__":
    tester = UIImprovementsTester()
    success = tester.run_all()
    exit(0 if success else 1)
