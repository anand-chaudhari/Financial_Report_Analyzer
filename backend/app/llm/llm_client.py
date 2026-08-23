from typing import Optional, Any
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def get_llm_model(temperature: float = 0.1) -> Any:
    """
    Factory function initializing the configured LLM client (Gemini / OpenAI).
    """
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.DEFAULT_LLM_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {str(e)}")

    # Fallback / Mock LLM for local setup and testing
    logger.warning("No live LLM API key detected; returning MockLLM for local startup.")
    
    class MockLLM:
        def invoke(self, prompt: str) -> Any:
            class MockResponse:
                content = (
                    "Based on the financial report [Page 1], total revenue grew steadily. "
                    "Operating expenses remained controlled throughout the fiscal year [Page 3]."
                )
            return MockResponse()

        def __call__(self, prompt: str) -> Any:
            return self.invoke(prompt)

    return MockLLM()


class LLMService:
    """Service wrapping LLM interactions."""

    def __init__(self):
        self.llm = get_llm_model()

    def generate(self, prompt: str) -> str:
        """Invokes LLM with the provided prompt."""
        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            logger.error(f"LLM Generation Error: {str(e)}")
            return "An error occurred while generating the response."
