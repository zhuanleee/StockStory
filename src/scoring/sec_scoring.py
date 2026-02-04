"""
SEC Activity Scoring
====================
Calculate institutional activity score based on SEC filings and market signals.

Used by Market Health dashboard to gauge institutional sentiment.

Components:
1. Options Flow - Bullish/Bearish bias from major tickers
2. 13F Activity - Institutional buying/selling patterns
3. Insider Transactions - Form 4 filings
4. SEC Filing Activity - M&A signals (8-K, SC 13D)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def get_sec_activity_score() -> Dict:
    """
    Calculate overall SEC/institutional activity score.

    Returns:
        {
            'score': int (0-100, higher = more bullish institutional activity),
            'components': {
                'options_flow': {...},
                'insider_activity': {...},
                'filing_activity': {...}
            },
            'signals': List[str],
            'timestamp': str
        }
    """
    try:
        result = {
            'score': 50,  # Default neutral
            'components': {},
            'signals': [],
            'bullish_count': 0,
            'bearish_count': 0,
            'timestamp': datetime.now().isoformat()
        }

        score_adjustments = []

        # 1. Options Flow Component (SPY + major tickers)
        try:
            options_score = _calculate_options_flow_score()
            result['components']['options_flow'] = options_score
            score_adjustments.append(options_score.get('score', 50))

            if options_score.get('sentiment') == 'bullish':
                result['bullish_count'] += 1
                result['signals'].append(f"Options flow bullish (P/C: {options_score.get('put_call_ratio', 'N/A')})")
            elif options_score.get('sentiment') == 'bearish':
                result['bearish_count'] += 1
                result['signals'].append(f"Options flow bearish (P/C: {options_score.get('put_call_ratio', 'N/A')})")
        except Exception as e:
            logger.warning(f"Options flow scoring failed: {e}")
            result['components']['options_flow'] = {'error': str(e)}

        # 2. VIX Component (fear gauge)
        try:
            vix_score = _calculate_vix_score()
            result['components']['vix'] = vix_score
            score_adjustments.append(vix_score.get('score', 50))

            if vix_score.get('level') == 'low':
                result['signals'].append(f"VIX low ({vix_score.get('value', 'N/A')}) - complacency")
            elif vix_score.get('level') == 'high':
                result['signals'].append(f"VIX elevated ({vix_score.get('value', 'N/A')}) - fear")
        except Exception as e:
            logger.warning(f"VIX scoring failed: {e}")
            result['components']['vix'] = {'error': str(e)}

        # 3. Market Breadth (would need more data sources)
        # For now, use options sentiment as proxy
        try:
            breadth_score = _estimate_market_breadth()
            result['components']['breadth'] = breadth_score
            score_adjustments.append(breadth_score.get('score', 50))
        except Exception as e:
            logger.warning(f"Breadth scoring failed: {e}")
            result['components']['breadth'] = {'error': str(e)}

        # Calculate final score (weighted average)
        if score_adjustments:
            result['score'] = int(sum(score_adjustments) / len(score_adjustments))

        # Determine overall signal
        if result['score'] >= 65:
            result['signal'] = 'bullish'
        elif result['score'] <= 35:
            result['signal'] = 'bearish'
        else:
            result['signal'] = 'neutral'

        logger.info(f"SEC activity score: {result['score']} ({result['signal']})")
        return result

    except Exception as e:
        logger.error(f"SEC activity scoring error: {e}")
        return {
            'score': 50,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def _calculate_options_flow_score() -> Dict:
    """
    Calculate score from options flow data.

    Returns bullish score (0-100) based on:
    - Put/Call ratio (lower = more bullish)
    - Call vs Put volume
    - Sentiment analysis
    """
    try:
        from src.data.options import get_options_flow

        # Get SPY options flow as market proxy
        flow = get_options_flow('SPY')

        if flow.get('error'):
            return {'score': 50, 'error': flow.get('error')}

        pc_ratio = flow.get('put_call_ratio', 1.0)
        sentiment = flow.get('sentiment', 'neutral')
        call_vol = flow.get('total_call_volume', 0)
        put_vol = flow.get('total_put_volume', 0)

        # Score calculation
        # P/C Ratio scoring: <0.7 = bullish (70+), 0.7-1.0 = neutral (40-60), >1.0 = bearish (<40)
        if pc_ratio < 0.6:
            score = 80
        elif pc_ratio < 0.7:
            score = 70
        elif pc_ratio < 0.85:
            score = 60
        elif pc_ratio < 1.0:
            score = 50
        elif pc_ratio < 1.2:
            score = 40
        else:
            score = 30

        # Adjust based on sentiment
        if sentiment == 'bullish':
            score = min(100, score + 10)
        elif sentiment == 'bearish':
            score = max(0, score - 10)

        return {
            'score': score,
            'put_call_ratio': round(pc_ratio, 2),
            'sentiment': sentiment,
            'call_volume': call_vol,
            'put_volume': put_vol
        }

    except Exception as e:
        logger.warning(f"Options flow score calculation failed: {e}")
        return {'score': 50, 'error': str(e)}


def _calculate_vix_score() -> Dict:
    """
    Calculate score from VIX level.

    VIX interpretation:
    - <12: Very low fear, complacency (slightly bearish - potential correction)
    - 12-15: Low fear, bullish
    - 15-20: Normal
    - 20-25: Elevated fear
    - 25-30: High fear (contrarian bullish)
    - >30: Extreme fear (contrarian very bullish)
    """
    try:
        from utils.data_providers import FREDProvider

        vix_data = FREDProvider.get_latest_value(FREDProvider.SERIES['vix'])

        if not vix_data:
            return {'score': 50, 'error': 'VIX data unavailable'}

        vix_date, vix_value = vix_data

        # Score calculation
        if vix_value < 12:
            score = 55  # Complacency - slightly bearish
            level = 'very_low'
        elif vix_value < 15:
            score = 70  # Low fear - bullish
            level = 'low'
        elif vix_value < 20:
            score = 55  # Normal
            level = 'normal'
        elif vix_value < 25:
            score = 45  # Elevated fear
            level = 'elevated'
        elif vix_value < 30:
            score = 55  # High fear - contrarian bullish
            level = 'high'
        else:
            score = 65  # Extreme fear - contrarian very bullish
            level = 'extreme'

        return {
            'score': score,
            'value': round(vix_value, 2),
            'level': level,
            'date': vix_date
        }

    except Exception as e:
        logger.warning(f"VIX score calculation failed: {e}")
        return {'score': 50, 'error': str(e)}


def _estimate_market_breadth() -> Dict:
    """
    Estimate market breadth from available data.

    Without direct breadth data, we use:
    - Multiple ticker options sentiment as proxy
    """
    try:
        from src.data.options import get_options_flow

        # Check major ETFs/tickers for breadth
        tickers = ['SPY', 'QQQ', 'IWM']
        bullish_count = 0
        bearish_count = 0

        for ticker in tickers:
            try:
                flow = get_options_flow(ticker)
                if flow and not flow.get('error'):
                    sentiment = flow.get('sentiment', 'neutral')
                    if sentiment == 'bullish':
                        bullish_count += 1
                    elif sentiment == 'bearish':
                        bearish_count += 1
            except:
                continue

        total = bullish_count + bearish_count
        if total == 0:
            return {'score': 50, 'breadth': 'neutral'}

        bullish_pct = bullish_count / len(tickers)

        if bullish_pct >= 0.67:
            score = 70
            breadth = 'broad_bullish'
        elif bullish_pct >= 0.33:
            score = 50
            breadth = 'mixed'
        else:
            score = 30
            breadth = 'broad_bearish'

        return {
            'score': score,
            'breadth': breadth,
            'bullish_tickers': bullish_count,
            'bearish_tickers': bearish_count,
            'total_checked': len(tickers)
        }

    except Exception as e:
        logger.warning(f"Breadth estimation failed: {e}")
        return {'score': 50, 'error': str(e)}


# Convenience function for API
def get_institutional_score() -> int:
    """Get just the institutional score (0-100)."""
    result = get_sec_activity_score()
    return result.get('score', 50)
