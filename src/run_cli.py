#!/usr/bin/env python3
"""CLI entry point for CS599 AI Research Agent v2.

Usage:
    python src/run_cli.py "topic" --skill research --provider deepseek
    python src/run_cli.py "topic" --skill paper_writing --paper-type survey
    python src/run_cli.py "topic" --crew  # Use multi-agent crew
"""
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext
from src.crew.crew import Crew
from src.models.manager import get_model_manager


def main():
    parser = argparse.ArgumentParser(description="CS599 AI Research Agent v2")
    parser.add_argument("topic", help="Research topic or paper title")
    parser.add_argument("--skill", default="research", 
                       choices=["research", "paper_writing", "survey_writing", 
                               "literature_review", "code_review", "crew"],
                       help="Skill to use")
    parser.add_argument("--provider", default="deepseek", help="Model provider")
    parser.add_argument("--model", default="deepseek-chat", help="Model ID")
    parser.add_argument("--crew", action="store_true", help="Use multi-agent crew")
    parser.add_argument("--paper-type", default="research", help="Paper type")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--key", help="API key (or set {PROVIDER}_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Setup API key if provided
    if args.key:
        manager = get_model_manager()
        manager.set_api_key(args.provider, args.key)
    
    print(f"🔬 CS599 AI Research Agent v2")
    print(f"   Topic: {args.topic}")
    print(f"   Provider: {args.provider} / {args.model}")
    print(f"   Mode: {'Crew' if args.crew else args.skill}")
    print("=" * 60)
    
    if args.crew:
        # Multi-agent mode
        crew = Crew(provider_name=args.provider, model_id=args.model)
        
        if args.skill and args.skill != "crew":
            result = crew.run_with_skills(args.topic, args.skill)
        else:
            result = crew.run_sequential(args.topic, doc_type="report")
        
        content = result.get("document", result.get("content", ""))
        
        # Print workflow log
        print("\n📋 Workflow:")
        for entry in result.get("workflow_log", []):
            print(f"  [{entry.get('agent', '')}] {entry.get('message', '')}")
    
    else:
        # Skill mode
        registry = get_skill_registry()
        ctx = SkillContext(
            topic=args.topic,
            provider_name=args.provider,
            model_id=args.model,
            custom_params={"paper_type": args.paper_type} if args.skill == "paper_writing" else {},
        )
        
        result = registry.execute(args.skill, ctx)
        content = result.content if result.success else f"Error: {result.error}"
        
        # Print steps
        if result.steps:
            print("\n🔄 Steps:")
            for step in result.steps:
                status = step.get("status", "")
                emoji = {"done": "✅", "error": "❌", "running": "🔄"}.get(status, "⏳")
                print(f"  {emoji} {step.get('action', '')}: {step.get('result', '')}")
    
    # Output
    if content:
        print("\n" + "=" * 60)
        print("📄 OUTPUT:")
        print("=" * 60)
        print(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(content)
            print(f"\n💾 Saved to: {args.output}")


if __name__ == "__main__":
    main()
