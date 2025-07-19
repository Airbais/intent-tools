#!/usr/bin/env python3
"""
GRASP Content Quality Evaluator
Evaluate website content across five key dimensions: Grounded, Readable, Accurate, Structured, Polished
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from main import main

if __name__ == "__main__":
    main()