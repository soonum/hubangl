# coding: utf-8
import os.path
import sys

# Add HUBAngl sources to the python path.
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if path not in sys.path:
    sys.path.insert(0, path)
