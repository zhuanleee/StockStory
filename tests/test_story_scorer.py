"""
Tests for Story-First Stock Scorer

Tests cover:
- Theme membership detection
- Theme heat calculation
- Catalyst detection
- News momentum tracking
- Sentiment analysis
- Social buzz aggregation
- Technical confirmation
- Story score calculation
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestThemeMembership:
    """Test theme membership detection"""

    @patch('src.scoring.story_scorer.HAS_THEME_REGISTRY', False)
    def test_get_theme_membership_hardcoded(self):
        """Test theme membership from hardcoded themes"""
        from src.scoring.story_scorer import get_theme_membership

        # Test AI infrastructure driver
        themes = get_theme_membership('NVDA')
        assert len(themes) > 0
        assert any(t['theme_id'] == 'ai_infrastructure' for t in themes)

        # Check role
        nvda_theme = next(t for t in themes if t['theme_id'] == 'ai_infrastructure')
        assert nvda_theme['role'] == 'driver'
        assert nvda_theme['stage'] == 'middle'

    @patch('src.scoring.story_scorer.HAS_THEME_REGISTRY', False)
    def test_get_theme_membership_beneficiary(self):
        """Test beneficiary role detection"""
        from src.scoring.story_scorer import get_theme_membership

        # SMCI is beneficiary of AI infrastructure
        themes = get_theme_membership('SMCI')
        assert len(themes) > 0

        smci_theme = next((t for t in themes if t['theme_id'] == 'ai_infrastructure'), None)
        assert smci_theme is not None
        assert smci_theme['role'] == 'beneficiary'

    @patch('src.scoring.story_scorer.HAS_THEME_REGISTRY', False)
    def test_get_theme_membership_multiple_themes(self):
        """Test stock in multiple themes"""
        from src.scoring.story_scorer import get_theme_membership

        # MSFT is in multiple themes (AI software, etc.)
        themes = get_theme_membership('MSFT')
        theme_ids = [t['theme_id'] for t in themes]

        # Should be in AI software as driver
        assert 'ai_software' in theme_ids

    @patch('src.scoring.story_scorer.HAS_THEME_REGISTRY', False)
    def test_get_theme_membership_no_theme(self):
        """Test stock not in any theme"""
        from src.scoring.story_scorer import get_theme_membership

        # Random ticker not in themes
        themes = get_theme_membership('XYZ_NONEXISTENT')
        assert len(themes) == 0


class TestThemeHeat:
    """Test theme heat calculation"""

    @patch('src.scoring.story_scorer.get_theme_membership')
    def test_calculate_theme_heat_driver(self, mock_membership):
        """Test theme heat for driver stock"""
        from src.scoring.story_scorer import calculate_theme_heat

        # Mock theme membership
        mock_membership.return_value = [{
            'theme_id': 'ai_infrastructure',
            'theme_name': 'AI Infrastructure',
            'role': 'driver',
            'stage': 'early',
            'is_learned': False
        }]

        result = calculate_theme_heat('TEST')

        assert result['score'] > 0
        assert len(result['themes']) == 1
        assert result['hottest_theme'] == 'AI Infrastructure'
        assert result['role'] == 'driver'

    @patch('src.scoring.story_scorer.get_theme_membership')
    def test_calculate_theme_heat_early_stage_boost(self, mock_membership):
        """Test early stage theme gets boost"""
        from src.scoring.story_scorer import calculate_theme_heat

        # Early stage theme
        mock_membership.return_value = [{
            'theme_id': 'nuclear_renaissance',
            'theme_name': 'Nuclear Renaissance',
            'role': 'driver',
            'stage': 'early',
            'is_learned': False
        }]

        early_result = calculate_theme_heat('TEST_EARLY')

        # Middle stage theme
        mock_membership.return_value = [{
            'theme_id': 'ai_infrastructure',
            'theme_name': 'AI Infrastructure',
            'role': 'driver',
            'stage': 'middle',
            'is_learned': False
        }]

        middle_result = calculate_theme_heat('TEST_MIDDLE')

        # Early stage should score higher (same role, earlier stage)
        assert early_result['score'] >= middle_result['score']

    @patch('src.scoring.story_scorer.get_theme_membership')
    def test_calculate_theme_heat_no_themes(self, mock_membership):
        """Test theme heat when no themes"""
        from src.scoring.story_scorer import calculate_theme_heat

        mock_membership.return_value = []

        result = calculate_theme_heat('TEST')

        assert result['score'] == 0
        assert len(result['themes']) == 0
        assert result['hottest_theme'] is None


class TestCatalystDetection:
    """Test catalyst detection"""

    def test_detect_catalysts_earnings_keyword(self):
        """Test earnings catalyst detection from news"""
        from src.scoring.story_scorer import detect_catalysts

        news = [
            {
                'title': 'Company XYZ reports upcoming earnings next week',
                'summary': 'Earnings preview for Q4 2026',
                'pubDate': datetime.now().isoformat()
            }
        ]

        result = detect_catalysts('XYZ', news_data=news)

        assert result['score'] > 0
        assert len(result['catalysts']) > 0
        assert result['catalysts'][0]['type'] == 'earnings'

    def test_detect_catalysts_fda_keyword(self):
        """Test FDA catalyst detection"""
        from src.scoring.story_scorer import detect_catalysts

        news = [
            {
                'title': 'FDA approval expected for new drug',
                'summary': 'PDUFA date set for next month',
                'pubDate': datetime.now().isoformat()
            }
        ]

        result = detect_catalysts('BIOTECH', news_data=news)

        assert len(result['catalysts']) > 0
        # Should detect FDA catalyst
        catalyst_types = [c['type'] for c in result['catalysts']]
        assert 'fda' in catalyst_types

    def test_detect_catalysts_merger(self):
        """Test merger catalyst detection"""
        from src.scoring.story_scorer import detect_catalysts

        news = [
            {
                'title': 'Company announces merger with competitor',
                'summary': 'Major acquisition deal announced',
                'pubDate': datetime.now().isoformat()
            }
        ]

        result = detect_catalysts('TICKER', news_data=news)

        catalyst_types = [c['type'] for c in result['catalysts']]
        assert 'merger' in catalyst_types

    def test_detect_catalysts_no_news(self):
        """Test catalyst detection with no news"""
        from src.scoring.story_scorer import detect_catalysts

        result = detect_catalysts('XYZ', news_data=[])

        assert result['score'] == 0
        assert len(result['catalysts']) == 0
        assert result['next_catalyst'] is None


class TestNewsMomentum:
    """Test news momentum calculation"""

    def test_calculate_news_momentum_accelerating(self):
        """Test accelerating news momentum"""
        from src.scoring.story_scorer import calculate_news_momentum

        # Create news with recent spike (3 articles in last 24h, 1 in previous days)
        now = datetime.now()
        news = [
            {'title': 'News 1', 'pubDate': now.isoformat()},
            {'title': 'News 2', 'pubDate': (now - timedelta(hours=6)).isoformat()},
            {'title': 'News 3', 'pubDate': (now - timedelta(hours=12)).isoformat()},
            {'title': 'News 4', 'pubDate': (now - timedelta(days=5)).isoformat()},
        ]

        result = calculate_news_momentum('TICKER', news_data=news)

        assert result['momentum'] == 'accelerating'
        assert result['score'] >= 60
        assert result['last_24h'] == 3

    def test_calculate_news_momentum_stable(self):
        """Test stable news momentum"""
        from src.scoring.story_scorer import calculate_news_momentum

        # Even distribution
        now = datetime.now()
        news = [
            {'title': 'News 1', 'pubDate': (now - timedelta(days=1)).isoformat()},
            {'title': 'News 2', 'pubDate': (now - timedelta(days=2)).isoformat()},
            {'title': 'News 3', 'pubDate': (now - timedelta(days=4)).isoformat()},
            {'title': 'News 4', 'pubDate': (now - timedelta(days=6)).isoformat()},
        ]

        result = calculate_news_momentum('TICKER', news_data=news)

        assert result['momentum'] in ['stable', 'declining', 'accelerating']
        assert result['article_count'] == 4

    def test_calculate_news_momentum_no_news(self):
        """Test news momentum with no news"""
        from src.scoring.story_scorer import calculate_news_momentum

        result = calculate_news_momentum('TICKER', news_data=[])

        assert result['score'] == 30
        assert result['article_count'] == 0
        assert result['momentum'] == 'unknown'


class TestSentimentAnalysis:
    """Test sentiment analysis"""

    @patch('src.scoring.story_scorer.HAS_DEEPSEEK_SENTIMENT', False)
    def test_calculate_sentiment_bullish(self):
        """Test bullish sentiment detection"""
        from src.scoring.story_scorer import calculate_sentiment_score

        news = [
            {'title': 'Stock surges on record earnings beat', 'summary': 'Strong growth continues'},
            {'title': 'Analysts upgrade to buy on bullish outlook', 'summary': 'Positive momentum'},
            {'title': 'Company raises guidance, stock jumps', 'summary': 'Exceeds expectations'},
        ]

        result = calculate_sentiment_score('TICKER', news_data=news)

        assert result['score'] > 50  # Bullish = > 50
        assert result['sentiment'] in ['bullish', 'neutral']
        assert result['bullish_count'] >= 2

    @patch('src.scoring.story_scorer.HAS_DEEPSEEK_SENTIMENT', False)
    def test_calculate_sentiment_bearish(self):
        """Test bearish sentiment detection"""
        from src.scoring.story_scorer import calculate_sentiment_score

        news = [
            {'title': 'Stock plunges on earnings miss', 'summary': 'Weak results disappoint'},
            {'title': 'Downgrade to sell on concerns', 'summary': 'Negative outlook'},
            {'title': 'Company cuts guidance, shares fall', 'summary': 'Underperform warning'},
        ]

        result = calculate_sentiment_score('TICKER', news_data=news)

        assert result['score'] < 50  # Bearish = < 50
        assert result['sentiment'] in ['bearish', 'neutral']
        assert result['bearish_count'] >= 2

    @patch('src.scoring.story_scorer.HAS_DEEPSEEK_SENTIMENT', False)
    def test_calculate_sentiment_neutral(self):
        """Test neutral sentiment"""
        from src.scoring.story_scorer import calculate_sentiment_score

        news = [
            {'title': 'Company reports quarterly results', 'summary': 'Numbers in line with expectations'},
        ]

        result = calculate_sentiment_score('TICKER', news_data=news)

        # Should be around neutral (40-60 range)
        assert 40 <= result['score'] <= 60
        assert result['confidence'] in ['low', 'medium']


class TestSocialBuzz:
    """Test social buzz aggregation"""

    @patch('src.scoring.story_scorer.fetch_stocktwits_sentiment')
    @patch('src.scoring.story_scorer.fetch_sec_filings')
    @patch('src.scoring.story_scorer._fetch_reddit_direct')
    @patch('src.scoring.story_scorer.fetch_x_sentiment')
    @patch('src.scoring.story_scorer.fetch_google_trends')
    def test_get_social_buzz_score_high(self, mock_gt, mock_x, mock_reddit, mock_sec, mock_st):
        """Test high social buzz score"""
        from src.scoring.story_scorer import get_social_buzz_score

        # Mock high volume responses
        mock_st.return_value = {
            'sentiment': 'bullish',
            'message_volume': 500,
            'trending': True,
            'bullish_count': 100,
            'bearish_count': 20
        }

        mock_reddit.return_value = {
            'mention_count': 15,
            'total_score': 5000,
            'sentiment': 'bullish'
        }

        mock_x.return_value = {
            'post_count': 20,
            'engagement_score': 80,
            'sentiment': 'bullish'
        }

        mock_sec.return_value = {
            'has_8k': True,
            'insider_activity': True
        }

        mock_gt.return_value = {
            'score': 85,
            'is_breakout': True,
            'trend_pct': 50
        }

        result = get_social_buzz_score('TICKER')

        assert result['buzz_score'] > 50
        assert result['trending'] is True
        assert 'stocktwits' in result
        assert 'reddit' in result
        assert 'x_twitter' in result
        assert 'google_trends' in result

    @patch('src.scoring.story_scorer.fetch_stocktwits_sentiment')
    @patch('src.scoring.story_scorer.fetch_sec_filings')
    @patch('src.scoring.story_scorer._fetch_reddit_direct')
    @patch('src.scoring.story_scorer.fetch_x_sentiment')
    @patch('src.scoring.story_scorer.fetch_google_trends')
    def test_get_social_buzz_score_low(self, mock_gt, mock_x, mock_reddit, mock_sec, mock_st):
        """Test low social buzz score"""
        from src.scoring.story_scorer import get_social_buzz_score

        # Mock low volume responses
        mock_st.return_value = {
            'sentiment': 'neutral',
            'message_volume': 5,
            'trending': False
        }

        mock_reddit.return_value = {
            'mention_count': 0,
            'total_score': 0,
            'sentiment': 'quiet'
        }

        mock_x.return_value = {
            'post_count': 0,
            'engagement_score': 0,
            'sentiment': 'unknown'
        }

        mock_sec.return_value = {
            'has_8k': False,
            'insider_activity': False
        }

        mock_gt.return_value = {
            'score': 30,
            'is_breakout': False,
            'trend_pct': -10
        }

        result = get_social_buzz_score('TICKER')

        assert result['buzz_score'] < 30
        assert result['trending'] is False


class TestTechnicalConfirmation:
    """Test technical analysis confirmation"""

    @patch('src.scoring.story_scorer.HAS_POLYGON', False)
    def test_calculate_technical_confirmation_no_data(self):
        """Test technical confirmation with no data"""
        from src.scoring.story_scorer import calculate_technical_confirmation

        result = calculate_technical_confirmation('TICKER', price_data=None)

        assert result['score'] == 50  # Default neutral
        assert result['rs'] == 0
        assert result['trend'] == 'unknown'

    def test_calculate_technical_confirmation_strong_uptrend(self):
        """Test strong uptrend detection"""
        import pandas as pd
        from src.scoring.story_scorer import calculate_technical_confirmation

        # Create mock price data - strong uptrend
        dates = pd.date_range(end=datetime.now(), periods=60)
        # Uptrending prices
        closes = [100 + i * 0.5 for i in range(60)]
        volumes = [1000000] * 60

        df = pd.DataFrame({
            'Close': closes,
            'Volume': volumes
        }, index=dates)

        result = calculate_technical_confirmation('TICKER', price_data=df)

        assert result['trend'] in ['strong_up', 'up']
        assert result['score'] > 50
        assert result['above_20sma'] is True
        assert result['above_50sma'] is True

    def test_calculate_technical_confirmation_downtrend(self):
        """Test downtrend detection"""
        import pandas as pd
        from src.scoring.story_scorer import calculate_technical_confirmation

        # Create mock price data - downtrend
        dates = pd.date_range(end=datetime.now(), periods=60)
        # Downtrending prices
        closes = [100 - i * 0.5 for i in range(60)]
        volumes = [1000000] * 60

        df = pd.DataFrame({
            'Close': closes,
            'Volume': volumes
        }, index=dates)

        result = calculate_technical_confirmation('TICKER', price_data=df)

        assert result['trend'] in ['down', 'neutral']
        assert result['score'] < 70  # Not strong


class TestStoryScoreCalculation:
    """Test complete story score calculation"""

    @patch('src.scoring.story_scorer.get_social_buzz_score')
    @patch('src.scoring.story_scorer.calculate_technical_confirmation')
    @patch('src.scoring.story_scorer.calculate_sentiment_score')
    @patch('src.scoring.story_scorer.calculate_news_momentum')
    @patch('src.scoring.story_scorer.detect_catalysts')
    @patch('src.scoring.story_scorer.calculate_theme_heat')
    def test_calculate_story_score_strong_story(
        self, mock_theme, mock_catalyst, mock_news, mock_sentiment, mock_technical, mock_social
    ):
        """Test strong story score calculation"""
        from src.scoring.story_scorer import calculate_story_score

        # Mock strong signals across all components
        mock_theme.return_value = {
            'score': 90,
            'themes': [{'theme_id': 'ai_infrastructure', 'theme_name': 'AI Infrastructure', 'role': 'driver', 'stage': 'early'}],
            'hottest_theme': 'AI Infrastructure',
            'role': 'driver'
        }

        mock_catalyst.return_value = {
            'score': 80,
            'catalysts': [{'type': 'earnings', 'days_away': 5}],
            'next_catalyst': {'type': 'earnings'}
        }

        mock_news.return_value = {
            'score': 75,
            'article_count': 15,
            'momentum': 'accelerating'
        }

        mock_sentiment.return_value = {
            'score': 70,
            'sentiment': 'bullish',
            'confidence': 'high'
        }

        mock_technical.return_value = {
            'score': 80,
            'rs': 15,
            'trend': 'strong_up',
            'volume': 2.0
        }

        mock_social.return_value = {
            'buzz_score': 75,
            'trending': True,
            'stocktwits': {},
            'reddit': {},
            'sec': {'has_8k': True}
        }

        result = calculate_story_score('STRONG_TICKER', include_social=True)

        assert result['story_score'] >= 70
        assert result['story_strength'] in ['STRONG_STORY', 'GOOD_STORY']
        assert result['has_theme'] is True
        assert result['has_catalyst'] is True
        assert result['is_trending'] is True

    @patch('src.scoring.story_scorer.get_social_buzz_score')
    @patch('src.scoring.story_scorer.calculate_technical_confirmation')
    @patch('src.scoring.story_scorer.calculate_sentiment_score')
    @patch('src.scoring.story_scorer.calculate_news_momentum')
    @patch('src.scoring.story_scorer.detect_catalysts')
    @patch('src.scoring.story_scorer.calculate_theme_heat')
    def test_calculate_story_score_weak_story(
        self, mock_theme, mock_catalyst, mock_news, mock_sentiment, mock_technical, mock_social
    ):
        """Test weak story score calculation"""
        from src.scoring.story_scorer import calculate_story_score

        # Mock weak signals
        mock_theme.return_value = {
            'score': 0,
            'themes': [],
            'hottest_theme': None,
            'role': None
        }

        mock_catalyst.return_value = {
            'score': 0,
            'catalysts': [],
            'next_catalyst': None
        }

        mock_news.return_value = {
            'score': 30,
            'article_count': 2,
            'momentum': 'quiet'
        }

        mock_sentiment.return_value = {
            'score': 50,
            'sentiment': 'neutral',
            'confidence': 'low'
        }

        mock_technical.return_value = {
            'score': 40,
            'rs': -5,
            'trend': 'down',
            'volume': 0.5
        }

        mock_social.return_value = {
            'buzz_score': 10,
            'trending': False,
            'stocktwits': {},
            'reddit': {},
            'sec': {}
        }

        result = calculate_story_score('WEAK_TICKER', include_social=True)

        assert result['story_score'] < 50
        assert result['story_strength'] in ['WEAK_STORY', 'MODERATE_STORY']
        assert result['has_theme'] is False
        assert result['has_catalyst'] is False


class TestThemeStocks:
    """Test theme stock retrieval"""

    def test_get_theme_stocks_valid_theme(self):
        """Test retrieving stocks for valid theme"""
        from src.scoring.story_scorer import get_theme_stocks

        result = get_theme_stocks('ai_infrastructure')

        assert result is not None
        assert result['theme_id'] == 'ai_infrastructure'
        assert result['name'] == 'AI Infrastructure'
        assert len(result['drivers']) > 0
        assert 'NVDA' in result['drivers']
        assert len(result['all_tickers']) > 0

    def test_get_theme_stocks_invalid_theme(self):
        """Test retrieving invalid theme"""
        from src.scoring.story_scorer import get_theme_stocks

        result = get_theme_stocks('nonexistent_theme')

        assert result is None

    def test_get_all_theme_tickers(self):
        """Test getting all theme tickers"""
        from src.scoring.story_scorer import get_all_theme_tickers

        all_tickers = get_all_theme_tickers()

        assert len(all_tickers) > 0
        assert 'NVDA' in all_tickers
        assert 'MSFT' in all_tickers

    def test_get_early_stage_themes(self):
        """Test getting early stage themes"""
        from src.scoring.story_scorer import get_early_stage_themes

        early_themes = get_early_stage_themes()

        assert len(early_themes) > 0
        # Nuclear Renaissance should be early stage
        theme_ids = [t['theme_id'] for t in early_themes]
        assert 'nuclear_renaissance' in theme_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
