"""
FinSight AI — Smart Intent & Real-Time Query Router.
Classifies user inquiries into 5 standardized categories to automatically determine
retrieval strategy, web search necessity, and conversational handling.

Categories:
- GENERAL_CONVERSATION: Greetings, capabilities, identity, general financial definitions (no PDF or web needed).
- DOCUMENT_QUESTION: Factual corporate filing questions (uses uploaded PDF RAG + Knowledge Card).
- REALTIME_CURRENT: Real-time stock prices, breaking news, leadership changes, current acquisitions (uses Web Search / Yahoo Finance).
- MIXED_FINANCIAL: Cross-temporal synthesis comparing historical filing data with current market news/quotes.
- OUT_OF_SCOPE: Completely unrelated non-business inquiries (weather, cooking, poetry, trivia).
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class IntentType:
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    DOCUMENT_QUESTION = "DOCUMENT_QUESTION"
    REALTIME_CURRENT = "REALTIME_CURRENT"
    MIXED_FINANCIAL = "MIXED_FINANCIAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class IntentRouter:
    """
    Lightweight, deterministic, and context-aware intent classification router.
    Resolves retrieval need and web search requirements based on inquiry semantics,
    active document availability, and explicit user toggle setting.
    """

    def __init__(self):
        # 1. Greetings & Capabilities
        self._greetings = {
            "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon",
            "good evening", "how are you", "who are you", "what can you do", "what is your name",
            "tell me about yourself", "what are your features", "who built you", "thank you",
            "thanks", "bye", "goodbye", "help me", "what is finsight", "what is finsight ai"
        }

        # 2. General Financial Definitions & Concepts (No PDF needed)
        self._concept_patterns = [
            r"\bwhat is (?:a |an |the )?(?:price[- ]to[- ]earnings|p/e|pe ratio|ebitda|roe|roa|roce|fcf|free cash flow|working capital|capex|opex|book value|goodwill|depreciation|amortization|market cap|dividend yield|ratio)\b",
            r"\bexplain (?:price[- ]to[- ]earnings|p/e|ebitda|p/e ratio|working capital|cash flow statement|balance sheet|income statement|debt to equity|current ratio|quick ratio)\b",
            r"\bhow (?:is|to calculate) (?:ebitda|eps|roe|roa|working capital|pe ratio|price to earnings)\b",
            r"\bdifference between (?:capex and opex|pbt and pat|gross and net margin|debt and equity)\b",
            r"\bformula for (?:ebitda|pe ratio|roe|current ratio|working capital|price to earnings)\b",
            r"\bdefine (?:ebitda|amortization|depreciation|liquidity|leverage|pe ratio)\b",
        ]

        # 3. Real-Time & Market Data Indicators (Category C)
        self._realtime_indicators = [
            r"\b(?:share|stock)\s+price\b",
            r"\b(?:current|latest|today(?:'s)?|right now|live)\s+(?:price|quote|trading|market cap|valuation|rate)\b",
            r"\bwhat is (?:the|its|their)?\s*(?:current|latest|today(?:'s)?|live)\s*(?:share|stock)?\s*price\b",
            r"\b(?:latest|breaking|recent|today(?:'s)?)\s+(?:news|announcements?|headlines?|updates?|developments?)\b",
            r"\bwhat happened (?:in the stock market|to (?:the|this)? stock|today|recently)\b",
            r"\bwho is (?:the )?(?:current |new )?(?:ceo|cfo|chairman|managing director|leader)\b",
            r"\b(?:latest|recent|new|upcoming)\s+(?:quarterly results|quarterly performance|q[1-4] results|earnings call|earnings release)\b",
            r"\bhas (?:the company|it) announced (?:any )?(?:new )?(?:acquisitions?|mergers?|buybacks?|dividends?)\b",
            r"\bwhat is the market sentiment\b",
            r"\bhow is the stock performing today\b",
            r"\b52\s*(?:week|w)\s*(?:high|low)\b",
        ]

        # 4. Mixed Financial Indicators (Category D)
        self._mixed_indicators = [
            r"\b(?:compare|how does|what has changed).*?(?:current|latest|today|now).*?(?:report|filing|fy\s*\d{2,4}|historical|pdf)\b",
            r"\b(?:compare|how does|what has changed).*?(?:report|filing|fy\s*\d{2,4}|historical|pdf).*?(?:current|latest|today|now)\b",
            r"\bhow does (?:.+?)?(?:current|latest|today's)\s*(?:share |stock )?price compare with\b",
            r"\bcompare (?:.+?)?(?:current|latest|today's|reported|historical|fy\s*\d{2,4})\b",
            r"\bwhat has changed since (?:this|the)? (?:annual report|report|filing) (?:was published|came out)\b",
            r"\bsince the (?:annual report|report|last filing)\b",
            r"\bvaluation based on current price and (?:fy\d+|historical|reported) earnings\b",
        ]

        # 5. Out of scope patterns (Category: Non-finance)
        self._out_of_scope_triggers = [
            r"\b(?:weather|recipe|write a poem|write a song|tell me a joke|movie recommendation|sing a song)\b",
            r"\b(?:football|cricket match|ipl score|fifa|basketball|tennis match)\b",
            r"\b(?:translate to french|translate to spanish|write a python script to scrape)\b",
        ]

    def classify(
        self,
        question: str,
        has_active_doc: bool = False,
        history: Optional[List[Dict[str, Any]]] = None,
        search_mode: str = "auto",
    ) -> Tuple[str, bool]:
        """
        Classifies query intent and returns (intent_category, should_web_search).

        search_mode options:
        - "auto": System decides automatically based on query semantics (default).
        - "on": Force web search enabled.
        - "off": Strictly disable web search (never overridden by intent classifier).
        """
        q_clean = question.strip().lower()
        mode = (search_mode or "auto").strip().lower()

        # Step 1: Out of scope check
        for pat in self._out_of_scope_triggers:
            if re.search(pat, q_clean):
                return IntentType.OUT_OF_SCOPE, False

        # Step 2: Greetings & capabilities
        q_words = re.findall(r"\b\w+\b", q_clean)
        if len(q_words) <= 3 and any(w in {"hi", "hello", "hey", "hola", "greetings"} for w in q_words):
            return IntentType.GENERAL_CONVERSATION, False

        for g in self._greetings:
            if g in q_clean and len(q_clean) < len(g) + 15:
                return IntentType.GENERAL_CONVERSATION, False

        # Step 3: General financial theory/concept (without report context)
        is_concept = False
        for pat in self._concept_patterns:
            if re.search(pat, q_clean):
                is_concept = True
                break

        if is_concept and "this report" not in q_clean and "this company" not in q_clean and not re.search(r"\bfy\s*20\d\d\b", q_clean):
            return IntentType.GENERAL_CONVERSATION, False

        # Step 4: Mixed Historical vs Current Question (Category D)
        is_mixed = False
        for pat in self._mixed_indicators:
            if re.search(pat, q_clean):
                is_mixed = True
                break

        if is_mixed:
            should_search = (mode != "off")
            return IntentType.MIXED_FINANCIAL, should_search

        # Step 5: Real-time / Current Market Questions (Category C)
        is_realtime = False
        for pat in self._realtime_indicators:
            if re.search(pat, q_clean):
                is_realtime = True
                break

        # Additional heuristics for real-time: mentions stock/price/ticker/today/latest
        if not is_realtime:
            has_time_term = any(w in q_clean for w in ["right now", "today", "latest", "current", "live"])
            has_market_term = any(w in q_clean for w in ["share price", "stock price", "market price", "trading at", "news", "ceo"])
            if has_time_term and has_market_term:
                is_realtime = True

        if is_realtime:
            should_search = (mode != "off")
            return IntentType.REALTIME_CURRENT, should_search

        # Step 6: Mode override if user explicitly set toggle to "on"
        if mode == "on":
            return IntentType.DOCUMENT_QUESTION, True

        # Step 7: Document Question vs General Conversation (Category B vs Category A)
        if not has_active_doc:
            return IntentType.GENERAL_CONVERSATION, False

        # In auto or off mode, default document questions do NOT trigger web search
        return IntentType.DOCUMENT_QUESTION, False


_intent_router_instance: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    global _intent_router_instance
    if _intent_router_instance is None:
        _intent_router_instance = IntentRouter()
    return _intent_router_instance
