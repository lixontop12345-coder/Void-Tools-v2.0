#!/usr/bin/env python3
"""Point d'entrée Void Selfbot — lancé depuis Void-Tools ou en direct."""
import os
import sys

_VOID = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _VOID not in sys.path:
    sys.path.insert(0, _VOID)

from lib.selfbot_launcher import launch_void_selfbot

if __name__ == "__main__":
    launch_void_selfbot()
