# Change Log (Auto-Updated)

<!-- AUTO-GENERATED BELOW -->

### 2026-02-04 00:02 - `13f9ed4`

**Add social buzz to scoring formula and integrate X Intelligence**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
src/core/async_scanner.py
src/core/story_scoring.py
src/scoring/story_scorer.py
```
</details>

---


### 2026-02-03 23:37 - `165411c`

**Add technical filters for stock universe scanning**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
modal_scanner.py
src/data/universe_manager.py
```
</details>

---


### 2026-02-03 23:16 - `e1d0638`

**Fix JSON serialization with robust NaN/numpy type handling**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:56 - `e19ab66`

**Fix NaN values in JSON serialization for scan results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:42 - `84c8b65`

**Fix: Dashboard and Telegram now show same sorted results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:40 - `460e46c`

**Fix Google Trends rate limiting with throttling and backoff**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/intelligence/google_trends.py
```
</details>

---


### 2026-02-03 22:18 - `cd43064`

**Add secrets to daily_scan for manual testing**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 22:11 - `6074c09`

**Fix: Add secrets to all scheduled bundle functions**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-03 21:58 - `98ecf43`

**Fix risk_reward calculation in agentic stock analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:56 - `c0cb2a5`

**Integrate Agentic Brain AI system into dashboard**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:39 - `1e669a4`

**Remove Quick Actions from dashboard and fix Daily Digest bug**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 21:22 - `8800c00`

**Optimize dashboard loading with staged data fetching**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
docs/js/main.js
```
</details>

---


### 2026-02-03 21:18 - `2352d15`

**Fix missing fetchAIIntelligence and fetchUnusualOptions in module's refreshAll**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/js/main.js
```
</details>

---


### 2026-02-03 21:15 - `20a0fd5`

**Add fetchUnusualOptions to dashboard data loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 21:09 - `4f6654e`

**Fix wrong API URL in config.js that was breaking dashboard data loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/js/config.js
```
</details>

---


### 2026-02-03 21:04 - `a0701d0`

**Fix dashboard data loading with improved error handling and logging**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:51 - `4a16ded`

**Fix Hot Themes on dashboard to render theme pills and stocks**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:46 - `c12728b`

**Fix High Conviction alerts to handle API response structure**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:41 - `03f07a2`

**Fix dashboard to load High Conviction and Hot Themes data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 20:34 - `8dfd8fa`

**Restructure dashboard from 10 flat tabs to 4 main categories**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 19:25 - `3441efc`

**Fix AI reasoning modal close button leaving overlay blocking dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 19:21 - `d73b6ff`

**Fix confirmations/conflicts to only compare directional signals**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 19:15 - `a06e717`

**Add AI Intelligence Hub with unified market analysis**

Files changed: 3

<details>
<summary>Show files</summary>

```
.gitignore
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 18:38 - `3d85e9c`

**Add debug providers endpoint and fix CPI YoY calculation**

Files changed: 2

<details>
<summary>Show files</summary>

```
modal_api_v2.py
utils/data_providers.py
```
</details>

---


### 2026-02-03 18:15 - `2e15383`

**Add FRED Economic Dashboard with comprehensive indicators**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
utils/data_providers.py
```
</details>

---


### 2026-02-03 18:06 - `63cdaeb`

**Fix themes tab API and JS for proper data rendering**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 18:03 - `c59dd49`

**Fix correlations endpoint to return flat pair format for dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:54 - `681efb7`

**Fix tooltip clipping by using JS-based tooltips appended to body**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 17:51 - `a113c3a`

**Improve tooltip readability with better contrast and styling**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 17:47 - `ad5c3bf`

**Fix Analytics tab API response structures for dashboard compatibility**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:35 - `a352b96`

**Fix SEC Intel tab API connections and data rendering**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:28 - `1020070`

**Fix nested response structure in contracts/patents themes endpoints**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:25 - `5de66fd`

**Fix SEC Intel API response structure to match dashboard JS**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:16 - `eb21f71`

**Bot only reads and replies in Bot Alerts topic**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 17:12 - `16f7cf8`

**Send bot messages to group topic instead of main chat**

Files changed: 6

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
src/notifications/notification_manager.py
tests/check_cron_status.py
tests/test_group_notification.py
tests/trigger_crisis_monitor.py
```
</details>

---


### 2026-02-03 16:46 - `1f90a23`

**Change tooltips from underlined text to info icons**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:40 - `1e7431d`

**Add tooltips to Options, Analytics, and SEC Intel tabs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:27 - `2d4113b`

**Watchlist updates now reflect instantly**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:17 - `a9ce0bb`

**Header refresh button now only refreshes current tab**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:15 - `7d04c87`

**Optimize dashboard performance with lazy loading**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 16:11 - `e238d70`

**Fix watchlist persistence with volume.commit()**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 16:04 - `671bc5d`

**Add expandable scan rows with individual stock add/remove**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 15:55 - `7444765`

**Add dedicated Watchlist tab to dashboard**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 15:48 - `c72a163`

**Add unified watchlist and scan management system**

Files changed: 12

<details>
<summary>Show files</summary>

```
CHANGES.md
assets/stockstory_icon.png
assets/stockstory_icon.svg
assets/stockstory_logo.png
assets/stockstory_logo.svg
assets/stockstory_minimal.png
assets/stockstory_minimal.svg
docs/index.html
modal_api_v2.py
modal_scanner.py
src/data/__init__.py
src/data/watchlist_manager.py
```
</details>

---


### 2026-02-03 04:17 - `49f5b09`

**feat: Add group chat support for all notifications**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
src/notifications/notification_manager.py
```
</details>

---


### 2026-02-03 04:12 - `e9a6c3a`

**fix: Use correct variable name in /chatid command**

Files changed: 7

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/check_bot_chats.py
tests/check_group_admin.py
tests/find_stockstory_group.py
tests/send_chatid_to_group.py
tests/test_group_chatid.py
```
</details>

---


### 2026-02-03 04:02 - `7cd157c`

**feat: Add /chatid command to get chat ID for group alerts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 03:56 - `c1e725f`

**fix: Always calculate market fear level even if other fetches fail**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:54 - `64dcca3`

**feat: Add GEX and Max Pain to /hedge command**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/test_hedge_command.py
tests/test_hedge_webhook.py
```
</details>

---


### 2026-02-03 03:48 - `6aab1d5`

**fix: Revert VIX to yfinance (Polygon VIX is EOD only)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:44 - `ef29448`

**feat: Get VIX from Polygon Indices API**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 03:41 - `03f8484`

**feat: Use Polygon for SPY/QQQ prices in Grok analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:40 - `c4d3337`

**feat: Feed Polygon live options data to Grok for put analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:37 - `a90bf88`

**feat: Integrate Grok 4.1 Fast Reasoning for put protection analysis**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 03:32 - `892ad66`

**feat: Add options sentiment and put protection to crisis alerts**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/analysis/options_flow.py
src/notifications/notification_manager.py
```
</details>

---


### 2026-02-03 03:23 - `af999a5`

**feat: Add SPY and QQQ prices to health monitor**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 03:21 - `ca17519`

**fix: Add comma formatting for large dollar amounts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:15 - `5550ead`

**fix: Use month abbreviation for expiration dates (Feb 7 instead of 2/7)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:13 - `86cfd56`

**feat: Add expiration date to Whale Trades, Unusual Activity, and Smart Money Flow**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:07 - `e0b1eba`

**fix: Fix vol/OI ratio display in Unusual Activity**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:03 - `998a4e4`

**fix: Fix put/call ratio display in Options Chain Lookup**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 03:00 - `37bd848`

**feat: Add real 0DTE volume from Polygon options data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 02:56 - `08716de`

**fix: Fix GEX calculation and display formatting**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 02:55 - `3938685`

**fix: Increase Polygon options limit to 250 for full chain data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 02:49 - `56dc6f3`

**fix: Call correct functions when switching to Options tab**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:45 - `48fd195`

**fix: Lower whale trades threshold to $50K for more data**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:43 - `27605ae`

**feat: Enable Polygon.io for real-time options data**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/analysis/options_flow.py
src/data/polygon_provider.py
```
</details>

---


### 2026-02-03 02:37 - `fc40f30`

**fix: Fix JavaScript to handle API response field names**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 02:32 - `ef8afb0`

**feat: Enhanced options flow with dashboard UI and Telegram commands**

Files changed: 4

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
src/analysis/options_flow.py
```
</details>

---


### 2026-02-03 02:09 - `096d458`

**docs: Update CHANGES.md with latest entries**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-03 02:02 - `56ac910`

**fix: Add raw_data to health endpoint for dashboard market pulse**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:56 - `b27d5e5`

**fix: Update API response format to match dashboard expectations**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:53 - `b16bf53`

**fix: Auto-load data when switching tabs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 01:52 - `5475bce`

**fix: Update API_BASE to use stockstory-api endpoint**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
```
</details>

---


### 2026-02-03 01:46 - `c161f59`

**feat: Add theme management to dashboard**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
docs/index.html
modal_api_v2.py
```
</details>

---


### 2026-02-03 01:37 - `c126191`

**feat: Implement hybrid dynamic theme system with AI discovery**

Files changed: 6

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
src/themes/fast_stories.py
src/themes/theme_manager.py
tests/test_theme_commands.py
tests/test_theme_manager.py
```
</details>

---


### 2026-02-02 21:37 - `247a19f`

**fix: Telegram bot volume access and themes display**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
modal_scanner.py
static/stockstory_logo.svg
tests/send_test_message.py
```
</details>

---


### 2026-02-02 20:43 - `9a959fa`

**fix: Add volume.reload() to sync scan results**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:39 - `8fd18e5`

**fix: Update /themes command to use correct function**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:31 - `5b3d8ab`

**fix: Use max_containers instead of deprecated concurrency_limit**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:30 - `dabc579`

**fix: Save scan results CSV to Modal volume for API access**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:20 - `309410f`

**perf: Limit GPU concurrency to 10 containers max**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_scanner.py
```
</details>

---


### 2026-02-02 20:16 - `d8122a7`

**fix: Correct /news command import error**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 20:07 - `49108d0`

**fix: Update GitHub workflows for StockStory rename**

Files changed: 4

<details>
<summary>Show files</summary>

```
.github/workflows/deploy.yml
.github/workflows/manual-deploy.yml
.github/workflows/test-crisis-monitor.yml
CHANGES.md
```
</details>

---


### 2026-02-02 19:42 - `52e277f`

**refactor: Complete StockStory rebranding**

Files changed: 13

<details>
<summary>Show files</summary>

```
.env.example
CHANGES.md
PROJECT.md
README.md
docs/deployment/DEPLOYMENT_STATUS.md
docs/index.html
main.py
modal_api_v2.py
scripts/maintenance/cleanup_modal_schedules.sh
scripts/run_scan.sh
src/notifications/notification_manager.py
utils/__init__.py
utils/exceptions.py
```
</details>

---


### 2026-02-02 19:37 - `53eb300`

**refactor: Rename project to StockStory**

Files changed: 8

<details>
<summary>Show files</summary>

```
CHANGES.md
main.py
modal_api_v2.py
modal_scanner.py
src/__init__.py
src/api/app.py
tests/setup_telegram_menu.py
tests/setup_telegram_webhook.py
```
</details>

---


### 2026-02-02 19:30 - `1c4e219`

**docs: Update CHANGES.md**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-02 19:30 - `8adb657`

**chore: Add Telegram message reader utility**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
tests/read_telegram_messages.py
```
</details>

---


### 2026-02-02 19:27 - `0f760d1`

**feat: Add Telegram menu button and inline keyboards**

Files changed: 3

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
tests/setup_telegram_menu.py
```
</details>

---


### 2026-02-02 19:20 - `6db7447`

**feat: 6-month candlestick chart with 10/20/50/200 SMAs**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 19:15 - `8215f97`

**feat: Replace line chart with candlestick chart**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 19:11 - `5cad92c`

**fix: Add Markdown fallback for Telegram replies**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:58 - `3e328da`

**feat: Add detailed logging to Telegram webhook**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:50 - `d5b2b07`

**fix: Correct import for calculate_story_score in Telegram bot**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:47 - `7a7546f`

**feat: Enhanced Telegram bot with rich analysis and charts**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:40 - `743626b`

**fix: Fix Telegram bot webhook conflict and add instant messaging**

Files changed: 5

<details>
<summary>Show files</summary>

```
.github/workflows/bot_listener.yml
CHANGES.md
modal_api_v2.py
tests/fix_telegram_webhook.py
tests/setup_telegram_webhook.py
```
</details>

---


### 2026-02-02 18:28 - `a4ef6fe`

**fix: Correct import errors in Modal API endpoints**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 18:11 - `95fd20d`

**perf: Optimize web scraping with parallel fetching and fix broken sources**

Files changed: 5

<details>
<summary>Show files</summary>

```
CHANGES.md
src/analysis/news_analyzer.py
src/data/alt_sources.py
src/scoring/story_scorer.py
src/themes/fast_stories.py
```
</details>

---


### 2026-02-02 17:54 - `48a7385`

**fix: Add missing except block in evolutionary_agentic_brain.py**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
src/ai/evolutionary_agentic_brain.py
```
</details>

---


### 2026-02-02 17:53 - `9532c1a`

**chore: Update CHANGES.md with latest entry**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---


### 2026-02-02 17:39 - `bd0d648`

**fix: modal_api_v2.py use correct secret name (Stock_Story)**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
modal_api_v2.py
```
</details>

---


### 2026-02-02 17:36 - `e6d4ed1`

**docs: Add Modal secret name (Stock_Story) to PROJECT.md**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
PROJECT.md
```
</details>

---


### 2026-02-02 17:18 - `e94964e`

**fix: Post-commit hook now stacks entries correctly**

Files changed: 2

<details>
<summary>Show files</summary>

```
CHANGES.md
scripts/hooks/post-commit
```
</details>

---


### 2026-02-02 17:17 - `e1f043d`

**chore: Update CHANGES.md with latest entry**

Files changed: 1

<details>
<summary>Show files</summary>

```
CHANGES.md
```
</details>

---

