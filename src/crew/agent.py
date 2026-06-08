"""Agent definitions for multi-agent collaboration.

Each agent has a specific role, goal, and set of capabilities.
Agents communicate through structured messages and share state.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.models.manager import get_model_manager


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: str           # Sender agent name
    to_agent: str             # Recipient agent name (or "all")
    message_type: str         # "task", "review", "feedback", "result"
    content: str              # Message content
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AgentState:
    """Internal state of an agent."""
    status: str = "idle"      # idle, working, waiting, done, error
    current_task: str = ""
    iterations: int = 0
    notes: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all crew agents.
    
    Each agent has:
    - A specific role and goal
    - Access to LLM for reasoning
    - Internal state (memory, notes)
    - Ability to send/receive messages
    """
    
    name: str = "base"
    role: str = "Base Agent"
    goal: str = "Execute tasks"
    backstory: str = ""
    
    def __init__(self, provider_name: str = "deepseek", model_id: str = "deepseek-chat",
                 temperature: float = 0.7):
        self.provider_name = provider_name
        self.model_id = model_id
        self.temperature = temperature
        self.state = AgentState()
        self.messages: List[AgentMessage] = []
        
    def _llm_call(self, prompt: str, system_prompt: str = "") -> str:
        """Call LLM with the agent's configuration."""
        manager = get_model_manager()
        llm = manager.create_llm_client(
            self.provider_name, self.model_id, self.temperature
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"[Error: {e}]"
    
    def send_message(self, to_agent: str, msg_type: str, content: str, 
                     metadata: Dict = None) -> AgentMessage:
        """Send a message to another agent."""
        msg = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=msg_type,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        return msg
    
    def receive_message(self, message: AgentMessage):
        """Receive a message from another agent."""
        self.messages.append(message)
        return self.process_message(message)
    
    @abstractmethod
    def process_message(self, message: AgentMessage) -> str:
        """Process an incoming message. Override in subclasses."""
        pass
    
    @abstractmethod
    def execute(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Execute the agent's primary task."""
        pass
    
    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "name": self.name,
            "role": self.role,
            "status": self.state.status,
            "current_task": self.state.current_task,
            "iterations": self.state.iterations,
            "message_count": len(self.messages),
        }


class ResearcherAgent(BaseAgent):
    """Research Agent - gathers and analyzes information.
    
    Capabilities:
    - Decomposes topics into research questions
    - Searches web and academic sources
    - Extracts and synthesizes information
    - Produces structured research notes
    """
    
    name = "researcher"
    role = "Senior Research Analyst"
    goal = "Gather comprehensive, accurate information on any topic through systematic research"
    backstory = "You are an expert research analyst with years of experience in academic and industry research. You excel at finding reliable sources, extracting key information, and synthesizing findings into structured notes."
    
    def process_message(self, message: AgentMessage) -> str:
        if message.message_type == "task":
            return self.execute(message.content)
        elif message.message_type == "feedback":
            self.state.notes.append(f"Feedback: {message.content}")
            return "Feedback received"
        return "Message acknowledged"
    
    def execute(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Execute research task."""
        self.state.status = "working"
        self.state.current_task = task
        
        ctx = context or {}
        
        # Step 1: Decompose topic
        decompose_prompt = f"""As a research analyst, decompose this topic into 3-5 specific research questions:

Topic: {task}

Previous context: {ctx.get('previous_research', 'None')}

Return ONLY a JSON array of questions."""
        
        import json, re
        response = self._llm_call(decompose_prompt, self.backstory)
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        questions = []
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list) and parsed:
                    questions = parsed
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        if not questions:
            questions = [task]
        
        # Step 2: Research each question
        from src.agent.tools import web_search, semantic_scholar_search
        
        findings = []
        for q in questions:
            web_results = web_search(q, max_results=3)
            ss_results = semantic_scholar_search(q, max_results=2)
            
            sources = []
            for r in web_results + ss_results:
                sources.append({"title": r.title, "url": r.url, "source": r.source})
            
            findings.append({
                "question": q,
                "sources": sources,
                "num_web": len(web_results),
                "num_ss": len(ss_results),
            })
        
        # Step 3: Synthesize
        synthesis_prompt = f"""Synthesize the following research findings into structured notes:

Topic: {task}

Findings:
{json.dumps(findings, indent=2, ensure_ascii=False)}

Provide:
1. Key findings summary
2. Important facts and data points
3. Contradictions or gaps
4. Source quality assessment

Write in Markdown format."""
        
        synthesis = self._llm_call(synthesis_prompt, self.backstory)
        
        self.state.status = "done"
        self.state.iterations += 1
        
        return {
            "agent": self.name,
            "task": task,
            "questions": questions,
            "findings": findings,
            "synthesis": synthesis,
            "sources_count": sum(len(f["sources"]) for f in findings),
        }


class CriticAgent(BaseAgent):
    """Critic Agent - reviews and validates research findings.
    
    Capabilities:
    - Identifies logical fallacies and biases
    - Checks factual accuracy
    - Evaluates source quality
    - Suggests improvements and corrections
    """
    
    name = "critic"
    role = "Research Quality Assurance Specialist"
    goal = "Ensure research quality by identifying errors, biases, and gaps in findings"
    backstory = "You are a meticulous quality assurance specialist with expertise in research methodology. You have a keen eye for identifying logical fallacies, factual errors, weak evidence, and biased arguments."
    
    def process_message(self, message: AgentMessage) -> str:
        if message.message_type == "review":
            return self._review_content(message.content, message.metadata)
        return "Message acknowledged"
    
    def execute(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Review and critique content."""
        self.state.status = "working"
        self.state.current_task = "review"
        
        content = context.get("content", task) if context else task
        metadata = context or {}
        
        review = self._review_content(content, metadata)
        
        self.state.status = "done"
        self.state.iterations += 1
        
        return {
            "agent": self.name,
            "task": "review",
            "review": review,
            "content_length": len(content),
        }
    
    def _review_content(self, content: str, metadata: Dict = None) -> str:
        """Perform detailed review of content."""
        prompt = f"""Review the following research content critically:

{content[:4000]}

Provide your review in this format:

## 1. Factual Accuracy
- Any factual errors or questionable claims
- Unsupported assertions

## 2. Logical Soundness  
- Logical fallacies
- Weak arguments
- Missing premises

## 3. Coverage & Completeness
- Important aspects missing
- Biases in coverage
- One-sided arguments

## 4. Source Quality
- Credibility assessment
- Sufficient citations
- Recency of sources

## 5. Suggested Improvements
- Specific, actionable suggestions
- Additional research needed

## 6. Overall Assessment
Output a JSON object with your assessment (no other text):
{"score": 8, "verdict": "pass", "issues": ["issue1"], "suggestions": ["suggestion1"]}"""
        
        return self._llm_call(prompt, self.backstory)


class WriterAgent(BaseAgent):
    """Writer Agent - produces final deliverables.
    
    Capabilities:
    - Writes academic papers and reports
    - Adapts style to different formats
    - Incorporates feedback from critic
    - Produces publication-ready documents
    """
    
    name = "writer"
    role = "Technical Writer and Editor"
    goal = "Produce high-quality, publication-ready documents from research findings"
    backstory = "You are an experienced technical writer and academic editor. You excel at transforming raw research into well-structured, clear, and compelling documents. You understand academic writing conventions and can adapt your style to different venues."
    
    def process_message(self, message: AgentMessage) -> str:
        if message.message_type == "task":
            return self.execute(message.content, message.metadata)
        elif message.message_type == "feedback":
            return self._revise_with_feedback(message.content, message.metadata)
        return "Message acknowledged"
    
    def execute(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Write document from research findings."""
        self.state.status = "working"
        self.state.current_task = "write"
        
        ctx = context or {}
        research = ctx.get("research", task)
        review = ctx.get("review", "")
        doc_type = ctx.get("doc_type", "report")
        
        # Write document
        write_prompt = f"""Write a professional {doc_type} based on the following research:

Research:
{research[:3000]}

{'Reviewer feedback (incorporate these suggestions):' + review[:1000] if review else ''}

Requirements:
- Professional academic style
- Clear structure with proper sections
- Incorporate all key findings
- Include references where applicable
- Output in Markdown format

Write the complete document."""
        
        document = self._llm_call(write_prompt, self.backstory)
        
        self.state.status = "done"
        self.state.iterations += 1
        
        return {
            "agent": self.name,
            "task": "write",
            "document": document,
            "doc_type": doc_type,
            "word_count": len(document.split()),
        }
    
    def _revise_with_feedback(self, feedback: str, context: Dict = None) -> str:
        """Revise document based on feedback."""
        current_doc = context.get("document", "") if context else ""
        
        revise_prompt = f"""Revise the following document based on the feedback:

Current document:
{current_doc[:3000]}

Feedback:
{feedback}

Provide the revised complete document in Markdown."""
        
        return self._llm_call(revise_prompt, self.backstory)
