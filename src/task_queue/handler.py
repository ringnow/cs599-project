"""Task handler: bridge between queue worker and skill system."""
from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext


def handle_task(task_type: str, payload: dict) -> dict:
    """Execute a task from the queue.

    Returns a dict with 'report' and 'metadata' keys.
    """
    topic = payload.get("topic", "")
    provider = payload.get("provider", "")
    model_id = payload.get("model_id", "")
    depth = payload.get("depth", 3)
    sources = payload.get("sources", ["web", "semantic_scholar"])
    user_id = payload.get("user_id", "") or ""
    # 从 payload 读取 request_id，用于协作式取消检查
    request_id = payload.get("request_id", "") or ""

    registry = get_skill_registry()
    ctx = SkillContext(
        topic=topic,
        provider_name=provider,
        model_id=model_id,
        temperature=0.7,
        custom_params={"depth": depth, "sources": sources, "request_id": request_id},
        user_id=user_id,
    )

    result = registry.execute(task_type, ctx)
    return {
        "report": result.content if result.success else f"Error: {result.error}",
        "metadata": result.metadata if result.success else {"error": result.error},
        "success": result.success,
    }
