#!/usr/bin/env python3
"""
Dynamic Theme Manager with AI Discovery and Lifecycle Management

Features:
1. Config-based themes (editable JSON on Modal volume)
2. AI discovery of emerging themes (DeepSeek/xAI)
3. Automatic lifecycle management (promote/archive)
4. Manual override via Telegram commands
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils import get_logger

logger = get_logger(__name__)

# Default path for theme config (can be overridden for Modal volume)
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "themes_config.json"
MODAL_VOLUME_PATH = "/data/themes_config.json"

# Theme status constants
STATUS_KNOWN = "known"        # Stable, manually added or promoted
STATUS_EMERGING = "emerging"  # AI-detected, needs validation
STATUS_ARCHIVED = "archived"  # Stale, no recent mentions


def get_config_path() -> Path:
    """Get the appropriate config path (Modal volume or local)."""
    if os.path.exists("/data"):
        return Path(MODAL_VOLUME_PATH)
    return DEFAULT_CONFIG_PATH


def get_default_themes() -> Dict[str, Any]:
    """Return default themes (current hardcoded ones as seed data)."""
    return {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "themes": {
            "AI_INFRASTRUCTURE": {
                "name": "AI Infrastructure",
                "status": STATUS_KNOWN,
                "keywords": ["nvidia", "nvda", "ai chip", "gpu", "data center", "artificial intelligence", "chatgpt", "openai", "llm", "inference", "ai server"],
                "tickers": ["NVDA", "AMD", "AVGO", "MRVL", "TSM", "SMCI", "ARM", "DELL"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "HBM_MEMORY": {
                "name": "HBM Memory",
                "status": STATUS_KNOWN,
                "keywords": ["hbm", "high bandwidth memory", "micron", "sk hynix", "memory", "dram", "hbm3", "hbm4"],
                "tickers": ["MU", "WDC", "STX", "LRCX"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "SEMICONDUCTOR": {
                "name": "Semiconductor",
                "status": STATUS_KNOWN,
                "keywords": ["semiconductor", "chip", "foundry", "tsmc", "asml", "amd", "intel", "fab", "wafer"],
                "tickers": ["NVDA", "AMD", "INTC", "TSM", "ASML", "AMAT", "LRCX", "KLAC", "ON", "NXPI"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "GLP1_OBESITY": {
                "name": "GLP-1 Obesity",
                "status": STATUS_KNOWN,
                "keywords": ["glp-1", "ozempic", "wegovy", "mounjaro", "obesity", "weight loss", "eli lilly", "novo nordisk", "zepbound"],
                "tickers": ["LLY", "NVO", "AMGN", "VKTX", "PFE"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "NUCLEAR": {
                "name": "Nuclear",
                "status": STATUS_KNOWN,
                "keywords": ["nuclear", "uranium", "smr", "small modular reactor", "constellation", "cameco", "nuclear power", "reactor"],
                "tickers": ["CEG", "VST", "CCJ", "UEC", "SMR", "OKLO", "NRG"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "EV_BATTERY": {
                "name": "EV Battery",
                "status": STATUS_KNOWN,
                "keywords": ["ev", "electric vehicle", "tesla", "battery", "lithium", "charging", "solid state"],
                "tickers": ["TSLA", "RIVN", "LCID", "ALB", "SQM", "LAC", "QS"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "CRYPTO_BITCOIN": {
                "name": "Crypto Bitcoin",
                "status": STATUS_KNOWN,
                "keywords": ["bitcoin", "crypto", "btc", "ethereum", "coinbase", "microstrategy", "etf", "btc etf"],
                "tickers": ["MSTR", "COIN", "MARA", "RIOT", "CLSK", "HUT"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "CLOUD_INFRASTRUCTURE": {
                "name": "Cloud Infrastructure",
                "status": STATUS_KNOWN,
                "keywords": ["cloud", "aws", "azure", "google cloud", "data center", "saas", "hyperscaler"],
                "tickers": ["AMZN", "MSFT", "GOOGL", "CRM", "NOW", "SNOW", "NET"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "CYBERSECURITY": {
                "name": "Cybersecurity",
                "status": STATUS_KNOWN,
                "keywords": ["cybersecurity", "security", "crowdstrike", "palo alto", "hack", "breach", "ransomware", "zero trust"],
                "tickers": ["CRWD", "PANW", "FTNT", "ZS", "S", "OKTA"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "QUANTUM": {
                "name": "Quantum",
                "status": STATUS_KNOWN,
                "keywords": ["quantum", "quantum computing", "ionq", "rigetti", "qubit", "supremacy"],
                "tickers": ["IONQ", "RGTI", "QBTS", "IBM", "GOOGL"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "ROBOTICS": {
                "name": "Robotics",
                "status": STATUS_KNOWN,
                "keywords": ["robot", "humanoid", "automation", "boston dynamics", "figure", "optimus"],
                "tickers": ["ISRG", "ROK", "TER", "ABB"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "SPACE": {
                "name": "Space",
                "status": STATUS_KNOWN,
                "keywords": ["space", "spacex", "rocket", "satellite", "starlink", "lunar", "orbit"],
                "tickers": ["RKLB", "LUNR", "ASTS", "SPCE", "BA"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "DEFENSE_AEROSPACE": {
                "name": "Defense Aerospace",
                "status": STATUS_KNOWN,
                "keywords": ["defense", "aerospace", "military", "pentagon", "lockheed", "raytheon", "boeing"],
                "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "HII"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "CHINA_TRADE": {
                "name": "China Trade",
                "status": STATUS_KNOWN,
                "keywords": ["china", "tariff", "trade war", "xi jinping", "beijing", "decoupling"],
                "tickers": ["BABA", "JD", "PDD", "NIO", "BIDU"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "INTEREST_RATES": {
                "name": "Interest Rates",
                "status": STATUS_KNOWN,
                "keywords": ["fed", "rate cut", "rate hike", "powell", "fomc", "inflation", "cpi"],
                "tickers": ["JPM", "BAC", "WFC", "GS", "MS"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "FINTECH_PAYMENTS": {
                "name": "Fintech Payments",
                "status": STATUS_KNOWN,
                "keywords": ["fintech", "payments", "visa", "mastercard", "paypal", "square", "digital payments"],
                "tickers": ["V", "MA", "PYPL", "SQ", "AFRM", "SOFI"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "STREAMING_MEDIA": {
                "name": "Streaming Media",
                "status": STATUS_KNOWN,
                "keywords": ["streaming", "netflix", "disney+", "hulu", "subscriber", "content"],
                "tickers": ["NFLX", "DIS", "WBD", "PARA", "ROKU"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "BIOTECH_PHARMA": {
                "name": "Biotech Pharma",
                "status": STATUS_KNOWN,
                "keywords": ["biotech", "fda", "approval", "trial", "drug", "pipeline", "clinical"],
                "tickers": ["MRNA", "REGN", "VRTX", "BIIB", "GILD", "BMY"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "REAL_ESTATE": {
                "name": "Real Estate",
                "status": STATUS_KNOWN,
                "keywords": ["real estate", "housing", "mortgage", "reit", "commercial", "homebuilder"],
                "tickers": ["AMT", "PLD", "CCI", "SPG", "DHI", "LEN"],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
            "EARNINGS_SEASON": {
                "name": "Earnings Season",
                "status": STATUS_KNOWN,
                "keywords": ["earnings", "beat", "miss", "guidance", "outlook", "eps"],
                "tickers": [],
                "discovered_at": "2024-01-01T00:00:00",
                "last_seen": datetime.now().isoformat(),
                "mention_count_7d": 0,
                "promoted_from_emerging": False,
            },
        },
        "ai_discovery": {
            "enabled": True,
            "last_run": None,
            "discovered_themes": [],
        },
        "lifecycle": {
            "auto_promote_after_days": 3,
            "auto_promote_min_mentions": 5,
            "auto_archive_after_days": 7,
        }
    }


class ThemeManager:
    """Manages theme configuration, discovery, and lifecycle."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or get_config_path()
        self._config = None
        self._load_config()

    def _load_config(self) -> None:
        """Load config from file or create default."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded theme config from {self.config_path}")
            else:
                self._config = get_default_themes()
                self._save_config()
                logger.info(f"Created default theme config at {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading theme config: {e}")
            self._config = get_default_themes()

    def _save_config(self) -> None:
        """Save config to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config["last_updated"] = datetime.now().isoformat()
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved theme config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving theme config: {e}")

    def reload(self) -> None:
        """Reload config from file (useful after Modal volume sync)."""
        self._load_config()

    # =========================================================================
    # Theme CRUD Operations
    # =========================================================================

    def get_all_themes(self, include_archived: bool = False) -> Dict[str, Any]:
        """Get all themes (optionally including archived)."""
        themes = self._config.get("themes", {})
        if include_archived:
            return themes
        return {k: v for k, v in themes.items() if v.get("status") != STATUS_ARCHIVED}

    def get_active_themes(self) -> Dict[str, Any]:
        """Get only known (active) themes."""
        return {k: v for k, v in self._config.get("themes", {}).items()
                if v.get("status") == STATUS_KNOWN}

    def get_emerging_themes(self) -> Dict[str, Any]:
        """Get AI-discovered emerging themes."""
        return {k: v for k, v in self._config.get("themes", {}).items()
                if v.get("status") == STATUS_EMERGING}

    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific theme by ID."""
        return self._config.get("themes", {}).get(theme_id)

    def add_theme(self, theme_id: str, name: str, keywords: List[str],
                  tickers: List[str], status: str = STATUS_KNOWN) -> bool:
        """Add a new theme manually."""
        theme_id = theme_id.upper().replace(" ", "_")

        if theme_id in self._config.get("themes", {}):
            logger.warning(f"Theme {theme_id} already exists")
            return False

        self._config["themes"][theme_id] = {
            "name": name,
            "status": status,
            "keywords": [k.lower() for k in keywords],
            "tickers": [t.upper() for t in tickers],
            "discovered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "mention_count_7d": 0,
            "promoted_from_emerging": status == STATUS_EMERGING,
        }
        self._save_config()
        logger.info(f"Added theme: {theme_id}")
        return True

    def update_theme(self, theme_id: str, **updates) -> bool:
        """Update an existing theme."""
        if theme_id not in self._config.get("themes", {}):
            logger.warning(f"Theme {theme_id} not found")
            return False

        theme = self._config["themes"][theme_id]

        if "keywords" in updates:
            theme["keywords"] = [k.lower() for k in updates["keywords"]]
        if "tickers" in updates:
            theme["tickers"] = [t.upper() for t in updates["tickers"]]
        if "name" in updates:
            theme["name"] = updates["name"]
        if "status" in updates:
            theme["status"] = updates["status"]

        self._save_config()
        return True

    def remove_theme(self, theme_id: str, archive: bool = True) -> bool:
        """Remove or archive a theme."""
        if theme_id not in self._config.get("themes", {}):
            return False

        if archive:
            self._config["themes"][theme_id]["status"] = STATUS_ARCHIVED
        else:
            del self._config["themes"][theme_id]

        self._save_config()
        return True

    def add_ticker_to_theme(self, theme_id: str, ticker: str) -> bool:
        """Add a ticker to an existing theme."""
        theme = self.get_theme(theme_id)
        if not theme:
            return False

        ticker = ticker.upper()
        if ticker not in theme["tickers"]:
            theme["tickers"].append(ticker)
            self._save_config()
        return True

    def add_keyword_to_theme(self, theme_id: str, keyword: str) -> bool:
        """Add a keyword to an existing theme."""
        theme = self.get_theme(theme_id)
        if not theme:
            return False

        keyword = keyword.lower()
        if keyword not in theme["keywords"]:
            theme["keywords"].append(keyword)
            self._save_config()
        return True

    # =========================================================================
    # For fast_stories.py compatibility
    # =========================================================================

    def get_keywords_dict(self) -> Dict[str, List[str]]:
        """Get THEME_KEYWORDS format for fast_stories.py."""
        return {k: v["keywords"] for k, v in self.get_all_themes().items()}

    def get_tickers_dict(self) -> Dict[str, List[str]]:
        """Get THEME_TICKERS format for fast_stories.py."""
        return {k: v["tickers"] for k, v in self.get_all_themes().items()}

    # =========================================================================
    # AI Discovery
    # =========================================================================

    def discover_themes_with_ai(self, headlines: List[Dict], api_key: str = None) -> List[Dict]:
        """
        Use AI to discover emerging themes not in the known list.

        Args:
            headlines: List of news headlines with 'title' key
            api_key: DeepSeek/xAI API key (optional, uses env var if not provided)

        Returns:
            List of discovered theme suggestions
        """
        api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("XAI_API_KEY")
        if not api_key:
            logger.warning("No AI API key found, skipping discovery")
            return []

        # Get current theme names for exclusion
        current_themes = list(self.get_all_themes().keys())

        # Prepare headlines for AI
        headline_texts = [h.get("title", "")[:100] for h in headlines[:50]]

        prompt = f"""Analyze these stock market headlines and identify NEW emerging investment themes
that are NOT in this existing list: {current_themes}

Headlines:
{json.dumps(headline_texts, indent=2)}

Look for:
1. New technologies or sectors gaining attention
2. Regulatory or policy changes affecting stocks
3. Macro trends creating investment opportunities
4. Sector rotations or new catalysts

Respond ONLY with valid JSON (no markdown):
{{
    "emerging_themes": [
        {{
            "id": "THEME_ID",
            "name": "Human Readable Name",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "suggested_tickers": ["TICK1", "TICK2"],
            "catalyst": "Why this theme is emerging",
            "confidence": 0.8
        }}
    ]
}}

Only include themes with confidence > 0.6 that are genuinely NEW and not variations of existing themes."""

        try:
            # Try DeepSeek first
            api_url = "https://api.deepseek.com/chat/completions"
            if "xai" in api_key.lower() or api_key.startswith("xai-"):
                api_url = "https://api.x.ai/v1/chat/completions"

            response = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat" if "deepseek" in api_url else "grok-2-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3,
                },
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return []

            content = response.json()["choices"][0]["message"]["content"]

            # Clean up response (remove markdown if present)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            discovered = result.get("emerging_themes", [])

            # Update discovery timestamp
            self._config["ai_discovery"]["last_run"] = datetime.now().isoformat()
            self._config["ai_discovery"]["discovered_themes"] = discovered
            self._save_config()

            logger.info(f"AI discovered {len(discovered)} potential new themes")
            return discovered

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return []
        except Exception as e:
            logger.error(f"AI discovery error: {e}")
            return []

    def add_discovered_theme(self, theme_data: Dict) -> bool:
        """Add an AI-discovered theme as emerging."""
        theme_id = theme_data.get("id", "").upper().replace(" ", "_")
        if not theme_id:
            return False

        return self.add_theme(
            theme_id=theme_id,
            name=theme_data.get("name", theme_id),
            keywords=theme_data.get("keywords", []),
            tickers=theme_data.get("suggested_tickers", []),
            status=STATUS_EMERGING
        )

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def update_theme_mentions(self, theme_id: str, mention_count: int) -> None:
        """Update mention count for a theme (called during detection)."""
        theme = self.get_theme(theme_id)
        if theme:
            theme["last_seen"] = datetime.now().isoformat()
            theme["mention_count_7d"] = mention_count
            # Don't save on every update - batch save later

    def run_lifecycle_management(self) -> Dict[str, List[str]]:
        """
        Run automatic lifecycle management:
        - Promote emerging themes that have proven themselves
        - Archive stale themes with no recent mentions

        Returns dict with promoted and archived theme IDs.
        """
        lifecycle = self._config.get("lifecycle", {})
        promote_days = lifecycle.get("auto_promote_after_days", 3)
        promote_min = lifecycle.get("auto_promote_min_mentions", 5)
        archive_days = lifecycle.get("auto_archive_after_days", 7)

        now = datetime.now()
        promoted = []
        archived = []

        for theme_id, theme in self._config.get("themes", {}).items():
            status = theme.get("status")
            last_seen = theme.get("last_seen")
            discovered_at = theme.get("discovered_at")
            mentions = theme.get("mention_count_7d", 0)

            try:
                last_seen_dt = datetime.fromisoformat(last_seen) if last_seen else now
                discovered_dt = datetime.fromisoformat(discovered_at) if discovered_at else now
            except (ValueError, TypeError):
                continue

            # Auto-promote emerging themes
            if status == STATUS_EMERGING:
                days_since_discovery = (now - discovered_dt).days
                if days_since_discovery >= promote_days and mentions >= promote_min:
                    theme["status"] = STATUS_KNOWN
                    theme["promoted_from_emerging"] = True
                    promoted.append(theme_id)
                    logger.info(f"Auto-promoted theme: {theme_id}")

            # Auto-archive stale themes (not for core themes)
            elif status == STATUS_KNOWN:
                days_since_seen = (now - last_seen_dt).days
                if days_since_seen >= archive_days and mentions == 0:
                    # Don't archive core themes (AI, semiconductor, etc.)
                    core_themes = ["AI_INFRASTRUCTURE", "SEMICONDUCTOR", "CRYPTO_BITCOIN",
                                   "INTEREST_RATES", "EARNINGS_SEASON"]
                    if theme_id not in core_themes:
                        theme["status"] = STATUS_ARCHIVED
                        archived.append(theme_id)
                        logger.info(f"Auto-archived theme: {theme_id}")

        if promoted or archived:
            self._save_config()

        return {"promoted": promoted, "archived": archived}

    def restore_theme(self, theme_id: str) -> bool:
        """Restore an archived theme to known status."""
        theme = self.get_theme(theme_id)
        if theme and theme.get("status") == STATUS_ARCHIVED:
            theme["status"] = STATUS_KNOWN
            theme["last_seen"] = datetime.now().isoformat()
            self._save_config()
            return True
        return False

    # =========================================================================
    # Stats and Info
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get theme statistics."""
        themes = self._config.get("themes", {})
        return {
            "total_themes": len(themes),
            "known": len([t for t in themes.values() if t.get("status") == STATUS_KNOWN]),
            "emerging": len([t for t in themes.values() if t.get("status") == STATUS_EMERGING]),
            "archived": len([t for t in themes.values() if t.get("status") == STATUS_ARCHIVED]),
            "last_updated": self._config.get("last_updated"),
            "ai_discovery_enabled": self._config.get("ai_discovery", {}).get("enabled", False),
            "last_ai_run": self._config.get("ai_discovery", {}).get("last_run"),
        }


# Global instance for convenience
_manager_instance = None


def get_theme_manager() -> ThemeManager:
    """Get or create the global ThemeManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ThemeManager()
    return _manager_instance


def reload_theme_manager() -> ThemeManager:
    """Force reload the theme manager (useful after config changes)."""
    global _manager_instance
    _manager_instance = ThemeManager()
    return _manager_instance
