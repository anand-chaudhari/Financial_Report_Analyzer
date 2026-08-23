import os
from typing import Optional, List, Dict, Any
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class GroqLLMClient:
    """
    LLM client using Groq API with robust model fallback handling.
    If the primary model fails or is unavailable, automatically retries
    with fallback models in sequence.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GROQ_API_KEY
        self.candidate_models = settings.groq_model_candidates

        self._client = None
        if self.api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info("Initialized Groq LLM client.")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client SDK: {str(e)}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Generates text completion using Groq API with sequential model fallback retry.
        """
        if not self._client:
            logger.warning("Groq API client not initialized or API key missing.")
            return "I could not find sufficient information for this question in the uploaded report."

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        if conversation_history:
            for item in conversation_history:
                role = item.get("role") or item.get("sender") or "user"
                if role in ("user", "human"):
                    role = "user"
                elif role in ("assistant", "ai", "system"):
                    role = "assistant"
                content = item.get("content") or item.get("text") or ""
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        last_error = None
        # Sequential fallback execution across candidate models
        for model_name in self.candidate_models:
            try:
                logger.info(f"Attempting LLM completion using model '{model_name}'...")
                response = self._client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                )
                if response.choices and len(response.choices) > 0:
                    text = response.choices[0].message.content or ""
                    logger.info(f"Successfully generated response with model '{model_name}'.")
                    return text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"Groq model '{model_name}' execution failed: {str(e)}. Trying next fallback model...")

        logger.error(f"All candidate Groq models failed. Last error: {str(last_error)}")
        return "I could not find sufficient information for this question in the uploaded report."

    def invoke(self, prompt: str) -> Any:
        class MockResponse:
            def __init__(self, text: str):
                self.content = text
        return MockResponse(self.generate(prompt))


# Backward compatibility aliases
LLMService = GroqLLMClient

def get_llm_model(temperature: float = 0.1) -> GroqLLMClient:
    return GroqLLMClient()

def get_llm_service() -> GroqLLMClient:
    return GroqLLMClient()
