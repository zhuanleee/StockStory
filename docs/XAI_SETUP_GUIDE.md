# xAI (Grok) API Setup Guide

## Quick Setup

### Step 1: Get Your API Key

1. Visit: **https://console.x.ai/**
2. Sign up or log in with your X/Twitter account
3. Navigate to **API Keys** section
4. Click **Create New Key**
5. Copy your API key (format: `xai-...`)

### Step 2: Add to Environment

**Option A: Add to .env file**
```bash
cd /Users/johnlee/stock_scanner_bot
echo "XAI_API_KEY=xai-your-key-here" >> .env
```

**Option B: Export directly**
```bash
export XAI_API_KEY="xai-your-key-here"
```

**Option C: Add to shell profile (persistent)**
```bash
# For bash
echo 'export XAI_API_KEY="xai-your-key-here"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export XAI_API_KEY="xai-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Verify Configuration

```bash
# Check if key is set
echo $XAI_API_KEY

# Test API connection
curl -X POST https://api.x.ai/v1/chat/completions \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-beta",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Say hello"}
    ],
    "max_tokens": 50
  }'
```

Expected response:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "grok-beta",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

### Step 4: Run A/B Test

```bash
cd /Users/johnlee/stock_scanner_bot
python3 tests/ai_stress_test.py
```

---

## xAI API Details

### Models Available

| Model | Description | Best For |
|-------|-------------|----------|
| **grok-beta** | Latest Grok model | General tasks, fastest |
| **grok-vision-beta** | Vision-capable Grok | Image analysis |

### Pricing (As of 2026)

| Tier | Input | Output |
|------|-------|--------|
| Standard | TBD | TBD |
| Premium | TBD | TBD |

*Note: Pricing not yet publicly available. Expected to be competitive with GPT-4.*

### Rate Limits

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 60 | 150,000 |
| Paid | 3,500+ | 10M+ |

### API Endpoints

**Base URL:** `https://api.x.ai/v1`

**Endpoints:**
- `/chat/completions` - Chat completion
- `/models` - List available models

---

## Common Issues

### Error: "Invalid API Key"

**Cause:** API key not set or incorrect format

**Solution:**
```bash
# Check key format (should start with 'xai-')
echo $XAI_API_KEY | cut -c 1-4

# Should output: xai-

# If not, check your key from console.x.ai
```

### Error: "Rate Limit Exceeded"

**Cause:** Too many requests in short time

**Solution:**
```python
# Add rate limiting to your code
import time

def make_xai_request_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = make_request(prompt)
            return response
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

### Error: "Model Not Found"

**Cause:** Using wrong model name

**Solution:**
```python
# Correct model names
model = "grok-beta"  # ✓ Correct
model = "grok"       # ✗ Wrong
model = "grok-1"     # ✗ Wrong
```

---

## Integration Example

### Basic Usage

```python
import os
import requests

XAI_API_KEY = os.environ.get('XAI_API_KEY')
XAI_BASE = "https://api.x.ai/v1"

def ask_grok(prompt: str, max_tokens: int = 500):
    """Ask Grok a question."""

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "You are a helpful financial analyst."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }

    response = requests.post(
        f"{XAI_BASE}/chat/completions",
        json=data,
        headers=headers,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

# Example usage
analysis = ask_grok("Analyze NVIDIA's competitive position in AI chips")
print(analysis)
```

### Stock Scanner Integration

```python
# Add to src/ai/xai_intelligence.py

class XAIIntelligence:
    """xAI (Grok) integration for stock analysis."""

    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-beta"

    def analyze_market_theme(self, theme: str) -> str:
        """Analyze a market theme using Grok."""
        prompt = f"""Analyze the current state of the {theme} theme in stock markets.

Include:
1. Top 3 companies driving this theme
2. Key catalysts and trends
3. Risk factors to watch

Keep response under 200 words."""

        return self._make_request(prompt)

    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of financial text."""
        prompt = f"""Analyze the sentiment of this text:

"{text}"

Respond in JSON format:
{{
  "sentiment": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0-100,
  "key_factors": ["factor1", "factor2", "factor3"]
}}"""

        response = self._make_request(prompt)
        return json.loads(response)
```

---

## Comparison: xAI vs DeepSeek

### When to Use Each

**Use xAI (Grok) when:**
- ✅ You need real-time information (Grok has web access)
- ✅ Speed is critical (<2s response time needed)
- ✅ X/Twitter integration is valuable
- ✅ Budget allows premium pricing

**Use DeepSeek when:**
- ✅ Cost optimization is priority
- ✅ Batch processing (many requests)
- ✅ Response time <10s is acceptable
- ✅ High-quality analysis at lower cost

**Hybrid Approach:**
```python
def get_ai_provider(use_case: str):
    """Smart routing based on use case."""

    # Real-time user queries
    if use_case == "chat" or use_case == "realtime":
        return "xai"

    # Batch analysis
    elif use_case == "scan" or use_case == "batch":
        return "deepseek"

    # Complex research
    elif use_case == "research" or use_case == "analysis":
        return "deepseek"  # Better cost/quality ratio

    # Default
    else:
        return "deepseek"
```

---

## Security Best Practices

### 1. Never Commit API Keys
```bash
# .gitignore should include:
.env
*.key
*_key.txt
```

### 2. Use Environment Variables
```python
# ✓ Good
api_key = os.environ.get('XAI_API_KEY')

# ✗ Bad - Never hardcode
api_key = "xai-123456789..."
```

### 3. Rotate Keys Regularly
- Rotate keys every 90 days
- Use different keys for dev/prod
- Revoke old keys immediately

### 4. Monitor Usage
```python
# Log API usage for monitoring
logger.info(
    f"XAI_REQUEST "
    f"model={model} "
    f"tokens={tokens} "
    f"cost=${cost:.4f}"
)
```

---

## Next Steps

1. ✅ Get API key from https://console.x.ai/
2. ✅ Add to .env file
3. ✅ Test connection with curl
4. ✅ Run stress test: `python3 tests/ai_stress_test.py`
5. ✅ Review A/B comparison results
6. ✅ Choose provider(s) for production
7. ✅ Implement monitoring and alerts

---

## Support

**xAI Documentation:** https://docs.x.ai/
**API Status:** https://status.x.ai/
**Support:** support@x.ai

**Stock Scanner Bot:**
- GitHub Issues: https://github.com/zhuanleee/stock_scanner_bot/issues
- Test Results: `ai_stress_test_results.json`
- Analysis: `docs/AI_STRESS_TEST_ANALYSIS.md`

---

**Last Updated:** 2026-01-29
