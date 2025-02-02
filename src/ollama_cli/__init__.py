"""Simply export main"""

from ollama_cli.__version__ import __version__, __version_tuple__
from ollama_cli.ollama_cli_main import main

__all__ = ["__version__", "__version_tuple__", "main"]
