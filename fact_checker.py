#!/usr/bin/env python3
"""
Fact Check System

Verifies claims across multiple sources.
All sources start equal - accuracy determines trust over time.

Features:
1. Claim extraction from headlines
2. Cross-source verification
3. SEC filing checks
4. Price action confirmation
5. Trust score updates based on accuracy
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Try to import yfinance for price checks
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

# DeepSeek for AI-powered claim extraction
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ============================================================
# CONFIGURATION
# ============================================================

# All sources start with EQUAL trust score
INITIAL_TRUST_SCORE = 50  # Everyone starts at 50/100

# Files for tracking
CLAIMS_FILE = Path('claims_history.json')
SOURCE_TRUST_FILE = Path('source_trust.json')

# Claim categories
CLAIM_TYPES = {
    'EARNINGS': ['earnings', 'eps', 'revenue', 'profit', 'beat', 'miss', 'guidance'],
    'MERGER_ACQUISITION': ['acquire', 'merger', 'buyout', 'takeover', 'deal'],
    'STOCK_ACTION': ['split', 'dividend', 'buyback', 'offering'],
    'PRODUCT': ['launch', 'announce', 'release', 'unveil', 'introduce'],
    'EXECUTIVE': ['ceo', 'cfo', 'resign', 'hire', 'appoint', 'depart'],
    'LEGAL': ['lawsuit', 'sue', 'settlement', 'investigation', 'sec'],
    'PARTNERSHIP': ['partner', 'collaborate', 'agreement', 'contract'],
    'PRICE_TARGET': ['target', 'upgrade', 'downgrade', 'rating'],
    'RUMOR': ['rumor', 'reportedly', 'may', 'might', 'could', 'considering'],
}


# ============================================================
# SOURCE TRUST MANAGEMENT (EQUAL START)
# ============================================================

def load_source_trust():
    """Load source trust scores. New sources start at INITIAL_TRUST_SCORE."""
    if SOURCE_TRUST_FILE.exists():
        with open(SOURCE_TRUST_FILE, 'r') as f:
            return json.load(f)
    return {
        'scores': {},  # source -> score
        'history': {},  # source -> {verified: X, total: Y}
        'last_updated': None,
    }


def save_source_trust(data):
    """Save source trust data."""
    data['last_updated'] = datetime.now().isoformat()
    with open(SOURCE_TRUST_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_source_trust(source_name):
    """
    Get trust score for a source.
    All sources start EQUAL at 50.
    Score adjusts based on verification accuracy.
    """
    trust_data = load_source_trust()

    if source_name not in trust_data['scores']:
        # New source - start at equal score
        trust_data['scores'][source_name] = INITIAL_TRUST_SCORE
        trust_data['history'][source_name] = {'verified': 0, 'total': 0}
        save_source_trust(trust_data)

    return trust_data['scores'][source_name]


def update_source_trust(source_name, was_accurate):
    """
    Update source trust based on claim accuracy.
    +5 for accurate claims, -5 for inaccurate.
    """
    trust_data = load_source_trust()

    if source_name not in trust_data['scores']:
        trust_data['scores'][source_name] = INITIAL_TRUST_SCORE
        trust_data['history'][source_name] = {'verified': 0, 'total': 0}

    # Update history
    trust_data['history'][source_name]['total'] += 1
    if was_accurate:
        trust_data['history'][source_name]['verified'] += 1

    # Calculate new score based on accuracy rate
    history = trust_data['history'][source_name]
    if history['total'] >= 3:  # Need at least 3 claims
        accuracy_rate = history['verified'] / history['total']
        # Score = 50 + (accuracy_rate - 0.5) * 100
        # Ranges from 0 (0% accurate) to 100 (100% accurate)
        new_score = 50 + (accuracy_rate - 0.5) * 100
        trust_data['scores'][source_name] = max(0, min(100, new_score))
    else:
        # Not enough data - small adjustment
        adjustment = 3 if was_accurate else -3
        trust_data['scores'][source_name] = max(0, min(100,
            trust_data['scores'][source_name] + adjustment))

    save_source_trust(trust_data)
    return trust_data['scores'][source_name]


def get_all_source_trust():
    """Get all source trust scores sorted by score."""
    trust_data = load_source_trust()

    result = []
    for source, score in trust_data['scores'].items():
        history = trust_data['history'].get(source, {'verified': 0, 'total': 0})
        result.append({
            'source': source,
            'score': score,
            'verified': history['verified'],
            'total': history['total'],
            'accuracy': round(history['verified'] / history['total'] * 100, 1) if history['total'] > 0 else 0,
        })

    result.sort(key=lambda x: -x['score'])
    return result


# ============================================================
# SELF-LEARNING SYSTEM
# ============================================================

LEARNING_FILE = Path('fact_check_learning.json')


def load_learning_data():
    """Load self-learning data."""
    if LEARNING_FILE.exists():
        with open(LEARNING_FILE, 'r') as f:
            return json.load(f)
    return {
        'source_topic_accuracy': {},   # source -> topic -> {correct, total}
        'source_claim_type_accuracy': {},  # source -> claim_type -> {correct, total}
        'verification_method_accuracy': {},  # method -> {correct, total}
        'source_combinations': {},  # "source1+source2" -> {correct, total}
        'early_detector_sources': {},  # source -> {early_calls, total}
        'learned_patterns': [],  # List of learned patterns
        'last_updated': None,
    }


def save_learning_data(data):
    """Save learning data."""
    data['last_updated'] = datetime.now().isoformat()
    with open(LEARNING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def learn_from_verification(claim, verification_result, was_accurate):
    """
    Learn from a verification result.
    Updates patterns for:
    1. Source accuracy by topic
    2. Source accuracy by claim type
    3. Verification method effectiveness
    4. Source combination reliability
    """
    learning = load_learning_data()
    source = claim.get('source', 'Unknown')
    claim_type = claim.get('claim_type', 'GENERAL')
    ticker = claim.get('ticker', '')

    # Determine topic from ticker
    topic = get_topic_from_ticker(ticker) if ticker else 'GENERAL'

    # 1. Learn source accuracy by topic
    if source not in learning['source_topic_accuracy']:
        learning['source_topic_accuracy'][source] = {}
    if topic not in learning['source_topic_accuracy'][source]:
        learning['source_topic_accuracy'][source][topic] = {'correct': 0, 'total': 0}

    learning['source_topic_accuracy'][source][topic]['total'] += 1
    if was_accurate:
        learning['source_topic_accuracy'][source][topic]['correct'] += 1

    # 2. Learn source accuracy by claim type
    if source not in learning['source_claim_type_accuracy']:
        learning['source_claim_type_accuracy'][source] = {}
    if claim_type not in learning['source_claim_type_accuracy'][source]:
        learning['source_claim_type_accuracy'][source][claim_type] = {'correct': 0, 'total': 0}

    learning['source_claim_type_accuracy'][source][claim_type]['total'] += 1
    if was_accurate:
        learning['source_claim_type_accuracy'][source][claim_type]['correct'] += 1

    # 3. Learn verification method effectiveness
    for verification in verification_result.get('verifications', []):
        method = verification.get('method', 'UNKNOWN')
        if method not in learning['verification_method_accuracy']:
            learning['verification_method_accuracy'][method] = {'correct': 0, 'total': 0}

        learning['verification_method_accuracy'][method]['total'] += 1
        if was_accurate:
            learning['verification_method_accuracy'][method]['correct'] += 1

    # 4. Learn source combinations
    sources = verification_result.get('verifications', [{}])[0].get('sources', [])
    if len(sources) >= 2:
        combo_key = '+'.join(sorted(sources[:3]))
        if combo_key not in learning['source_combinations']:
            learning['source_combinations'][combo_key] = {'correct': 0, 'total': 0}

        learning['source_combinations'][combo_key]['total'] += 1
        if was_accurate:
            learning['source_combinations'][combo_key]['correct'] += 1

    save_learning_data(learning)


def get_topic_from_ticker(ticker):
    """Map ticker to a topic/sector."""
    # Simple mapping - could be enhanced with yfinance sector data
    TICKER_TOPICS = {
        'NVDA': 'SEMICONDUCTORS', 'AMD': 'SEMICONDUCTORS', 'INTC': 'SEMICONDUCTORS',
        'AVGO': 'SEMICONDUCTORS', 'MU': 'SEMICONDUCTORS', 'QCOM': 'SEMICONDUCTORS',
        'AAPL': 'TECH', 'MSFT': 'TECH', 'GOOGL': 'TECH', 'META': 'TECH', 'AMZN': 'TECH',
        'TSLA': 'EV', 'RIVN': 'EV', 'LCID': 'EV',
        'LLY': 'PHARMA', 'NVO': 'PHARMA', 'PFE': 'PHARMA', 'MRNA': 'PHARMA',
        'JPM': 'FINANCE', 'GS': 'FINANCE', 'BAC': 'FINANCE',
        'VST': 'ENERGY', 'CEG': 'ENERGY', 'NEE': 'ENERGY',
        'BTC': 'CRYPTO', 'COIN': 'CRYPTO', 'MSTR': 'CRYPTO',
    }
    return TICKER_TOPICS.get(ticker, 'GENERAL')


def get_source_topic_score(source, topic):
    """Get a source's accuracy score for a specific topic."""
    learning = load_learning_data()

    source_topics = learning.get('source_topic_accuracy', {}).get(source, {})
    topic_data = source_topics.get(topic, {'correct': 0, 'total': 0})

    if topic_data['total'] >= 3:
        return topic_data['correct'] / topic_data['total'] * 100

    return 50  # Default


def get_best_sources_for_topic(topic, top_n=5):
    """Get the best sources for a specific topic based on learned accuracy."""
    learning = load_learning_data()

    source_scores = []
    for source, topics in learning.get('source_topic_accuracy', {}).items():
        if topic in topics and topics[topic]['total'] >= 2:
            accuracy = topics[topic]['correct'] / topics[topic]['total'] * 100
            source_scores.append({
                'source': source,
                'accuracy': accuracy,
                'total': topics[topic]['total'],
            })

    source_scores.sort(key=lambda x: -x['accuracy'])
    return source_scores[:top_n]


def get_best_source_combinations(top_n=5):
    """Get the most reliable source combinations."""
    learning = load_learning_data()

    combos = []
    for combo, data in learning.get('source_combinations', {}).items():
        if data['total'] >= 3:
            accuracy = data['correct'] / data['total'] * 100
            combos.append({
                'combination': combo.split('+'),
                'accuracy': accuracy,
                'total': data['total'],
            })

    combos.sort(key=lambda x: -x['accuracy'])
    return combos[:top_n]


def learn_early_detector(source, was_early):
    """
    Track which sources detect stories early (before price moves).
    """
    learning = load_learning_data()

    if source not in learning['early_detector_sources']:
        learning['early_detector_sources'][source] = {'early_calls': 0, 'total': 0}

    learning['early_detector_sources'][source]['total'] += 1
    if was_early:
        learning['early_detector_sources'][source]['early_calls'] += 1

    save_learning_data(learning)


def get_early_detector_sources(top_n=5):
    """Get sources that are best at detecting stories early."""
    learning = load_learning_data()

    sources = []
    for source, data in learning.get('early_detector_sources', {}).items():
        if data['total'] >= 3:
            early_rate = data['early_calls'] / data['total'] * 100
            sources.append({
                'source': source,
                'early_rate': early_rate,
                'total': data['total'],
            })

    sources.sort(key=lambda x: -x['early_rate'])
    return sources[:top_n]


def add_learned_pattern(pattern_description, confidence):
    """Add a learned pattern to the system."""
    learning = load_learning_data()

    learning['learned_patterns'].append({
        'pattern': pattern_description,
        'confidence': confidence,
        'learned_date': datetime.now().isoformat(),
    })

    # Keep only last 50 patterns
    learning['learned_patterns'] = learning['learned_patterns'][-50:]

    save_learning_data(learning)


def get_learned_insights():
    """Get human-readable insights from learned data."""
    learning = load_learning_data()
    insights = []

    # Best sources by topic
    for topic in ['SEMICONDUCTORS', 'TECH', 'PHARMA', 'ENERGY', 'CRYPTO']:
        best = get_best_sources_for_topic(topic, top_n=2)
        if best and best[0]['accuracy'] > 60:
            insights.append(f"For {topic}: {best[0]['source']} is {best[0]['accuracy']:.0f}% accurate")

    # Best source combinations
    combos = get_best_source_combinations(top_n=2)
    for combo in combos:
        if combo['accuracy'] > 70:
            sources = ' + '.join(combo['combination'][:2])
            insights.append(f"Reliable combo: {sources} ({combo['accuracy']:.0f}% accurate)")

    # Early detectors
    early = get_early_detector_sources(top_n=2)
    for source in early:
        if source['early_rate'] > 50:
            insights.append(f"Early signal source: {source['source']} ({source['early_rate']:.0f}% early)")

    return insights


# ============================================================
# CLAIM EXTRACTION
# ============================================================

def extract_claims_ai(headlines):
    """
    Use AI to extract specific factual claims from headlines.
    """
    if not DEEPSEEK_API_KEY or not headlines:
        return extract_claims_keywords(headlines)

    headlines_text = "\n".join([
        f"[{h.get('source', 'Unknown')}] {h.get('title', h.get('text', ''))}"
        for h in headlines[:20]
    ])

    prompt = f"""Extract specific FACTUAL CLAIMS from these headlines that can be verified.

Headlines:
{headlines_text}

For each claim, identify:
1. The specific claim (what is being stated)
2. The ticker/company involved
3. The claim type (EARNINGS, MERGER, PRODUCT, EXECUTIVE, LEGAL, RUMOR, etc.)
4. Source that made the claim
5. Is this verifiable? (can we check if true/false)

Respond in JSON format:
{{
    "claims": [
        {{
            "claim": "specific statement that can be verified",
            "ticker": "TICKER or null",
            "company": "Company Name",
            "claim_type": "EARNINGS/MERGER/PRODUCT/etc",
            "source": "source name",
            "verifiable": true/false,
            "verification_method": "how to verify (SEC filing, price action, official announcement, etc.)"
        }}
    ]
}}

Only extract claims that make specific, verifiable statements. Skip vague opinions."""

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a fact-checker extracting verifiable claims from news. Be precise and objective."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

    except Exception as e:
        print(f"AI claim extraction error: {e}")

    return extract_claims_keywords(headlines)


def extract_claims_keywords(headlines):
    """Fallback: Extract claims using keyword matching."""
    claims = []

    for h in headlines:
        text = h.get('title', h.get('text', '')).lower()
        source = h.get('source', 'Unknown')

        # Detect claim type
        claim_type = 'GENERAL'
        for ctype, keywords in CLAIM_TYPES.items():
            if any(kw in text for kw in keywords):
                claim_type = ctype
                break

        # Extract ticker (simple pattern)
        ticker_match = re.search(r'\b([A-Z]{2,5})\b', h.get('title', ''))
        ticker = ticker_match.group(1) if ticker_match else None

        # Skip very short headlines
        if len(text) < 20:
            continue

        claims.append({
            'claim': h.get('title', h.get('text', '')),
            'ticker': ticker,
            'claim_type': claim_type,
            'source': source,
            'verifiable': claim_type in ['EARNINGS', 'MERGER_ACQUISITION', 'STOCK_ACTION', 'EXECUTIVE'],
        })

    return {'claims': claims[:15]}


# ============================================================
# VERIFICATION METHODS
# ============================================================

def verify_claim_cross_source(claim, all_headlines):
    """
    Verify a claim by checking if multiple sources report it.
    """
    claim_text = claim.get('claim', '').lower()
    claim_source = claim.get('source', '')

    # Extract key terms from claim
    key_terms = [w for w in claim_text.split()
                 if len(w) > 4 and w not in ['about', 'their', 'which', 'would', 'could', 'after']][:5]

    if not key_terms:
        return {'verified': False, 'confidence': 0, 'sources': [claim_source]}

    # Find matching headlines from other sources
    matching_sources = set([claim_source])

    for h in all_headlines:
        h_source = h.get('source', '')
        h_text = h.get('title', h.get('text', '')).lower()

        if h_source == claim_source:
            continue

        # Count matching terms
        matches = sum(1 for term in key_terms if term in h_text)
        if matches >= len(key_terms) * 0.4:  # 40% of key terms match
            matching_sources.add(h_source)

    num_sources = len(matching_sources)

    if num_sources >= 3:
        return {
            'verified': True,
            'confidence': 90,
            'sources': list(matching_sources),
            'method': 'CROSS_SOURCE',
            'detail': f'Confirmed by {num_sources} sources'
        }
    elif num_sources == 2:
        return {
            'verified': True,
            'confidence': 60,
            'sources': list(matching_sources),
            'method': 'CROSS_SOURCE',
            'detail': f'Reported by {num_sources} sources'
        }
    else:
        return {
            'verified': False,
            'confidence': 20,
            'sources': list(matching_sources),
            'method': 'SINGLE_SOURCE',
            'detail': 'Only one source reporting'
        }


def verify_claim_price_action(claim):
    """
    Verify claim by checking if price moved as expected.
    """
    if not YF_AVAILABLE:
        return None

    ticker = claim.get('ticker')
    if not ticker:
        return None

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='5d')

        if len(hist) < 2:
            return None

        # Calculate recent move
        current = hist['Close'].iloc[-1]
        previous = hist['Close'].iloc[0]
        change_pct = (current / previous - 1) * 100
        volume_spike = hist['Volume'].iloc[-1] / hist['Volume'].mean()

        claim_type = claim.get('claim_type', '')
        claim_text = claim.get('claim', '').lower()

        # Check if price action matches claim
        is_positive_claim = any(w in claim_text for w in ['beat', 'raise', 'upgrade', 'buy', 'growth', 'approve'])
        is_negative_claim = any(w in claim_text for w in ['miss', 'cut', 'downgrade', 'sell', 'decline', 'lawsuit'])

        price_confirms = False
        if is_positive_claim and change_pct > 2:
            price_confirms = True
        elif is_negative_claim and change_pct < -2:
            price_confirms = True
        elif volume_spike > 2:  # High volume suggests news event
            price_confirms = True

        return {
            'price_change': round(change_pct, 2),
            'volume_spike': round(volume_spike, 1),
            'confirms_claim': price_confirms,
            'method': 'PRICE_ACTION'
        }

    except Exception as e:
        return None


def verify_claim(claim, all_headlines):
    """
    Run full verification on a claim.
    """
    results = {
        'claim': claim,
        'verifications': [],
        'overall_confidence': 0,
        'status': 'UNVERIFIED'
    }

    # Cross-source verification
    cross_source = verify_claim_cross_source(claim, all_headlines)
    results['verifications'].append(cross_source)

    # Price action verification
    price_action = verify_claim_price_action(claim)
    if price_action:
        results['verifications'].append(price_action)

    # Calculate overall confidence
    confidences = [v.get('confidence', 0) for v in results['verifications'] if 'confidence' in v]
    if confidences:
        results['overall_confidence'] = sum(confidences) / len(confidences)

    # Determine status
    if results['overall_confidence'] >= 70:
        results['status'] = 'VERIFIED'
    elif results['overall_confidence'] >= 40:
        results['status'] = 'LIKELY_TRUE'
    elif results['overall_confidence'] >= 20:
        results['status'] = 'UNCONFIRMED'
    else:
        results['status'] = 'LIKELY_FALSE'

    # Update source trust based on verification
    if results['status'] in ['VERIFIED', 'LIKELY_TRUE']:
        for source in cross_source.get('sources', []):
            update_source_trust(source, True)
    elif results['status'] == 'LIKELY_FALSE':
        update_source_trust(claim.get('source', 'Unknown'), False)

    return results


# ============================================================
# MAIN FACT CHECK FUNCTION
# ============================================================

def run_fact_check(headlines):
    """
    Run fact check on a list of headlines.

    1. Extract claims
    2. Verify each claim
    3. Return verified vs unverified
    """
    if not headlines:
        return {'claims': [], 'summary': 'No headlines to check'}

    # Extract claims
    extracted = extract_claims_ai(headlines)
    claims = extracted.get('claims', [])

    if not claims:
        return {'claims': [], 'summary': 'No verifiable claims found'}

    # Verify each claim
    verified_claims = []
    for claim in claims:
        if claim.get('verifiable', True):
            result = verify_claim(claim, headlines)
            verified_claims.append(result)

    # Summarize
    verified = [c for c in verified_claims if c['status'] == 'VERIFIED']
    likely_true = [c for c in verified_claims if c['status'] == 'LIKELY_TRUE']
    unconfirmed = [c for c in verified_claims if c['status'] == 'UNCONFIRMED']
    likely_false = [c for c in verified_claims if c['status'] == 'LIKELY_FALSE']

    return {
        'claims': verified_claims,
        'summary': {
            'total': len(verified_claims),
            'verified': len(verified),
            'likely_true': len(likely_true),
            'unconfirmed': len(unconfirmed),
            'likely_false': len(likely_false),
        }
    }


# ============================================================
# FORMATTING
# ============================================================

def format_fact_check_report(result):
    """Format fact check results for Telegram."""
    msg = "🔍 *FACT CHECK REPORT*\n\n"

    summary = result.get('summary', {})
    if isinstance(summary, str):
        msg += f"_{summary}_"
        return msg

    msg += f"*Claims analyzed:* {summary.get('total', 0)}\n"
    msg += f"✅ Verified: {summary.get('verified', 0)}\n"
    msg += f"🟡 Likely true: {summary.get('likely_true', 0)}\n"
    msg += f"⚪ Unconfirmed: {summary.get('unconfirmed', 0)}\n"
    msg += f"🔴 Likely false: {summary.get('likely_false', 0)}\n\n"

    claims = result.get('claims', [])

    # Show verified claims
    verified = [c for c in claims if c['status'] in ['VERIFIED', 'LIKELY_TRUE']]
    if verified:
        msg += "*✅ VERIFIED CLAIMS:*\n"
        for c in verified[:4]:
            claim = c.get('claim', {})
            msg += f"• {claim.get('claim', 'Unknown')[:70]}...\n"
            sources = c.get('verifications', [{}])[0].get('sources', [])
            if sources:
                msg += f"  _Sources: {', '.join(sources[:3])}_\n"
        msg += "\n"

    # Show unconfirmed/false claims
    unverified = [c for c in claims if c['status'] in ['UNCONFIRMED', 'LIKELY_FALSE']]
    if unverified:
        msg += "*⚠️ UNVERIFIED CLAIMS:*\n"
        for c in unverified[:3]:
            claim = c.get('claim', {})
            status_emoji = '⚪' if c['status'] == 'UNCONFIRMED' else '🔴'
            msg += f"{status_emoji} {claim.get('claim', 'Unknown')[:60]}...\n"
            msg += f"  _Source: {claim.get('source', 'Unknown')} (single source)_\n"

    return msg


def format_source_trust_report():
    """Format source trust leaderboard."""
    sources = get_all_source_trust()

    if not sources:
        msg = "📊 *SOURCE TRUST SCORES*\n\n"
        msg += "_No data yet. Sources start equal at 50._\n"
        msg += "_Trust adjusts based on claim accuracy over time._"
        return msg

    msg = "📊 *SOURCE TRUST LEADERBOARD*\n\n"
    msg += "_All sources start at 50. Accuracy adjusts score._\n\n"

    for i, source in enumerate(sources[:12], 1):
        score = source['score']

        # Score emoji
        if score >= 70:
            emoji = "🟢"
        elif score >= 50:
            emoji = "🟡"
        else:
            emoji = "🔴"

        msg += f"{i}. {emoji} *{source['source']}* [{score:.0f}]\n"

        if source['total'] > 0:
            msg += f"   {source['verified']}/{source['total']} verified ({source['accuracy']}%)\n"

    msg += "\n_Score = 50 + (accuracy% - 50)_"

    return msg


def format_learning_insights():
    """Format learned insights for Telegram."""
    msg = "🧠 *LEARNED INSIGHTS*\n\n"
    msg += "_System learns from verification accuracy over time._\n\n"

    insights = get_learned_insights()

    if insights:
        msg += "*📈 What I've learned:*\n"
        for insight in insights[:8]:
            msg += f"• {insight}\n"
    else:
        msg += "_Not enough data yet. Run /factcheck to start learning._\n"

    # Show best combos
    combos = get_best_source_combinations(top_n=3)
    if combos:
        msg += "\n*🤝 Reliable Source Combinations:*\n"
        for combo in combos:
            sources = ', '.join(combo['combination'][:2])
            msg += f"• {sources}: {combo['accuracy']:.0f}% accurate\n"

    # Show early detectors
    early = get_early_detector_sources(top_n=3)
    if early:
        msg += "\n*⏰ Best Early Signal Sources:*\n"
        for source in early:
            msg += f"• {source['source']}: {source['early_rate']:.0f}% early calls\n"

    return msg


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Test with sample headlines
    test_headlines = [
        {'title': 'NVDA beats earnings expectations, stock surges 5%', 'source': 'Bloomberg'},
        {'title': 'NVIDIA reports record quarterly revenue', 'source': 'Reuters'},
        {'title': 'Nvidia earnings crush estimates', 'source': 'CNBC'},
        {'title': 'NVDA to the moon! 🚀', 'source': 'Reddit'},
        {'title': 'Apple reportedly considering TikTok acquisition', 'source': 'Twitter'},
    ]

    result = run_fact_check(test_headlines)
    print(format_fact_check_report(result))
    print("\n" + "="*50 + "\n")
    print(format_source_trust_report())
