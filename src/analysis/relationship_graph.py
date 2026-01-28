#!/usr/bin/env python3
"""
Relationship Graph - Stock Ecosystem Data Structure

A graph-based data structure for managing stock relationships:
- Nodes represent stocks with metadata
- Edges represent relationships (supplier, customer, competitor, adjacent, infrastructure)
- Supports freshness decay and confidence scoring
- Persistent storage in JSON format

Usage:
    graph = RelationshipGraph()
    graph.load()
    graph.add_node('NVDA', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_edge('NVDA', 'MU', 'supplier', strength=0.85, sub_theme='HBM_Memory')
    ecosystem = graph.get_subgraph('NVDA', depth=2)
    graph.save()
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
from typing import Optional

from utils import get_logger

logger = get_logger(__name__)

# Storage path
ECOSYSTEM_GRAPH_PATH = Path('learning_data/ecosystem_graph.json')


class RelationshipGraph:
    """
    Graph data structure for stock ecosystem relationships.

    Supports:
    - Directed edges with relationship types
    - Confidence scoring and freshness decay
    - Subgraph extraction for ecosystem queries
    - Path finding between stocks
    """

    # Relationship types with default decay rates
    RELATIONSHIP_TYPES = {
        'supplier': {'decay_rate': 0.98, 'description': 'Provides components/services'},
        'customer': {'decay_rate': 0.98, 'description': 'Buys products/services'},
        'competitor': {'decay_rate': 0.99, 'description': 'Competes in same market'},
        'adjacent': {'decay_rate': 0.97, 'description': 'Related play in same theme'},
        'infrastructure': {'decay_rate': 0.99, 'description': 'Enables business operations'},
        'picks_shovels': {'decay_rate': 0.98, 'description': 'Tool/equipment provider'},
    }

    # Market cap tiers
    MARKET_CAP_TIERS = ['mega', 'large', 'mid', 'small', 'micro']

    def __init__(self):
        """Initialize empty graph."""
        self.nodes = {}  # ticker -> metadata
        self.edges = defaultdict(list)  # source -> list of edges
        self.reverse_edges = defaultdict(list)  # target -> list of edges (for reverse lookup)
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'version': '1.0',
            'stats': {},
        }

    def add_node(self, ticker: str, metadata: Optional[dict] = None) -> dict:
        """
        Add or update a stock node.

        Args:
            ticker: Stock ticker symbol
            metadata: Optional dict with themes, market_cap_tier, etc.

        Returns:
            The node metadata
        """
        ticker = ticker.upper()

        if ticker in self.nodes:
            # Update existing node
            if metadata:
                self.nodes[ticker].update(metadata)
            self.nodes[ticker]['updated_at'] = datetime.now().isoformat()
        else:
            # Create new node
            self.nodes[ticker] = {
                'ticker': ticker,
                'themes': [],
                'market_cap_tier': 'unknown',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            if metadata:
                self.nodes[ticker].update(metadata)

        return self.nodes[ticker]

    def add_edge(
        self,
        source: str,
        target: str,
        rel_type: str,
        strength: float = 0.7,
        sub_theme: Optional[str] = None,
        sources: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Add or update a relationship edge.

        Args:
            source: Source ticker (e.g., driver stock)
            target: Target ticker (e.g., supplier)
            rel_type: Relationship type (supplier, customer, etc.)
            strength: Confidence score 0-1
            sub_theme: Optional sub-theme category
            sources: List of data sources (sec_10k, news, manual, deepseek)
            metadata: Additional metadata

        Returns:
            The edge data
        """
        source = source.upper()
        target = target.upper()

        # Validate relationship type
        if rel_type not in self.RELATIONSHIP_TYPES:
            logger.warning(f"Unknown relationship type: {rel_type}")
            rel_type = 'adjacent'  # Default

        # Ensure nodes exist
        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)

        # Create edge data
        edge = {
            'source': source,
            'target': target,
            'type': rel_type,
            'strength': min(1.0, max(0.0, strength)),
            'freshness': 1.0,
            'sub_theme': sub_theme,
            'sources': sources or ['manual'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        if metadata:
            edge.update(metadata)

        # Check for existing edge
        existing_idx = None
        for i, e in enumerate(self.edges[source]):
            if e['target'] == target and e['type'] == rel_type:
                existing_idx = i
                break

        if existing_idx is not None:
            # Update existing edge
            old_edge = self.edges[source][existing_idx]
            edge['created_at'] = old_edge['created_at']
            # Merge sources
            edge['sources'] = list(set(old_edge.get('sources', []) + edge['sources']))
            # Keep higher strength
            edge['strength'] = max(old_edge['strength'], edge['strength'])
            self.edges[source][existing_idx] = edge

            # Update reverse edge
            for i, e in enumerate(self.reverse_edges[target]):
                if e['source'] == source and e['type'] == rel_type:
                    self.reverse_edges[target][i] = edge
                    break
        else:
            # Add new edge
            self.edges[source].append(edge)
            self.reverse_edges[target].append(edge)

        return edge

    def get_node(self, ticker: str) -> Optional[dict]:
        """Get node metadata for a ticker."""
        return self.nodes.get(ticker.upper())

    def get_edge(self, source: str, target: str, rel_type: Optional[str] = None) -> Optional[dict]:
        """Get edge between two nodes."""
        source = source.upper()
        target = target.upper()

        for edge in self.edges.get(source, []):
            if edge['target'] == target:
                if rel_type is None or edge['type'] == rel_type:
                    return edge
        return None

    def get_neighbors(
        self,
        ticker: str,
        rel_type: Optional[str] = None,
        direction: str = 'outgoing',
        min_strength: float = 0.0,
        min_freshness: float = 0.0,
    ) -> list:
        """
        Get neighboring stocks connected to a ticker.

        Args:
            ticker: Stock ticker to query
            rel_type: Optional filter by relationship type
            direction: 'outgoing' (source->target), 'incoming' (target->source), or 'both'
            min_strength: Minimum confidence score
            min_freshness: Minimum freshness score

        Returns:
            List of (ticker, edge_data) tuples
        """
        ticker = ticker.upper()
        neighbors = []

        # Outgoing edges (this ticker is source)
        if direction in ['outgoing', 'both']:
            for edge in self.edges.get(ticker, []):
                if rel_type and edge['type'] != rel_type:
                    continue
                if edge['strength'] < min_strength:
                    continue
                if edge['freshness'] < min_freshness:
                    continue
                neighbors.append((edge['target'], edge))

        # Incoming edges (this ticker is target)
        if direction in ['incoming', 'both']:
            for edge in self.reverse_edges.get(ticker, []):
                if rel_type and edge['type'] != rel_type:
                    continue
                if edge['strength'] < min_strength:
                    continue
                if edge['freshness'] < min_freshness:
                    continue
                neighbors.append((edge['source'], edge))

        return neighbors

    def get_suppliers(self, ticker: str, min_strength: float = 0.5) -> list:
        """Get stocks that supply to this ticker."""
        neighbors = self.get_neighbors(
            ticker, rel_type='supplier', direction='outgoing', min_strength=min_strength
        )
        return [{'ticker': t, **e} for t, e in neighbors]

    def get_customers(self, ticker: str, min_strength: float = 0.5) -> list:
        """Get stocks that are customers of this ticker."""
        neighbors = self.get_neighbors(
            ticker, rel_type='customer', direction='outgoing', min_strength=min_strength
        )
        return [{'ticker': t, **e} for t, e in neighbors]

    def get_competitors(self, ticker: str, min_strength: float = 0.5) -> list:
        """Get stocks that compete with this ticker."""
        neighbors = self.get_neighbors(
            ticker, rel_type='competitor', direction='both', min_strength=min_strength
        )
        return [{'ticker': t, **e} for t, e in neighbors]

    def get_subgraph(
        self,
        ticker: str,
        depth: int = 2,
        rel_types: Optional[list] = None,
        min_strength: float = 0.3,
    ) -> dict:
        """
        Extract a subgraph centered on a ticker.

        Args:
            ticker: Center node ticker
            depth: Maximum depth to traverse
            rel_types: Optional list of relationship types to include
            min_strength: Minimum edge strength to include

        Returns:
            Dict with nodes, edges, and summary
        """
        ticker = ticker.upper()

        if ticker not in self.nodes:
            return {'nodes': [], 'edges': [], 'center': ticker, 'summary': {}}

        visited = set()
        nodes = {}
        edges = []
        queue = deque([(ticker, 0)])

        while queue:
            current, current_depth = queue.popleft()

            if current in visited:
                continue
            visited.add(current)

            # Add node
            if current in self.nodes:
                nodes[current] = self.nodes[current]

            if current_depth >= depth:
                continue

            # Traverse edges
            for target, edge in self.get_neighbors(
                current, direction='both', min_strength=min_strength
            ):
                if rel_types and edge['type'] not in rel_types:
                    continue

                edges.append(edge)

                if target not in visited:
                    queue.append((target, current_depth + 1))

        # Create summary
        summary = {
            'center': ticker,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'depth': depth,
            'by_type': defaultdict(int),
            'by_sub_theme': defaultdict(list),
        }

        for edge in edges:
            summary['by_type'][edge['type']] += 1
            if edge.get('sub_theme'):
                summary['by_sub_theme'][edge['sub_theme']].append(edge['target'])

        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'center': ticker,
            'summary': dict(summary),
        }

    def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 4,
        rel_types: Optional[list] = None,
    ) -> Optional[list]:
        """
        Find shortest path between two stocks.

        Args:
            source: Starting ticker
            target: Destination ticker
            max_depth: Maximum path length
            rel_types: Optional relationship type filter

        Returns:
            List of (ticker, edge) tuples representing the path, or None
        """
        source = source.upper()
        target = target.upper()

        if source not in self.nodes or target not in self.nodes:
            return None

        if source == target:
            return [(source, None)]

        visited = set()
        queue = deque([(source, [(source, None)])])

        while queue:
            current, path = queue.popleft()

            if len(path) > max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            for neighbor, edge in self.get_neighbors(current, direction='both'):
                if rel_types and edge['type'] not in rel_types:
                    continue

                new_path = path + [(neighbor, edge)]

                if neighbor == target:
                    return new_path

                if neighbor not in visited:
                    queue.append((neighbor, new_path))

        return None

    def decay_freshness(self, rate: Optional[float] = None, days: int = 1):
        """
        Apply freshness decay to all edges.

        Args:
            rate: Override decay rate (0-1)
            days: Number of days of decay to apply
        """
        for source in self.edges:
            for edge in self.edges[source]:
                edge_type = edge['type']
                decay = rate or self.RELATIONSHIP_TYPES.get(
                    edge_type, {}
                ).get('decay_rate', 0.98)

                # Apply decay for each day
                edge['freshness'] = edge['freshness'] * (decay ** days)

                # Minimum freshness
                edge['freshness'] = max(0.1, edge['freshness'])

        self.metadata['last_decay'] = datetime.now().isoformat()

    def refresh_edge(self, source: str, target: str, rel_type: Optional[str] = None):
        """Reset freshness for an edge (e.g., after verification)."""
        edge = self.get_edge(source, target, rel_type)
        if edge:
            edge['freshness'] = 1.0
            edge['updated_at'] = datetime.now().isoformat()

    def get_stale_edges(self, threshold: float = 0.5) -> list:
        """Get edges with freshness below threshold."""
        stale = []
        for source in self.edges:
            for edge in self.edges[source]:
                if edge['freshness'] < threshold:
                    stale.append(edge)
        return sorted(stale, key=lambda e: e['freshness'])

    def get_strong_edges(self, min_strength: float = 0.8) -> list:
        """Get high-confidence edges."""
        strong = []
        for source in self.edges:
            for edge in self.edges[source]:
                if edge['strength'] >= min_strength:
                    strong.append(edge)
        return sorted(strong, key=lambda e: -e['strength'])

    def get_by_sub_theme(self, sub_theme: str) -> list:
        """Get all tickers in a sub-theme."""
        tickers = set()
        for source in self.edges:
            for edge in self.edges[source]:
                if edge.get('sub_theme') == sub_theme:
                    tickers.add(edge['source'])
                    tickers.add(edge['target'])
        return list(tickers)

    def get_stats(self) -> dict:
        """Get graph statistics."""
        edge_count = sum(len(edges) for edges in self.edges.values())

        type_counts = defaultdict(int)
        subtheme_counts = defaultdict(int)
        avg_strength = []
        avg_freshness = []

        for source in self.edges:
            for edge in self.edges[source]:
                type_counts[edge['type']] += 1
                if edge.get('sub_theme'):
                    subtheme_counts[edge['sub_theme']] += 1
                avg_strength.append(edge['strength'])
                avg_freshness.append(edge['freshness'])

        return {
            'node_count': len(self.nodes),
            'edge_count': edge_count,
            'by_type': dict(type_counts),
            'by_sub_theme': dict(subtheme_counts),
            'avg_strength': sum(avg_strength) / len(avg_strength) if avg_strength else 0,
            'avg_freshness': sum(avg_freshness) / len(avg_freshness) if avg_freshness else 0,
            'last_updated': self.metadata.get('last_updated'),
        }

    def to_dict(self) -> dict:
        """Convert graph to dictionary for serialization."""
        return {
            'nodes': self.nodes,
            'edges': {k: v for k, v in self.edges.items()},
            'metadata': self.metadata,
        }

    def from_dict(self, data: dict):
        """Load graph from dictionary."""
        self.nodes = data.get('nodes', {})
        self.edges = defaultdict(list, data.get('edges', {}))
        self.metadata = data.get('metadata', self.metadata)

        # Rebuild reverse edges
        self.reverse_edges = defaultdict(list)
        for source in self.edges:
            for edge in self.edges[source]:
                self.reverse_edges[edge['target']].append(edge)

    def save(self, path: Optional[Path] = None):
        """Save graph to JSON file."""
        path = path or ECOSYSTEM_GRAPH_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        self.metadata['last_updated'] = datetime.now().isoformat()
        self.metadata['stats'] = self.get_stats()

        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved ecosystem graph: {self.metadata['stats']['node_count']} nodes, {self.metadata['stats']['edge_count']} edges")

    def load(self, path: Optional[Path] = None) -> bool:
        """Load graph from JSON file."""
        path = path or ECOSYSTEM_GRAPH_PATH

        if not path.exists():
            logger.info(f"No existing graph at {path}, starting fresh")
            return False

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            self.from_dict(data)
            logger.info(f"Loaded ecosystem graph: {len(self.nodes)} nodes, {sum(len(e) for e in self.edges.values())} edges")
            return True
        except Exception as e:
            logger.error(f"Failed to load ecosystem graph: {e}")
            return False

    def merge(self, other: 'RelationshipGraph', overwrite: bool = False):
        """
        Merge another graph into this one.

        Args:
            other: Graph to merge
            overwrite: If True, overwrite existing edges
        """
        # Merge nodes
        for ticker, node in other.nodes.items():
            if ticker not in self.nodes or overwrite:
                self.nodes[ticker] = node
            else:
                # Update with newer data
                if node.get('updated_at', '') > self.nodes[ticker].get('updated_at', ''):
                    self.nodes[ticker].update(node)

        # Merge edges
        for source in other.edges:
            for edge in other.edges[source]:
                existing = self.get_edge(edge['source'], edge['target'], edge['type'])
                if not existing or overwrite:
                    self.add_edge(
                        edge['source'],
                        edge['target'],
                        edge['type'],
                        strength=edge['strength'],
                        sub_theme=edge.get('sub_theme'),
                        sources=edge.get('sources'),
                    )


# Singleton instance
_graph_instance = None


def get_ecosystem_graph() -> RelationshipGraph:
    """Get singleton graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = RelationshipGraph()
        _graph_instance.load()
    return _graph_instance


def reset_graph():
    """Reset the singleton instance (for testing)."""
    global _graph_instance
    _graph_instance = None


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == '__main__':
    print("Testing RelationshipGraph...")

    graph = RelationshipGraph()

    # Add nodes
    graph.add_node('NVDA', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_node('MU', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'large'})
    graph.add_node('TSM', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})
    graph.add_node('AMD', {'themes': ['ai_infrastructure'], 'market_cap_tier': 'mega'})

    # Add edges
    graph.add_edge('NVDA', 'MU', 'supplier', strength=0.9, sub_theme='HBM_Memory')
    graph.add_edge('NVDA', 'TSM', 'supplier', strength=0.95, sub_theme='CoWoS_Packaging')
    graph.add_edge('NVDA', 'AMD', 'competitor', strength=0.85)
    graph.add_edge('AMD', 'TSM', 'supplier', strength=0.9, sub_theme='Foundry')

    # Test queries
    print(f"\nGraph stats: {graph.get_stats()}")

    print(f"\nNVDA suppliers: {[s['ticker'] for s in graph.get_suppliers('NVDA')]}")
    print(f"NVDA competitors: {[s['ticker'] for s in graph.get_competitors('NVDA')]}")

    subgraph = graph.get_subgraph('NVDA', depth=2)
    print(f"\nNVDA subgraph: {subgraph['summary']}")

    path = graph.find_path('AMD', 'MU')
    print(f"\nPath from AMD to MU: {[p[0] for p in path] if path else 'Not found'}")

    # Test persistence
    graph.save(Path('/tmp/claude/test_ecosystem_graph.json'))

    new_graph = RelationshipGraph()
    new_graph.load(Path('/tmp/claude/test_ecosystem_graph.json'))
    print(f"\nReloaded graph stats: {new_graph.get_stats()}")

    print("\nAll tests passed!")
