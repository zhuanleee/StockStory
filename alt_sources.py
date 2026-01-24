#!/usr/bin/env python3
"""
Alternative Sources - Podcasts, Newsletters, Influencers

Scrapes early signals from:
1. YouTube transcripts (All-In, Bankless, etc.)
2. Substack RSS feeds
3. Podcast show notes
4. Finance Twitter/X influencers
"""

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

# Popular finance podcasts (YouTube channels)
PODCAST_YOUTUBE = {
    # Tech/VC Investing
    'All-In Podcast': 'UCESLZhusAkFfsNsApnjF_Cg',
    'Lex Fridman': 'UCSHZKyawb77ixDdsGog4iWA',
    'Patrick Boyle': 'UCASM0cgfkJxQ1ICmRcdqXSQ',
    'The Compound': 'UC66rQ0kNBUbGwYiJhwESrJA',
    'Odd Lots Bloomberg': 'UCIALMKvObZNtJ6AmdCLP7Lg',

    # Crypto
    'Bankless': 'UCAl9Ld79qaZxp9JzEOwd3aA',
    'Real Vision': 'UCKMXV-VqgVsVXOgo5vPTxuQ',
    'The Pomp Podcast': 'UCnzTeMXpYNyABqAMQCDlHbQ',

    # Macro/Economics
    'Wealthion': 'UCie_J2xi2RoYBR0lBNIbNfQ',
    'Kitco NEWS': 'UCECOl04AVzs3DCWT4I_8qzw',
    'Peter Schiff': 'UCw9awFTR92VWNfh4ZPjO_RA',
}

# Substack newsletters (RSS feeds)
SUBSTACK_FEEDS = [
    # Tech Strategy (Tier 1)
    ('Stratechery', 'https://stratechery.com/feed/'),
    ('SemiAnalysis', 'https://semianalysis.com/feed/'),
    ('Platformer', 'https://www.platformer.news/feed'),

    # Finance/Investing (Tier 1-2)
    ('The Diff', 'https://diff.substack.com/feed'),
    ('Doomberg', 'https://doomberg.substack.com/feed'),
    ('Net Interest', 'https://netinterest.substack.com/feed'),
    ('The Pomp Letter', 'https://pomp.substack.com/feed'),
    ('Kyla Scanlon', 'https://kylascanlon.substack.com/feed'),

    # Tech/Startup
    ('Not Boring', 'https://www.notboring.co/feed'),
    ('The Generalist', 'https://www.readthegeneralist.com/feed'),
    ('Lenny Newsletter', 'https://www.lennysnewsletter.com/feed'),

    # Macro/Economics
    ('The Macro Compass', 'https://themacrocompass.substack.com/feed'),
    ('Apricitas Economics', 'https://www.apricitas.io/feed'),

    # AI/Tech Deep Dives
    ('AI Snake Oil', 'https://aisnakeoil.substack.com/feed'),
    ('The Batch', 'https://www.deeplearning.ai/the-batch/feed'),
    ('Import AI', 'https://importai.substack.com/feed'),

    # Energy/Commodities
    ('Energy Flux', 'https://energyflux.substack.com/feed'),
    ('Goehring & Rozencwajg', 'https://blog.gorozen.com/feed'),

    # China/Asia
    ('ChinaTalk', 'https://chinatalk.substack.com/feed'),
    ('Sinocism', 'https://sinocism.com/feed'),
]

# Podcast RSS feeds (for show notes)
PODCAST_RSS = [
    # Tech/VC
    ('All-In Podcast', 'https://feeds.megaphone.fm/all-in-with-chamath-jason-sacks-friedberg'),
    ('Acquired', 'https://feeds.simplecast.com/i2F5rPab'),
    ('20VC', 'https://feeds.megaphone.fm/the-twenty-minute-vc-venture-capital'),

    # Investing
    ('Invest Like the Best', 'https://feeds.simplecast.com/JGE3yC0V'),
    ('The Prof G Pod', 'https://feeds.megaphone.fm/profgpod'),
    ('Motley Fool Money', 'https://feeds.megaphone.fm/motleyfoolmoney'),
    ('Odd Lots', 'https://feeds.bloomberg.com/BLM6611713481'),
    ('Macro Voices', 'https://www.macrovoices.com/feed'),

    # Business/Entrepreneurship
    ('My First Million', 'https://feeds.megaphone.fm/HSW2674591386'),
    ('How I Built This', 'https://feeds.npr.org/510313/podcast.xml'),
    ('Founders', 'https://feeds.transistor.fm/founders'),

    # Markets/Trading
    ('Chat With Traders', 'https://feeds.megaphone.fm/chatwithtraders'),
    ('Top Traders Unplugged', 'https://feeds.megaphone.fm/TTU'),
    ('Market Huddle', 'https://feeds.libsyn.com/418831/rss'),

    # Crypto
    ('Bankless', 'https://feeds.simplecast.com/lGK0X2cY'),
    ('Unchained', 'https://unchainedpodcast.com/feed/'),

    # Real Estate
    ('BiggerPockets', 'https://www.omnycontent.com/d/playlist/06e8a6a6-19a7-4e21-8e3f-acf10032f176/a87a82d2-5ca5-4f2e-b72d-adf7014cc2c7/83aa4c6b-ccaa-4f62-96a2-adf7014cc2dd/podcast.rss'),
]

# Finance influencers (Twitter handles)
FINANCE_INFLUENCERS = [
    # All-In crew
    'chamath', 'Jason', 'friedberg', 'DavidSacks',
    # Macro
    'LynAldenContact', 'DiMartinoBooth', 'JeffSnider_AIP',
    # Tech/VC
    'benedictevans', 'pmarca', 'balaborr',
    # Trading
    'OptionsHawk', 'traborr', 'VolatilityGuy',
    # Crypto
    'APompliano', 'RyanSAdams', 'TrustlessState',
]

# Finance influencers (Twitter handles to check via Nitter)
FINANCE_INFLUENCERS = [
    'chaaborr',      # Chamath
    'Jason',         # Jason Calacanis
    'friedberg',     # David Friedberg
    'saxena',        # David Sacks
    'elaboratewrt',  # Elaborate
    'GavinSBaker',   # Gavin Baker
    'haborr',        # Brad Gerstner
]


# ============================================================
# YOUTUBE TRANSCRIPT SCRAPING
# ============================================================

def get_youtube_video_ids(channel_id, max_videos=5):
    """Get recent video IDs from a YouTube channel."""
    try:
        # Use RSS feed to get recent videos
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        # Parse RSS
        root = ET.fromstring(response.content)
        ns = {'yt': 'http://www.youtube.com/xml/schemas/2015',
              'atom': 'http://www.w3.org/2005/Atom'}

        videos = []
        entries = root.findall('.//atom:entry', ns)

        for entry in entries[:max_videos]:
            video_id = entry.find('yt:videoId', ns)
            title = entry.find('atom:title', ns)
            published = entry.find('atom:published', ns)

            if video_id is not None and title is not None:
                videos.append({
                    'id': video_id.text,
                    'title': title.text,
                    'published': published.text if published is not None else '',
                })

        return videos
    except Exception as e:
        return []


def get_youtube_transcript(video_id):
    """
    Get transcript/captions from YouTube video.
    Uses timedtext API (doesn't require API key).
    """
    try:
        # Try to get auto-generated captions
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        # Extract caption track URL from page
        # Look for "captionTracks" in the page source
        caption_pattern = r'"captionTracks":\[(.*?)\]'
        match = re.search(caption_pattern, response.text)

        if not match:
            return None

        # Extract baseUrl for English captions
        base_url_pattern = r'"baseUrl":"(.*?)"'
        urls = re.findall(base_url_pattern, match.group(1))

        if not urls:
            return None

        # Get the transcript
        caption_url = urls[0].replace('\\u0026', '&')
        caption_response = requests.get(caption_url, timeout=10)

        if caption_response.status_code != 200:
            return None

        # Parse XML transcript
        root = ET.fromstring(caption_response.content)
        texts = root.findall('.//text')

        transcript = ' '.join([t.text for t in texts if t.text])
        return transcript[:5000]  # Limit length

    except Exception as e:
        return None


def scrape_podcast_transcripts():
    """Scrape transcripts from popular finance podcasts on YouTube."""
    all_content = []

    for name, channel_id in PODCAST_YOUTUBE.items():
        try:
            videos = get_youtube_video_ids(channel_id, max_videos=3)

            for video in videos:
                # Check if video is recent (within 7 days)
                try:
                    pub_date = datetime.fromisoformat(video['published'].replace('Z', '+00:00'))
                    if pub_date < datetime.now(pub_date.tzinfo) - timedelta(days=7):
                        continue
                except:
                    pass

                # For now, just use title as content (transcript is slow)
                all_content.append({
                    'source': name,
                    'type': 'podcast',
                    'title': video['title'],
                    'content': video['title'],  # Use title for quick analysis
                    'video_id': video['id'],
                })
        except:
            continue

    return all_content


# ============================================================
# SUBSTACK / NEWSLETTER SCRAPING
# ============================================================

def scrape_substack_feed(name, feed_url):
    """Scrape recent posts from a Substack RSS feed."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        posts = []
        for item in items[:5]:
            title = item.find('title')
            description = item.find('description')
            pub_date = item.find('pubDate')

            if title is not None:
                # Check if recent (within 7 days)
                try:
                    if pub_date is not None:
                        # Parse date like "Mon, 20 Jan 2026 12:00:00 GMT"
                        date_str = pub_date.text
                        # Simple check - just look for recent month/year
                        pass  # Skip date check for now
                except:
                    pass

                # Clean description HTML
                desc_text = ''
                if description is not None and description.text:
                    desc_text = re.sub(r'<[^>]+>', '', description.text)[:500]

                posts.append({
                    'source': name,
                    'type': 'newsletter',
                    'title': title.text,
                    'content': desc_text,
                })

        return posts
    except Exception as e:
        return []


def scrape_all_newsletters():
    """Scrape all configured newsletter feeds."""
    all_posts = []

    for name, feed_url in SUBSTACK_FEEDS:
        try:
            posts = scrape_substack_feed(name, feed_url)
            all_posts.extend(posts)
        except:
            continue

    return all_posts


# ============================================================
# PODCAST SHOW NOTES
# ============================================================

def scrape_podcast_rss(name, feed_url):
    """Scrape show notes from podcast RSS feed."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        episodes = []
        for item in items[:3]:  # Last 3 episodes
            title = item.find('title')
            description = item.find('description')

            if title is not None:
                desc_text = ''
                if description is not None and description.text:
                    desc_text = re.sub(r'<[^>]+>', '', description.text)[:1000]

                episodes.append({
                    'source': name,
                    'type': 'podcast_notes',
                    'title': title.text,
                    'content': desc_text,
                })

        return episodes
    except Exception as e:
        return []


def scrape_all_podcast_notes():
    """Scrape show notes from all configured podcasts."""
    all_episodes = []

    for name, feed_url in PODCAST_RSS:
        try:
            episodes = scrape_podcast_rss(name, feed_url)
            all_episodes.extend(episodes)
        except:
            continue

    return all_episodes


# ============================================================
# AGGREGATE ALL ALTERNATIVE SOURCES
# ============================================================

def aggregate_alt_sources():
    """
    Aggregate content from all alternative sources.
    Returns list of content items with source info.
    """
    all_content = []

    # Podcasts (YouTube titles)
    try:
        podcasts = scrape_podcast_transcripts()
        all_content.extend(podcasts)
    except:
        pass

    # Newsletters
    try:
        newsletters = scrape_all_newsletters()
        all_content.extend(newsletters)
    except:
        pass

    # Podcast show notes
    try:
        podcast_notes = scrape_all_podcast_notes()
        all_content.extend(podcast_notes)
    except:
        pass

    return all_content


def extract_themes_from_alt_sources(content_list):
    """
    Extract potential themes/tickers from alternative source content.
    Returns themes with source attribution.
    """
    # Common stock tickers to look for
    ticker_pattern = r'\b([A-Z]{2,5})\b'

    # Theme keywords
    theme_keywords = {
        'ai': ['artificial intelligence', 'ai ', 'machine learning', 'llm', 'chatgpt', 'gpt'],
        'nuclear': ['nuclear', 'uranium', 'smr', 'nuclear power'],
        'crypto': ['bitcoin', 'crypto', 'ethereum', 'btc'],
        'chips': ['semiconductor', 'chips', 'gpu', 'nvidia', 'tsmc'],
        'energy': ['energy', 'power grid', 'electricity', 'utilities'],
        'obesity': ['glp-1', 'ozempic', 'wegovy', 'weight loss'],
        'robotics': ['robot', 'humanoid', 'automation', 'optimus'],
        'space': ['space', 'rocket', 'satellite', 'starlink'],
        'rates': ['interest rate', 'fed', 'powell', 'rate cut'],
    }

    theme_mentions = defaultdict(list)
    ticker_mentions = defaultdict(list)

    for item in content_list:
        text = (item.get('title', '') + ' ' + item.get('content', '')).lower()
        source = item.get('source', 'Unknown')

        # Check for theme keywords
        for theme, keywords in theme_keywords.items():
            for kw in keywords:
                if kw in text:
                    theme_mentions[theme].append({
                        'source': source,
                        'type': item.get('type'),
                        'title': item.get('title', '')[:80],
                    })
                    break

        # Extract tickers mentioned
        upper_text = item.get('title', '') + ' ' + item.get('content', '')
        tickers = re.findall(ticker_pattern, upper_text)

        # Filter to likely stock tickers (exclude common words)
        skip_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL',
                      'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HAS',
                      'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE',
                      'WAY', 'WHO', 'BOY', 'DID', 'GET', 'LET', 'PUT', 'SAY',
                      'SHE', 'TOO', 'USE', 'RSS', 'CEO', 'CFO', 'IPO', 'ETF'}

        for ticker in tickers:
            if ticker not in skip_words and len(ticker) >= 2:
                ticker_mentions[ticker].append({
                    'source': source,
                    'type': item.get('type'),
                })

    return {
        'themes': dict(theme_mentions),
        'tickers': dict(ticker_mentions),
        'total_items': len(content_list),
    }


def format_alt_sources_report(analysis):
    """Format alternative sources analysis for Telegram."""
    msg = "📻 *PODCAST & NEWSLETTER INTEL*\n\n"

    # Theme mentions
    themes = analysis.get('themes', {})
    if themes:
        msg += "*🎯 THEMES DISCUSSED:*\n"
        for theme, mentions in sorted(themes.items(), key=lambda x: -len(x[1]))[:6]:
            sources = set(m['source'] for m in mentions)
            msg += f"• *{theme.upper()}* ({len(mentions)} mentions)\n"
            msg += f"  _Sources: {', '.join(list(sources)[:3])}_\n"
        msg += "\n"

    # Top tickers mentioned
    tickers = analysis.get('tickers', {})
    if tickers:
        top_tickers = sorted(tickers.items(), key=lambda x: -len(x[1]))[:10]
        msg += "*📈 TICKERS MENTIONED:*\n"
        ticker_str = ', '.join([f"`{t}` ({len(m)})" for t, m in top_tickers])
        msg += ticker_str + "\n\n"

    msg += f"_Scanned {analysis.get('total_items', 0)} items from podcasts & newsletters_"

    return msg


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("Scraping alternative sources...")
    content = aggregate_alt_sources()
    print(f"Found {len(content)} items")

    analysis = extract_themes_from_alt_sources(content)
    print(format_alt_sources_report(analysis))
