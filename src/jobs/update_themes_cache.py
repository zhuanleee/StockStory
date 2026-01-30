#!/usr/bin/env python3
"""
Background job to update themes cache.
Runs independently, stores results in cache file.
API endpoint reads from cache for instant response.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

CACHE_FILE = Path('.cache/themes_list.json')
CACHE_FILE.parent.mkdir(exist_ok=True)

def update_themes_cache():
    """Update themes cache from theme registry."""
    logger.info("Starting themes cache update...")

    try:
        from theme_registry import get_registry

        logger.info("Loading theme registry...")
        registry = get_registry()

        themes = []
        for theme_id, theme in registry.themes.items():
            try:
                themes.append({
                    'id': theme_id,
                    'name': theme.template.name,
                    'category': theme.template.category,
                    'stage': theme.stage.value,
                    'heat_score': theme.heat_score,
                    'members': len(theme.members),
                    'drivers': theme.get_drivers(),
                    'discovery_method': theme.discovery_method,
                    'discovered_at': theme.discovered_at,
                })
            except Exception as e:
                logger.warning(f"Error processing theme {theme_id}: {e}")
                continue

        # Sort by heat score
        themes_sorted = sorted(themes, key=lambda x: x.get('heat_score', 0), reverse=True)

        # Save to cache
        cache_data = {
            'ok': True,
            'themes': themes_sorted,
            'total': len(themes_sorted),
            'updated_at': datetime.now().isoformat(),
            'cache_version': 1
        }

        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"✅ Themes cache updated: {len(themes_sorted)} themes")
        return cache_data

    except ImportError as e:
        logger.error(f"Theme registry not available: {e}")
        return {'ok': False, 'error': 'Theme registry not available'}
    except Exception as e:
        logger.error(f"Error updating themes cache: {e}", exc_info=True)
        return {'ok': False, 'error': str(e)}

if __name__ == '__main__':
    result = update_themes_cache()
    if result.get('ok'):
        print(f"✅ Updated {result['total']} themes")
    else:
        print(f"❌ Error: {result.get('error')}")
        exit(1)
