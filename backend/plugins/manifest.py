from dataclasses import dataclass
from typing import List

@dataclass
class PluginInfo:
    name: str
    version: str
    author: str
    compatible_engine_version: str
    description: str
    plugin_type: str  # parser, retriever, generator, evaluator
    entrypoint: str  # dotted import path to the plugin class
