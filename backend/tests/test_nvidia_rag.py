import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.llm.nvidia_client import (
    NvidiaRAGClient,
    rerank_passages_nvidia,
    NVIDIA_BASE_URL,
    CHAT_MODELS,
    EMBEDDING_MODELS,
    RERANK_MODELS,
)


def test_nvidia_client_initialization_and_urls():
    """Verify NVIDIA base URL and catalog models."""
    client = NvidiaRAGClient(api_key="nvapi-test123")
    assert client.base_url == "https://integrate.api.nvidia.com/v1"
    assert "moonshotai/kimi-k3" in CHAT_MODELS
    assert "nvidia/llama-3.2-nv-embedqa-1b-v2" in EMBEDDING_MODELS
    assert "nvidia/llama-3.2-nv-rerankqa-1b-v2" in RERANK_MODELS
    assert client.get_headers()["Authorization"] == "Bearer nvapi-test123"


def test_nvidia_chat_completion_routing():
    """Verify chat completion routes to /v1/chat/completions."""
    client = NvidiaRAGClient(api_key="nvapi-test123")

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="EBITDA is Operating Profit plus D&A."))]
    
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = mock_resp
    client._openai_client = mock_openai

    messages = [{"role": "user", "content": "What is EBITDA?"}]
    res = client.chat_completion(messages=messages, model="moonshotai/kimi-k3")

    assert res == "EBITDA is Operating Profit plus D&A."
    mock_openai.chat.completions.create.assert_called_once_with(
        model="moonshotai/kimi-k3",
        messages=messages,
        temperature=0.15,
        max_tokens=2048,
    )


def test_nvidia_embeddings_routing():
    """Verify embeddings route to /v1/embeddings with input_type."""
    client = NvidiaRAGClient(api_key="nvapi-test123")

    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json.return_value = {
        "data": [
            {"embedding": [0.12, -0.34, 0.56, 0.78]},
            {"embedding": [0.05, 0.11, -0.22, 0.99]}
        ]
    }

    with patch("requests.post", return_value=mock_http_resp) as mock_post:
        texts = ["Revenue Statement", "Balance Sheet"]
        embeddings = client.create_embeddings(
            texts=texts,
            model="nvidia/llama-3.2-nv-embedqa-1b-v2",
            input_type="passage"
        )
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 4
        mock_post.assert_called_once_with(
            "https://integrate.api.nvidia.com/v1/embeddings",
            headers=client.get_headers(),
            json={
                "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
                "input": texts,
                "input_type": "passage",
                "encoding_format": "float",
            },
            timeout=30,
        )


def test_nvidia_reranking_routing():
    """Verify reranking routes to /v1/ranking with query and passages."""
    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json.return_value = {
        "rankings": [
            {"index": 1, "logit": 4.52},
            {"index": 0, "logit": 1.21}
        ]
    }

    with patch("requests.post", return_value=mock_http_resp) as mock_post:
        rankings = rerank_passages_nvidia(
            query="What is total revenue?",
            passages=[{"text": "Operating cost $50M"}, {"text": "Total revenue $120M"}],
            api_key="nvapi-test123",
            model="nvidia/llama-3.2-nv-rerankqa-1b-v2",
            top_n=2
        )
        assert len(rankings) == 2
        assert rankings[0]["index"] == 1
        assert rankings[0]["logit"] == 4.52

        mock_post.assert_called_once_with(
            "https://integrate.api.nvidia.com/v1/ranking",
            headers={
                "Authorization": "Bearer nvapi-test123",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FinSightAI/1.0",
            },
            json={
                "model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
                "query": {"text": "What is total revenue?"},
                "passages": [{"text": "Operating cost $50M"}, {"text": "Total revenue $120M"}],
                "top_n": 2,
            },
            timeout=30,
        )
