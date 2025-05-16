"""Simply export main"""

import importlib.metadata

from ollama_cli.ollama_cli_main import main

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development mode

__all__ = ["__version__", "main"]
