"""Multi-Agent Collaboration System (Crew).

Implements a CrewAI-style multi-agent architecture where specialized agents
collaborate on complex tasks through a structured workflow.

Agents:
- Researcher: Gathers and analyzes information
- Critic: Reviews and validates findings
- Writer: Produces final deliverables
"""
from src.crew.agent import BaseAgent, ResearcherAgent, CriticAgent, WriterAgent
from src.crew.crew import Crew, TaskAssignment

__all__ = [
    "BaseAgent",
    "ResearcherAgent",
    "CriticAgent", 
    "WriterAgent",
    "Crew",
    "TaskAssignment",
]
