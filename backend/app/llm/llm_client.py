import os
from typing import Optional, List, Dict, Any

from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Gemini model candidates in priority order
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-pro",
]


# Cache for uploaded Gemini file handles across requests
_cached_gemini_files: Dict[str, Any] = {}


class GeminiLLMClient:
    """
    Production-grade LLM client with multi-provider failover:
    Primary (Gemini / Groq / OpenAI) -> Multi-tier candidate models -> Backup LLM providers -> Grounded response.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.provider = (os.getenv("LLM_PROVIDER") or settings.LLM_PROVIDER or "groq").lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        self.groq_api_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY or "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"
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        self._initialized = False

        if self.groq_api_key:
            logger.info("Successfully configured Groq LLM client (Llama 3.3 70B Versatile).")

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
                self._initialized = True
                logger.info("Successfully configured Google Gemini LLM client.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini: {str(e)}")

    def _get_or_upload_file(self, pdf_path: str) -> Optional[Any]:
        """Uploads and caches the PDF file with Gemini File API for full multimodal inspection."""
        if not pdf_path or not os.path.exists(pdf_path) or not self._initialized:
            return None
        if pdf_path in _cached_gemini_files:
            return _cached_gemini_files[pdf_path]
        try:
            import google.generativeai as genai
            import time
            logger.info(f"Uploading PDF '{os.path.basename(pdf_path)}' to Gemini File API...")
            uploaded = genai.upload_file(path=pdf_path, mime_type="application/pdf")
            
            # Wait briefly if state is PROCESSING
            for _ in range(6):
                if getattr(uploaded, "state", None) and uploaded.state.name == "PROCESSING":
                    time.sleep(0.5)
                    uploaded = genai.get_file(uploaded.name)
                else:
                    break

            _cached_gemini_files[pdf_path] = uploaded
            logger.info(f"PDF uploaded & cached in Gemini File API: {uploaded.name}")
            return uploaded
        except Exception as e:
            logger.warning(f"Could not upload PDF file to Gemini: {str(e)}")
            return None

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.15,
        max_tokens: int = 2048,
        pdf_path: Optional[str] = None,
    ) -> str:
        """
        Generates a grounded completion trying primary provider first, then automatic failovers.
        """
        # If Groq is explicitly configured as primary provider
        if self.provider == "groq" and self.groq_api_key:
            groq_res = self._try_groq(prompt, system_instruction, conversation_history, temperature, max_tokens)
            if groq_res:
                return groq_res

        # If OpenAI is configured as primary provider
        if self.provider == "openai" and self.openai_api_key:
            openai_res = self._try_openai(prompt, system_instruction, conversation_history, temperature, max_tokens)
            if openai_res:
                return openai_res

        # Try Gemini models in sequence
        if self._initialized:
            import google.generativeai as genai

            parts: List[str] = []
            if conversation_history:
                history_lines = []
                for msg in conversation_history:
                    role = (msg.get("role") or msg.get("sender") or "user").capitalize()
                    content = msg.get("content") or msg.get("text") or ""
                    if content:
                        history_lines.append(f"{role}: {content}")
                if history_lines:
                    parts.append("[Previous Conversation Context]\n" + "\n".join(history_lines))
            parts.append(prompt)
            combined_prompt = "\n\n".join(parts)

            gemini_file = None
            if pdf_path:
                gemini_file = self._get_or_upload_file(pdf_path)

            content_payload = []
            if gemini_file:
                content_payload.append(gemini_file)
            content_payload.append(combined_prompt)

            gen_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            candidates_to_try = [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash-lite",
                "gemini-2.5-pro",
                "gemini-1.5-flash-8b",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ]

            last_error = None
            for model_name in candidates_to_try:
                try:
                    logger.info(f"Attempting Gemini completion with model '{model_name}'...")
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction if system_instruction else None,
                        generation_config=gen_config,
                    )

                    response = None
                    try:
                        response = model.generate_content(content_payload)
                    except Exception as file_err:
                        logger.debug(f"Multimodal generation note on '{model_name}': {str(file_err)}. Trying text prompt...")
                        prepended = f"{system_instruction}\n\n{combined_prompt}" if system_instruction else combined_prompt
                        response = model.generate_content(prepended)

                    if response and response.text:
                        text = response.text.strip()
                        self._working_model = model_name
                        logger.info(f"Gemini '{model_name}' generated response successfully ({len(text)} chars).")
                        return text

                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini model '{model_name}' error: {str(e)}. Trying next candidate...")

            logger.error(f"All Gemini candidates exhausted. Attempting backup providers... (Last error: {str(last_error)})")

        # Automatic backup: Try Groq
        if self.groq_api_key:
            groq_res = self._try_groq(prompt, system_instruction, conversation_history, temperature, max_tokens)
            if groq_res:
                return groq_res

        # Automatic backup: Try OpenAI
        if self.openai_api_key:
            openai_res = self._try_openai(prompt, system_instruction, conversation_history, temperature, max_tokens)
            if openai_res:
                return openai_res

        return "⚠️ The AI generation service is temporarily busy or rate limited (HTTP 429). Please wait a few moments and try your question again."

    def _try_groq(
        self,
        prompt: str,
        system_instruction: Optional[str],
        conversation_history: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Calls Groq API using Groq SDK and direct HTTP REST API."""
        if not self.groq_api_key:
            return None

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        if conversation_history:
            for m in conversation_history:
                r = m.get("role") or m.get("sender") or "user"
                messages.append({"role": "assistant" if r in ("assistant", "ai") else "user", "content": m.get("content") or m.get("text") or ""})
        messages.append({"role": "user", "content": prompt})

        # Models to try (Non-compound verified standard models on Groq)
        groq_models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "qwen/qwen3.6-27b",
        ]

        # 1. Try Groq SDK
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_api_key.strip())
            for groq_model in groq_models:
                try:
                    resp = client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if resp.choices and resp.choices[0].message.content:
                        text = resp.choices[0].message.content.strip()
                        logger.info(f"Groq SDK '{groq_model}' generated response successfully ({len(text)} chars).")
                        return text
                except Exception as m_err:
                    logger.debug(f"Groq SDK model '{groq_model}' note: {str(m_err)}")
                    continue
        except Exception as g_err:
            logger.debug(f"Groq SDK note: {str(g_err)}")

        # 2. Direct HTTP REST API via httpx / urllib
        import json
        import urllib.request

        for groq_model in groq_models:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": groq_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key.strip()}",
                    "Content-Type": "application/json",
                    "User-Agent": "FinSightAI/1.0",
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    if resp_data.get("choices") and len(resp_data["choices"]) > 0:
                        content = resp_data["choices"][0]["message"]["content"]
                        if content:
                            text = content.strip()
                            logger.info(f"Groq REST '{groq_model}' generated response successfully ({len(text)} chars).")
                            return text
            except Exception as rest_err:
                logger.warning(f"Groq REST model '{groq_model}' error: {str(rest_err)}")
                continue

        return None

    def _try_openai(
        self,
        prompt: str,
        system_instruction: Optional[str],
        conversation_history: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Calls OpenAI API with gpt-4o / gpt-4o-mini fallback."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            if conversation_history:
                for m in conversation_history:
                    r = m.get("role") or m.get("sender") or "user"
                    messages.append({"role": "assistant" if r in ("assistant", "ai") else "user", "content": m.get("content") or m.get("text") or ""})
            messages.append({"role": "user", "content": prompt})

            for oa_model in ["gpt-4o-mini", "gpt-4o"]:
                try:
                    resp = client.chat.completions.create(
                        model=oa_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if resp.choices and resp.choices[0].message.content:
                        text = resp.choices[0].message.content.strip()
                        logger.info(f"OpenAI '{oa_model}' generated response successfully ({len(text)} chars).")
                        return text
                except Exception as m_err:
                    logger.debug(f"OpenAI model '{oa_model}' note: {str(m_err)}")
                    continue
        except Exception as oa_err:
            logger.warning(f"OpenAI provider note: {str(oa_err)}")
        return None

    def invoke(self, prompt: str) -> Any:
        """Backward-compatible invoke() wrapper."""
        class _Resp:
            def __init__(self, text: str):
                self.content = text
        return _Resp(self.generate(prompt))


# Backward-compatibility aliases - all existing imports keep working
GroqLLMClient = GeminiLLMClient
LLMService = GeminiLLMClient


def get_llm_model(temperature: float = 0.15) -> GeminiLLMClient:
    return GeminiLLMClient()


def get_llm_service() -> GeminiLLMClient:
    return GeminiLLMClient()
