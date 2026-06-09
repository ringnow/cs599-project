"""Image Generation Module - AI-powered image generation for research reports.

Supports generating images to enhance research reports (concept illustrations,
visual abstracts, methodology diagrams) using the available model provider.

Current implementation:
- Shangtang SenseNova (sensenova-u1-fast) text-to-image via OpenAI-compatible API
- Extensible to add more providers later

Usage:
    from src.agent.image_gen import generate_image, enhance_report_with_images
    
    # Generate a single image
    success, path = generate_image(
        prompt="A diagram showing deep learning architecture",
        output_path="/tmp/outputs/architecture.png",
    )
    
    # Enhance a full report with images (post-processing)
    images = enhance_report_with_images(report_text, llm, output_dir)
"""
import json
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import requests
from PIL import Image as PILImage

from src.models.manager import get_model_manager


# Directory for generated images
IMAGES_DIR = Path("research_outputs/images")


def _get_shangtang_api_key() -> Tuple[str, str]:
    """Get Shangtang API credentials from ModelManager."""
    manager = get_model_manager()
    provider = manager.get_provider("shangtang")
    if not provider:
        return "", ""
    return provider.api_key or "", provider.config.base_url


def generate_image(
    prompt: str,
    output_path: str,
    model: str = "sensenova-u1-fast",
    size: str = "2048x2048",
    provider_name: str = "shangtang",
) -> Tuple[bool, str]:
    """Generate an image using the Shangtang SenseNova API.

    Args:
        prompt: Text description of the image to generate
        output_path: Local path to save the generated image
        model: Model name (default: sensenova-u1-fast)
        size: Image size - supported: 1664x2496, 2496x1664, 1760x2368, 2368x1760,
              1824x2272, 2272x1824, 2048x2048, 2752x1536, 1536x2752, 3072x1376, 1344x3136
        provider_name: Provider name (default: shangtang)

    Returns:
        Tuple of (success: bool, file_path_or_error: str)
    """
    api_key, base_url = _get_shangtang_api_key()
    if not api_key:
        return False, "Shangtang API key not found"

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1: Call the image generation API
        url = f"{base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }

        print(f"  🎨 Generating image: {prompt[:60]}...")
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Step 2: Extract image URL from response
        image_url = ""
        if "data" in data and len(data["data"]) > 0:
            image_url = data["data"][0].get("url", "")
        if not image_url:
            return False, f"No image URL in response: {json.dumps(data, ensure_ascii=False)[:200]}"

        # Step 3: Download the image
        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        # Step 4: Verify and optionally resize
        try:
            with PILImage.open(output_path) as img:
                print(f"  ✅ Image saved: {output_path} ({img.size[0]}x{img.size[1]})")
        except Exception:
            print(f"  ⚠️  Image saved (could not verify: {output_path})")

        return True, output_path

    except requests.exceptions.Timeout:
        return False, "Image generation request timed out (120s)"
    except requests.exceptions.RequestException as e:
        return False, f"Image generation request failed: {e}"
    except Exception as e:
        return False, f"Image generation failed: {e}"


def generate_diagram_description(section_title: str, section_content: str, llm) -> Optional[str]:
    """Use LLM to generate an image prompt for a specific section of the report.

    Analyzes the section content and creates a detailed prompt suitable for
    text-to-image generation, producing academic-style illustrations.

    Args:
        section_title: Title of the section (e.g., "Methodology", "Results")
        section_content: Text content of the section
        llm: ChatOpenAI instance

    Returns:
        Image prompt string, or None if no suitable image opportunity
    """
    prompt = f"""You are helping to generate illustrations for an academic research paper.
Analyze the following section and decide if an image would enhance understanding.

Section Title: {section_title}

Section Content:
{section_content[:1500]}

If an image would be valuable, generate a detailed English prompt for a text-to-image AI model.
The prompt should describe a clean, academic-style illustration suitable for a research paper.

Requirements:
- Describe the visual clearly and concretely (what to draw, colors, layout)
- Style: "flat vector illustration, clean academic diagram style, white background, professional"
- Include specific technical elements mentioned in the text
- Output ONLY the prompt text, or "NO_IMAGE_NEEDED" if no image is warranted

Good examples of what to illustrate:
- Architecture diagrams showing system components and data flow
- Comparison of approaches (before/after, side-by-side)
- Conceptual illustrations of key ideas
- Workflow/process diagrams

Do NOT generate prompts for:
- Purely textual content
- Mathematical equations
- Tables of data
"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        result = response.content if hasattr(response, 'content') else str(response)
        result = result.strip()

        if result == "NO_IMAGE_NEEDED" or not result:
            return None
        return result
    except Exception as e:
        print(f"  ⚠️  Diagram prompt generation failed: {e}")
        return None


def split_report_into_sections(report_text: str) -> List[Dict[str, str]]:
    """Split a report markdown text into sections for image analysis.

    Args:
        report_text: Full report text in Markdown

    Returns:
        List of {"title": str, "content": str} dicts
    """
    sections = []
    lines = report_text.split("\n")
    current_title = ""
    current_content = []

    for line in lines:
        # H2 heading — save previous section, start new one
        if line.startswith("## ") and not line.startswith("### "):
            if current_content:
                sections.append({
                    "title": current_title or "Title",
                    "content": "\n".join(current_content).strip(),
                })
            current_title = line.lstrip("#").strip()
            current_content = []
        elif line.startswith("# ") and not line.startswith("## "):
            # H1 heading — set as title for next section
            if current_content:
                sections.append({
                    "title": current_title or "Title",
                    "content": "\n".join(current_content).strip(),
                })
            current_title = line.lstrip("#").strip()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections.append({
            "title": current_title or "Abstract",
            "content": "\n".join(current_content).strip(),
        })

    return sections


def enhance_report_with_images(
    report_text: str,
    llm,
    output_dir: Optional[str] = None,
    max_images: int = 3,
) -> List[Dict]:
    """Post-process a report to generate relevant images.

    Analyzes the report sections, identifies opportunities for illustrations,
    generates images using the AI API, and returns metadata for embedding.

    Args:
        report_text: The full report text (Markdown)
        llm: ChatOpenAI instance for analysis
        output_dir: Directory to save images (default: research_outputs/images/
                     {timestamp}/)
        max_images: Maximum number of images to generate (default: 3)

    Returns:
        List of dicts with keys:
            - section: Section title the image belongs to
            - prompt: The image generation prompt used
            - file_path: Path to the generated image file
            - caption: Suggested caption for the image
            - success: Whether generation succeeded
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(IMAGES_DIR / timestamp)

    os.makedirs(output_dir, exist_ok=True)

    sections = split_report_into_sections(report_text)
    results = []
    images_generated = 0

    for section in sections:
        if images_generated >= max_images:
            break

        title = section["title"]
        # Skip sections unlikely to need images
        if title.lower() in ("references", "abstract", "conclusion"):
            continue
        if len(section["content"]) < 100:
            continue

        image_prompt = generate_diagram_description(title, section["content"], llm)
        if not image_prompt:
            continue

        # Create safe filename from section title
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        safe_name = safe_name.strip().replace(" ", "_")[:40]
        output_path = os.path.join(output_dir, f"{safe_name}.png")

        success, file_path = generate_image(image_prompt, output_path)

        # Convert to absolute path for reliable embedding
        abs_file_path = os.path.abspath(file_path) if success else ""

        caption = f"Figure: {title}"
        results.append({
            "section": title,
            "prompt": image_prompt,
            "file_path": abs_file_path,
            "caption": caption,
            "success": success,
        })

        if success:
            images_generated += 1

    return results


def embed_images_in_markdown(report_text: str, image_data: List[Dict]) -> str:
    """Insert image references into the report markdown.

    Places ![caption](path) after the section heading that matches.

    Args:
        report_text: Original report markdown
        image_data: List of image metadata from enhance_report_with_images()

    Returns:
        Updated markdown with image references inserted
    """
    if not image_data:
        return report_text

    lines = report_text.split("\n")
    result_lines = []
    inserted = set()

    for line in lines:
        result_lines.append(line)
        if line.startswith("## ") and not line.startswith("### "):
            section_title = line.lstrip("#").strip()
            for img in image_data:
                if img.get("section") == section_title and img.get("success") and section_title not in inserted:
                    rel_path = img["file_path"]
                    caption = img.get("caption", "Figure")
                    result_lines.append("")
                    result_lines.append(f"![{caption}]({rel_path})")
                    result_lines.append(f"*{caption}*")
                    result_lines.append("")
                    inserted.add(section_title)

    return "\n".join(result_lines)