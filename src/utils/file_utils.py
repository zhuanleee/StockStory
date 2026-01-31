"""
File utility functions.
Shared utilities for file and directory operations.
"""
import os
import logging

logger = logging.getLogger(__name__)


def ensure_data_dir(subdir=None):
    """
    Ensure data directory exists.

    Args:
        subdir: Optional subdirectory name within data/

    Returns:
        str: Path to the data directory
    """
    base_dir = os.path.join(os.getcwd(), "data")
    if subdir:
        base_dir = os.path.join(base_dir, subdir)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir
