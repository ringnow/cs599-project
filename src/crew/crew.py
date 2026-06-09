"""Crew - Multi-agent collaboration orchestrator.

Manages the workflow between multiple agents:
1. Assigns tasks to appropriate agents
2. Routes messages between agents
3. Manages the overall execution flow
4. Collects and aggregates results

Workflow patterns:
- Sequential: Researcher -> Critic -> Writer
- Iterative: Researcher -> Critic -> (revise) -> Writer -> Critic
- Parallel: Multiple researchers working on different aspects
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.crew.agent import BaseAgent, ResearcherAgent, CriticAgent, WriterAgent, AgentMessage


@dataclass
class TaskAssignment:
    """Assignment of a task to an agent."""
    task_id: str
    agent_name: str
    task_description: str
    context: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # Task IDs to wait for
    status: str = "pending"  # pending, running, done, error
    result: Dict = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""


class Crew:
    """Orchestrates multi-agent collaboration.
    
    Manages a team of agents and coordinates their work
    through structured workflows.
    
    Usage:
        crew = Crew()
        crew.add_agent(ResearcherAgent())
        crew.add_agent(CriticAgent())
        crew.add_agent(WriterAgent())
        result = crew.run_sequential("Research quantum computing applications")
    """
    
    def __init__(self, provider_name: str = "deepseek", model_id: str = "deepseek-chat"):
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, TaskAssignment] = {}
        self.workflow_log: List[Dict] = []
        self.provider_name = provider_name
        self.model_id = model_id
        self._setup_default_agents()
    
    def _setup_default_agents(self):
        """Set up the default agent team."""
        self.add_agent(ResearcherAgent(self.provider_name, self.model_id))
        self.add_agent(CriticAgent(self.provider_name, self.model_id))
        self.add_agent(WriterAgent(self.provider_name, self.model_id))
    
    def add_agent(self, agent: BaseAgent):
        """Add an agent to the crew."""
        self.agents[agent.name] = agent
    
    def remove_agent(self, name: str):
        """Remove an agent from the crew."""
        if name in self.agents:
            del self.agents[name]
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Dict]:
        """List all agents with their status."""
        return [agent.get_status() for agent in self.agents.values()]
    
    # --- Workflow Patterns ---
    
    def run_sequential(self, topic: str, doc_type: str = "report",
                       max_iterations: int = 2, context: str = "") -> Dict[str, Any]:
        """Run sequential workflow: Research -> Review -> Write.

        Args:
            topic: Research topic
            doc_type: Type of document to produce
            max_iterations: Max review-revise iterations
            context: Additional user-provided context

        Returns:
            Dict with final document and workflow log
        """
        self.workflow_log = []
        start_time = time.time()

        # Phase 1: Research
        self._log("phase", "Starting Phase 1: Research", "crew")
        researcher = self.agents.get("researcher")
        if not researcher:
            return {"error": "Researcher agent not found"}

        researcher.state.status = "working"
        ctx_dict = {"user_context": context} if context else None
        research_result = researcher.execute(topic, ctx_dict)
        researcher.state.status = "done"
        
        self._log("complete", f"Research complete: {research_result.get('sources_count', 0)} sources", 
                   "researcher", research_result)
        
        # Phase 2: Review (Critic)
        self._log("phase", "Starting Phase 2: Review", "crew")
        critic = self.agents.get("critic")
        review_result = None
        
        if critic:
            critic.state.status = "working"
            review_context = {
                "content": research_result.get("synthesis", ""),
                "questions": research_result.get("questions", []),
                "sources_count": research_result.get("sources_count", 0),
            }
            review_result = critic.execute("review", review_context)
            critic.state.status = "done"
            
            self._log("complete", "Review complete", "critic", 
                       {"review_length": len(review_result.get("review", ""))})
        
        # Phase 3: Write
        self._log("phase", "Starting Phase 3: Write", "crew")
        writer = self.agents.get("writer")
        
        if not writer:
            return {"error": "Writer agent not found"}
        
        # Iterative review-write cycle
        document = ""
        for iteration in range(max_iterations):
            writer.state.status = "working"
            
            write_context = {
                "research": research_result.get("synthesis", ""),
                "review": review_result.get("review", "") if review_result else "",
                "doc_type": doc_type,
            }
            
            if iteration > 0 and document:
                # Revise mode
                write_context["document"] = document
                msg = AgentMessage(
                    from_agent="crew",
                    to_agent="writer",
                    message_type="feedback",
                    content=review_result.get("review", "") if review_result else "",
                    metadata=write_context,
                )
                document = writer.receive_message(msg)
            else:
                # Fresh write
                write_result = writer.execute(topic, write_context)
                document = write_result.get("document", "")
            
            writer.state.status = "done"
            self._log("complete", f"Write iteration {iteration + 1} complete", "writer")
            
            # If critic says it's good enough via JSON, stop early
            if review_result:
                import json as _json, re as _re
                review_text = review_result.get("review", "")
                try:
                    m = _re.search(r'\{.*\}', review_text, _re.DOTALL)
                    if m:
                        j = _json.loads(m.group())
                        verdict = j.get("verdict", "").lower()
                        if verdict == "pass":
                            self._log("decision", "✅ Review passed via JSON verdict, stopping iterations", "crew")
                            break
                except Exception:
                    pass
                if "Pass" in review_text:
                    self._log("decision", "Review passed, stopping iterations", "crew")
                    break
        
        duration = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "topic": topic,
            "document": document,
            "doc_type": doc_type,
            "iterations": max_iterations,
            "duration_ms": duration,
            "research": research_result,
            "review": review_result,
            "workflow_log": self.workflow_log,
            "agent_statuses": self.list_agents(),
        }
    
    def run_research_only(self, topic: str) -> Dict[str, Any]:
        """Run only the research phase.
        
        Returns research findings without writing.
        """
        self.workflow_log = []
        researcher = self.agents.get("researcher")
        
        if not researcher:
            return {"error": "Researcher agent not found"}
        
        result = researcher.execute(topic)
        
        return {
            "success": True,
            "topic": topic,
            **result,
            "workflow_log": self.workflow_log,
        }
    
    def run_with_skills(self, topic: str, skill_name: str, 
                        skill_context: Dict = None) -> Dict[str, Any]:
        """Run crew with a specific skill.
        
        Uses the skill system for the core task while agents
        handle quality assurance.
        """
        from src.skills.registry import get_skill_registry
        from src.skills.base import SkillContext
        
        self.workflow_log = []
        
        # Phase 1: Execute skill
        self._log("phase", f"Executing skill: {skill_name}", "crew")
        registry = get_skill_registry()
        
        ctx = SkillContext(
            topic=topic,
            provider_name=self.provider_name,
            model_id=self.model_id,
            custom_params=skill_context or {},
        )
        
        skill_result = registry.execute(skill_name, ctx)
        
        if not skill_result.success:
            return {"error": skill_result.error, "skill_result": skill_result}
        
        self._log("complete", f"Skill execution complete", "crew")
        
        # Phase 2: Critic review (optional)
        review_result = None
        critic = self.agents.get("critic")
        if critic and skill_result.content:
            critic.state.status = "working"
            review_result = critic.execute("review", {
                "content": skill_result.content,
            })
            critic.state.status = "done"
            self._log("complete", "Review complete", "critic")
        
        return {
            "success": True,
            "topic": topic,
            "skill": skill_name,
            "content": skill_result.content,
            "metadata": skill_result.metadata,
            "review": review_result.get("review", "") if review_result else "",
            "workflow_log": self.workflow_log,
        }
    
    def _log(self, event_type: str, message: str, agent: str, 
             metadata: Dict = None):
        """Add entry to workflow log."""
        self.workflow_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "agent": agent,
            "metadata": metadata or {},
        })
    
    def get_workflow_summary(self) -> str:
        """Get a human-readable summary of the workflow."""
        lines = ["# Crew Workflow Summary\n"]
        
        for entry in self.workflow_log:
            emoji = {
                "phase": "\ud83d\udd04",
                "complete": "\u2705",
                "decision": "\ud83e\udd14",
                "error": "\u274c",
            }.get(entry["type"], "\u2022")
            
            lines.append(f"{emoji} **{entry['agent']}**: {entry['message']}")
        
        lines.append("\n## Agent Statuses")
        for status in self.list_agents():
            lines.append(f"- **{status['name']}** ({status['role']}): {status['status']}")
        
        return "\n".join(lines)
