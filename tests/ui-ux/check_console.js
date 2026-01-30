#!/usr/bin/env node
/**
 * Chrome Console Error Checker
 * Checks for all JavaScript console errors, warnings, and network issues
 */

const puppeteer = require('puppeteer');

const BASE_URL = 'https://stock-story-jy89o.ondigitalocean.app/';

async function checkConsole() {
    console.log('='.repeat(70));
    console.log('CHROME CONSOLE ERROR CHECKER');
    console.log('='.repeat(70));
    console.log(`URL: ${BASE_URL}`);
    console.log('');

    let browser;
    const consoleMessages = [];
    const errors = [];
    const warnings = [];
    const networkErrors = [];

    try {
        console.log('🚀 Launching Chrome...');

        const path = require('path');
        const fs = require('fs');
        const profileDir = path.join(__dirname, 'chrome-profile');

        // Clean up profile directory completely
        if (fs.existsSync(profileDir)) {
            fs.rmSync(profileDir, { recursive: true, force: true });
        }

        // Wait a bit for cleanup
        await new Promise(resolve => setTimeout(resolve, 1000));

        browser = await puppeteer.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage'
            ],
            userDataDir: profileDir
        });

        const page = await browser.newPage();

        // Set viewport
        await page.setViewport({ width: 1920, height: 1080 });

        // Capture console messages
        page.on('console', msg => {
            const type = msg.type();
            const text = msg.text();
            const location = msg.location();

            consoleMessages.push({
                type,
                text,
                location: `${location.url}:${location.lineNumber}`
            });

            if (type === 'error') {
                errors.push({ text, location: location.url });
            } else if (type === 'warning') {
                warnings.push({ text, location: location.url });
            }
        });

        // Capture page errors
        page.on('pageerror', error => {
            errors.push({
                text: error.message,
                location: 'Page Error',
                stack: error.stack
            });
        });

        // Capture failed requests
        page.on('requestfailed', request => {
            networkErrors.push({
                url: request.url(),
                failure: request.failure().errorText
            });
        });

        console.log('🌐 Loading page...');
        await page.goto(BASE_URL, {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        console.log('✅ Page loaded');
        console.log('');

        // Wait a bit for JavaScript to execute
        await page.waitForTimeout(3000);

        // Check for helper functions
        console.log('='.repeat(70));
        console.log('CHECKING JAVASCRIPT HELPER FUNCTIONS');
        console.log('='.repeat(70));

        const helpers = [
            'showFieldError',
            'showFieldSuccess',
            'setButtonLoading',
            'updateProgress',
            'showLoading',
            'updateTabARIA'
        ];

        for (const helper of helpers) {
            const exists = await page.evaluate((fn) => {
                return typeof window[fn] === 'function';
            }, helper);

            if (exists) {
                console.log(`✅ ${helper}()`);
            } else {
                console.log(`❌ ${helper}() - NOT FOUND`);
                errors.push({
                    text: `Missing function: ${helper}()`,
                    location: 'Function Check'
                });
            }
        }

        console.log('');

        // Check for global functions
        console.log('='.repeat(70));
        console.log('CHECKING GLOBAL FUNCTIONS');
        console.log('='.repeat(70));

        const globals = ['refreshAll', 'showTab', 'triggerScan', 'fetchScan'];

        for (const globalFunc of globals) {
            const exists = await page.evaluate((fn) => {
                return typeof window[fn] === 'function';
            }, globalFunc);

            if (exists) {
                console.log(`✅ ${globalFunc}()`);
            } else {
                console.log(`⚠️  ${globalFunc}() - not found`);
            }
        }

        console.log('');

        // Check DOM elements
        console.log('='.repeat(70));
        console.log('CHECKING DOM ELEMENTS');
        console.log('='.repeat(70));

        const checks = [
            { selector: '[role="tab"]', name: 'Tabs' },
            { selector: '.btn', name: 'Buttons' },
            { selector: '#sync-status-text', name: 'Sync status' },
            { selector: '.market-pulse', name: 'Market pulse' },
            { selector: '.tab-content', name: 'Tab panels' }
        ];

        for (const check of checks) {
            const count = await page.$$eval(check.selector, elements => elements.length);
            if (count > 0) {
                console.log(`✅ ${check.name}: ${count} found`);
            } else {
                console.log(`⚠️  ${check.name}: not found`);
            }
        }

        console.log('');

        // Test tab switching
        console.log('='.repeat(70));
        console.log('TESTING INTERACTIONS');
        console.log('='.repeat(70));

        try {
            const tabs = await page.$$('[role="tab"]');
            if (tabs.length > 1) {
                console.log('🧪 Testing tab switching...');
                await tabs[1].click();
                await page.waitForTimeout(500);

                const isSelected = await page.evaluate(() => {
                    const tabs = document.querySelectorAll('[role="tab"]');
                    return tabs[1].getAttribute('aria-selected') === 'true';
                });

                if (isSelected) {
                    console.log('   ✅ Tab switching works');
                } else {
                    console.log('   ❌ Tab switching ARIA not updated');
                }
            }
        } catch (e) {
            console.log(`   ❌ Tab switching failed: ${e.message}`);
        }

        console.log('');

        // Report console messages
        console.log('='.repeat(70));
        console.log(`CONSOLE ERRORS: ${errors.length} found`);
        console.log('='.repeat(70));

        if (errors.length > 0) {
            for (let i = 0; i < errors.length; i++) {
                console.log(`\n❌ Error #${i + 1}:`);
                console.log(`   Message: ${errors[i].text}`);
                console.log(`   Location: ${errors[i].location}`);
                if (errors[i].stack) {
                    console.log(`   Stack: ${errors[i].stack.split('\n')[0]}`);
                }
            }
        } else {
            console.log('✅ No console errors found!');
        }

        console.log('');
        console.log('='.repeat(70));
        console.log(`CONSOLE WARNINGS: ${warnings.length} found`);
        console.log('='.repeat(70));

        if (warnings.length > 0) {
            for (let i = 0; i < warnings.length; i++) {
                console.log(`\n⚠️  Warning #${i + 1}:`);
                console.log(`   ${warnings[i].text}`);
            }
        } else {
            console.log('✅ No console warnings found!');
        }

        console.log('');
        console.log('='.repeat(70));
        console.log(`NETWORK ERRORS: ${networkErrors.length} found`);
        console.log('='.repeat(70));

        if (networkErrors.length > 0) {
            for (let i = 0; i < networkErrors.length; i++) {
                console.log(`\n❌ Network Error #${i + 1}:`);
                console.log(`   URL: ${networkErrors[i].url}`);
                console.log(`   Error: ${networkErrors[i].failure}`);
            }
        } else {
            console.log('✅ No network errors found!');
        }

        console.log('');
        console.log('='.repeat(70));
        console.log('ALL CONSOLE MESSAGES');
        console.log('='.repeat(70));

        if (consoleMessages.length > 0) {
            const grouped = consoleMessages.reduce((acc, msg) => {
                if (!acc[msg.type]) acc[msg.type] = [];
                acc[msg.type].push(msg);
                return acc;
            }, {});

            for (const [type, messages] of Object.entries(grouped)) {
                console.log(`\n📋 ${type.toUpperCase()} (${messages.length} messages):`);
                messages.slice(0, 10).forEach((msg, i) => {
                    console.log(`   ${i + 1}. ${msg.text}`);
                });
                if (messages.length > 10) {
                    console.log(`   ... and ${messages.length - 10} more`);
                }
            }
        } else {
            console.log('ℹ️  No console messages captured');
        }

        console.log('');
        console.log('='.repeat(70));
        console.log('SUMMARY');
        console.log('='.repeat(70));
        console.log(`Errors: ${errors.length}`);
        console.log(`Warnings: ${warnings.length}`);
        console.log(`Network Errors: ${networkErrors.length}`);
        console.log(`Total Console Messages: ${consoleMessages.length}`);
        console.log('');

        if (errors.length === 0 && networkErrors.length === 0) {
            console.log('🎉 NO CRITICAL ERRORS FOUND!');
            console.log('✅ Dashboard is functioning properly');
            await browser.close();
            return true;
        } else {
            console.log('⚠️  ISSUES DETECTED');
            console.log(`   ${errors.length} console errors`);
            console.log(`   ${networkErrors.length} network errors`);
            await browser.close();
            return false;
        }

    } catch (error) {
        console.log(`❌ Failed to check console: ${error.message}`);
        if (browser) {
            try {
                await browser.close();
            } catch (e) {}
        }
        return false;
    } finally {
        // Clean up profile directory
        const path = require('path');
        const fs = require('fs');
        const profileDir = path.join(__dirname, 'chrome-profile');

        try {
            if (fs.existsSync(profileDir)) {
                fs.rmSync(profileDir, { recursive: true, force: true });
            }
        } catch (e) {
            // Ignore cleanup errors
        }
    }
}

checkConsole().then(success => {
    process.exit(success ? 0 : 1);
}).catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
