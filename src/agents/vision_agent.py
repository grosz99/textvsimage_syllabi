"""
Vision Agent for Basketball Boxscore Analysis

Analyzes dashboard screenshots using Claude Vision to answer
basketball analytics questions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.services.anthropic import AnthropicService, VisionResponse


@dataclass
class VisionAgentResult:
    """Result from the Vision Agent."""
    answer: Optional[str]
    confidence: float
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


class VisionAgent:
    """Agent that analyzes basketball boxscore screenshots."""

    def __init__(
        self,
        anthropic_service: AnthropicService,
        db_path: Optional[Path] = None,
        screenshots_dir: Optional[Path] = None,
    ):
        """
        Initialize the Vision Agent.

        Args:
            anthropic_service: Service for making API calls
            db_path: Path to database (optional, for context)
            screenshots_dir: Directory containing screenshots
        """
        self.anthropic = anthropic_service
        self.db_path = db_path
        self.screenshots_dir = screenshots_dir

    def ask(
        self,
        question: str,
        game_id: Optional[str] = None,
        screenshot_path: Optional[Path] = None,
    ) -> VisionAgentResult:
        """
        Ask a question about a basketball game using visual analysis.

        Args:
            question: The question to answer
            game_id: Game ID (used to find screenshot if path not provided)
            screenshot_path: Direct path to screenshot image

        Returns:
            VisionAgentResult with answer, confidence, and screenshot path
        """
        # Validate screenshot path
        if screenshot_path is None:
            return VisionAgentResult(
                answer=None,
                confidence=0.0,
                error="No screenshot path provided",
            )

        if not screenshot_path.exists():
            return VisionAgentResult(
                answer=None,
                confidence=0.0,
                error=f"Screenshot not found: {screenshot_path}",
            )

        # Build the analysis prompt
        prompt = self._build_prompt(question)

        try:
            # Call Claude Vision API
            response: VisionResponse = self.anthropic.analyze_image(
                image_path=screenshot_path,
                question=prompt,
            )

            return VisionAgentResult(
                answer=response.answer,
                confidence=response.confidence,
                screenshot_path=str(screenshot_path),
            )

        except Exception as e:
            return VisionAgentResult(
                answer=None,
                confidence=0.0,
                error=f"Vision analysis failed: {str(e)}",
            )

    def _build_prompt(self, question: str) -> str:
        """
        Build the prompt for Claude Vision.

        Args:
            question: User's question

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this basketball boxscore image and answer the following question:

Question: {question}

Instructions:
- Look at the complete boxscore data shown in the image
- Find the specific statistics needed to answer the question
- Provide a clear, direct answer with specific numbers
- If the question asks about "top" or "most", find the maximum value
- Include the player name and their team when relevant

Answer the question based solely on what you can see in the image."""
