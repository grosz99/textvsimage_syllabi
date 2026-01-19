"""
Anthropic API Service for Vision Analysis

Provides a wrapper around the Anthropic API for sending vision requests
to Claude for analyzing basketball boxscore screenshots.
"""

import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import anthropic


@dataclass
class VisionResponse:
    """Response from a vision analysis request."""
    answer: str
    confidence: float
    raw_response: str


class AnthropicService:
    """Service for interacting with the Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Anthropic service.

        Args:
            api_key: Anthropic API key
            model: Model to use for requests
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def encode_image(self, image_path: Path) -> tuple[str, str]:
        """
        Encode an image file to base64.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (base64_data, media_type)
        """
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determine media type from extension
        suffix = image_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")

        return image_data, media_type

    def analyze_image(
        self,
        image_path: Path,
        question: str,
        system_prompt: Optional[str] = None,
    ) -> VisionResponse:
        """
        Analyze an image using Claude Vision.

        Args:
            image_path: Path to the image to analyze
            question: Question to ask about the image
            system_prompt: Optional system prompt

        Returns:
            VisionResponse with answer and confidence
        """
        image_data, media_type = self.encode_image(image_path)

        default_system = """You are an expert basketball analyst analyzing game boxscores.
When answering questions about the boxscore image:
1. Look carefully at all player statistics shown
2. Provide a clear, concise answer
3. Include specific numbers from the boxscore
4. After your answer, on a new line, provide a confidence score from 0.0 to 1.0 in the format: CONFIDENCE: 0.XX

Focus on accuracy - the data in the image is the source of truth."""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": question,
                    },
                ],
            }
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt or default_system,
            messages=messages,
        )

        raw_text = response.content[0].text

        # Parse answer and confidence from response
        answer, confidence = self._parse_response(raw_text)

        return VisionResponse(
            answer=answer,
            confidence=confidence,
            raw_response=raw_text,
        )

    def _parse_response(self, response_text: str) -> tuple[str, float]:
        """
        Parse the answer and confidence from the response.

        Args:
            response_text: Raw response text from Claude

        Returns:
            Tuple of (answer, confidence)
        """
        lines = response_text.strip().split("\n")
        confidence = 0.85  # Default confidence
        answer_lines = []

        for line in lines:
            if line.upper().startswith("CONFIDENCE:"):
                try:
                    conf_str = line.split(":", 1)[1].strip()
                    confidence = float(conf_str)
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, IndexError):
                    pass
            else:
                answer_lines.append(line)

        answer = "\n".join(answer_lines).strip()

        return answer, confidence
