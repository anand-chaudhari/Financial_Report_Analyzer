"""
FinSight AI - NVIDIA NIM Dedicated Integration Layer
Provides strictly routed API endpoints for:
1. Chat & Generation: POST https://integrate.api.nvidia.com/v1/chat/completions (moonshotai/kimi-k3, meta/llama-3.3-70b-instruct, deepseek-ai/...)
2. Embeddings: POST https://integrate.api.nvidia.com/v1/embeddings (nvidia/llama-3.2-nv-embedqa-1b-v2 with input_type='query'|'passage')
3. Reranking: POST https://integrate.api.nvidia.com/v1/ranking (nvidia/llama-3.2-nv-rerankqa-1b-v2)
"""
import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger("app.llm.nvidia_client")

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Supported Catalog Models
CHAT_MODELS = [
    "moonshotai/kimi-k3",
    "meta/llama-3.2-90b-vision-instruct",
    "mistralai/mistral-large",
    "nv-mistralai/mistral-nemo-12b-instruct",
    "meta/llama-3.3-70b-instruct",
]

EMBEDDING_MODELS = [
    "nvidia/llama-3.2-nv-embedqa-1b-v2",
    "nvidia/nemotron-3-embed-1b",
    "baai/bge-m3",
]

RERANK_MODELS = [
    "nvidia/llama-3.2-nv-rerankqa-1b-v2",
    "nvidia/llama-nemotron-rerank-1b-v2",
]


class NvidiaRAGClient:
    """
    Dedicated client for NVIDIA NIM APIs adhering strictly to NVIDIA endpoint specifications.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = NVIDIA_BASE_URL):
        self.api_key = (api_key or os.getenv("NVIDIA_API_KEY") or "").strip()
        self.base_url = base_url.rstrip("/")
        self._openai_client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                logger.info(f"NvidiaRAGClient initialized with base_url '{self.base_url}'.")
            except Exception as e:
                logger.debug(f"OpenAI SDK client init for NVIDIA note: {str(e)}")

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FinSightAI/1.0",
        }

    # -------------------------------------------------------------------------
    # 1. Chat Completion / Generation (POST /v1/chat/completions)
    # -------------------------------------------------------------------------
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "moonshotai/kimi-k3",
        temperature: float = 0.15,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Optional[str]:
        """
        Routes generation strictly to POST https://integrate.api.nvidia.com/v1/chat/completions.
        """
        if not self.is_available:
            return None

        models_to_try = [model] + [m for m in CHAT_MODELS if m != model]

        # 1. Try via OpenAI SDK client
        if self._openai_client and not stream:
            for m in models_to_try:
                try:
                    logger.info(f"NVIDIA Chat Completion -> Requesting '{m}'...")
                    resp = self._openai_client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if resp.choices and resp.choices[0].message.content:
                        text = resp.choices[0].message.content.strip()
                        logger.info(f"NVIDIA '{m}' responded successfully ({len(text)} chars).")
                        return text
                except Exception as ex:
                    logger.warning(f"NVIDIA SDK chat model '{m}' error: {str(ex)}")
                    continue

        # 2. REST Request Fallback
        url = f"{self.base_url}/chat/completions"
        headers = self.get_headers()

        for m in models_to_try:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": stream,
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=35)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices and choices[0].get("message", {}).get("content"):
                        text = choices[0]["message"]["content"].strip()
                        logger.info(f"NVIDIA REST '{m}' responded successfully ({len(text)} chars).")
                        return text
                else:
                    logger.warning(f"NVIDIA REST '{m}' returned HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as ex:
                logger.warning(f"NVIDIA REST chat error on '{m}': {str(ex)}")
                continue

        return None

    # -------------------------------------------------------------------------
    # 2. Embeddings (POST /v1/embeddings with input_type)
    # -------------------------------------------------------------------------
    def create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2",
        input_type: str = "query",  # "query" for search queries, "passage" for documents
    ) -> Optional[List[List[float]]]:
        """
        Routes embedding generation strictly to POST https://integrate.api.nvidia.com/v1/embeddings.
        """
        if not self.is_available:
            return None

        if isinstance(texts, str):
            texts = [texts]

        url = f"{self.base_url}/embeddings"
        headers = self.get_headers()

        models_to_try = [model] + [m for m in EMBEDDING_MODELS if m != model]

        for m in models_to_try:
            try:
                payload = {
                    "model": m,
                    "input": texts,
                    "input_type": input_type,
                    "encoding_format": "float",
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("data", [])
                    embeddings = [item["embedding"] for item in records if "embedding" in item]
                    if embeddings:
                        logger.info(f"NVIDIA Embedding '{m}' generated {len(embeddings)} vectors.")
                        return embeddings
                else:
                    logger.warning(f"NVIDIA Embedding '{m}' returned HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as ex:
                logger.warning(f"NVIDIA Embedding error on '{m}': {str(ex)}")
                continue

        return None

    # -------------------------------------------------------------------------
    # 3. Reranking (POST /v1/ranking)
    # -------------------------------------------------------------------------
    def rerank(
        self,
        query: str,
        passages: List[Union[str, Dict[str, Any]]],
        model: str = "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        top_n: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Executes semantic passage reranking via POST https://integrate.api.nvidia.com/v1/ranking.
        Returns sorted list of items with index and logit relevance scores.
        """
        if not self.is_available or not passages:
            return None

        url = f"{self.base_url}/ranking"
        headers = self.get_headers()

        # Format passage items according to NVIDIA ranking schema
        formatted_passages = []
        for p in passages:
            if isinstance(p, dict):
                text = p.get("text") or p.get("content") or json.dumps(p)
            else:
                text = str(p)
            formatted_passages.append({"text": text})

        models_to_try = [model] + [m for m in RERANK_MODELS if m != model]

        for m in models_to_try:
            try:
                payload: Dict[str, Any] = {
                    "model": m,
                    "query": {"text": query},
                    "passages": formatted_passages,
                }
                if top_n:
                    payload["top_n"] = top_n

                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    rankings = data.get("rankings", [])
                    if rankings:
                        logger.info(f"NVIDIA Rerank '{m}' scored {len(rankings)} passages.")
                        return rankings
                else:
                    logger.warning(f"NVIDIA Rerank '{m}' returned HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as ex:
                logger.warning(f"NVIDIA Rerank error on '{m}': {str(ex)}")
                continue

        return None


# Standalone Rerank Function as requested
def rerank_passages_nvidia(
    query: str,
    passages: List[Union[str, Dict[str, Any]]],
    api_key: Optional[str] = None,
    model: str = "nvidia/llama-3.2-nv-rerankqa-1b-v2",
    top_n: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Standalone function for reranking using requests.post to https://integrate.api.nvidia.com/v1/ranking.
    """
    client = NvidiaRAGClient(api_key=api_key)
    return client.rerank(query=query, passages=passages, model=model, top_n=top_n)


_nvidia_rag_client: Optional[NvidiaRAGClient] = None


def get_nvidia_rag_client() -> NvidiaRAGClient:
    """Singleton accessor for NvidiaRAGClient."""
    global _nvidia_rag_client
    if _nvidia_rag_client is None:
        _nvidia_rag_client = NvidiaRAGClient()
    return _nvidia_rag_client
