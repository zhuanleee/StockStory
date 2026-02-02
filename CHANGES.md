# Change Log (Auto-Updated)

<!-- AUTO-GENERATED BELOW -->

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

