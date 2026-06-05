"""Configuration management for CS599 AI Research Agent v2."""
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""
    
    # Default LLM settings (can be overridden via UI)
    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    default_temperature: float = 0.7
    
    # Research settings
    max_search_results: int = 5
    max_iterations: int = 3
    
    # Crew settings
    crew_max_iterations: int = 2
    
    # Paths
    skills_library_path: str = "skills_library"
    output_path: str = "research_outputs"
    
    def validate(self) -> bool:
        """Validate essential configuration."""
        return True  # v2 uses model manager for validation


config = Config()
