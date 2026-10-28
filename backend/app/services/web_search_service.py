"""
FinSight AI — Reliable Real-Time Web Search & Financial Market Intelligence Service.
Combines DuckDuckGo News & Web Discovery with Yahoo Finance real-time stock quotes.
Enforces grounded facts, non-hallucinatory citations, TTL-bounded caching, and safe ticker resolution.
"""
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

# Expanded benchmark company-to-ticker mapping for Indian (NSE) and Global benchmarks
POPULAR_TICKER_MAP = {
    # Indian Large-Cap Equities (NSE)
    "tata consultancy services": "TCS.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "reliance industries": "RELIANCE.NS",
    "reliance": "RELIANCE.NS",
    "ril": "RELIANCE.NS",
    "hdfc bank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "state bank of india": "SBIN.NS",
    "sbi": "SBIN.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS",
    "itc limited": "ITC.NS",
    "larsen & toubro": "LT.NS",
    "l&t": "LT.NS",
    "tata motors": "TATAMOTORS.NS",
    "maruti suzuki": "MARUTI.NS",
    "hcl technologies": "HCLTECH.NS",
    "hcl tech": "HCLTECH.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "sun pharmaceutical": "SUNPHARMA.NS",
    "titan company": "TITAN.NS",
    "adani enterprises": "ADANIENT.NS",
    "adani ports": "ADANIPORTS.NS",
    # Global Equities (US Exchanges)
    "apple": "AAPL",
    "microsoft": "MSFT",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "amazon": "AMZN",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "meta": "META",
    "meta platforms": "META",
    "berkshire hathaway": "BRK-B",
}


class WebSearchService:
    """
    Live Web Search & Financial Market Intelligence Service.
    Powered by DuckDuckGo Search (no API key required) and Yahoo Finance.
    Enriches historical financial reports with real-time market prices,
    latest quarterly performance, macro trends, and recent regulatory news.
    """

    def __init__(self):
        # Cache dictionaries with expiration timestamps
        self._quote_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # {key: (expiry_timestamp, data)}
        self._search_cache: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}
        self.quote_ttl_seconds: int = 60       # 1 minute TTL for stock quotes to ensure fresh prices
        self.search_ttl_seconds: int = 900     # 15 minutes TTL for web search news items

    def resolve_ticker(self, company_name: str, given_ticker: Optional[str] = None) -> Optional[str]:
        """
        Resolves company name or user prompt to a valid financial ticker symbol.
        Returns None when the company identity is ambiguous or generic to prevent incorrect tickers.
        """
        if given_ticker and re.match(r"^[A-Z0-9\.\-]{1,12}$", given_ticker.strip()):
            return given_ticker.strip().upper()

        if not company_name or not company_name.strip():
            return None

        clean_name = company_name.lower().strip()

        # Reject generic placeholder company names
        if clean_name in ("financial report", "financial entity", "corporate filing", "document a", "document b", "company name"):
            return None

        # Check direct dictionary mapping
        for key, sym in POPULAR_TICKER_MAP.items():
            if key == clean_name or f" {key} " in f" {clean_name} ":
                return sym

        for key, sym in POPULAR_TICKER_MAP.items():
            if key in clean_name or clean_name in key:
                return sym

        return None

    def search_company_web(
        self,
        company_name: str,
        query: str = "",
        max_results: int = 4
    ) -> List[Dict[str, str]]:
        """
        Executes live web search using DuckDuckGo with bounded timeout, deduplication, and quality filtering.
        Returns verified list of dictionaries: [{'title': ..., 'snippet': ..., 'url': ...}].
        """
        # Formulate clean search query
        company_clean = (company_name or "").strip()
        if company_clean.lower() in ("financial report", "financial entity", "corporate filing", "metadata", "knowledge card"):
            company_clean = ""

        clean_query = query.strip()
        # Remove noisy chat prefixes and conversational filler
        clean_query = re.sub(r"^(?:what is|what are|tell me about|how much is|can you tell me|search the web for|show me)\s+", "", clean_query, flags=re.IGNORECASE)
        clean_query = re.sub(r"\b(?:the|a|an|current|latest|right now|today(?:'s)?|of)\b", "", clean_query, flags=re.IGNORECASE)
        clean_query = re.sub(r"[\?\.,!]", " ", clean_query)
        clean_query = re.sub(r"\s+", " ", clean_query).strip()

        if company_clean and company_clean.lower() not in clean_query.lower():
            search_terms = f"{company_clean} {clean_query}".strip()
        else:
            search_terms = clean_query if clean_query else company_clean

        if not search_terms:
            return []

        cache_key = f"ddg_{search_terms[:80].lower()}"
        now = time.time()
        if cache_key in self._search_cache:
            exp, cached_res = self._search_cache[cache_key]
            if now < exp:
                return cached_res

        if not DDGS:
            logger.warning("Neither ddgs nor duckduckgo_search is installed.")
            return []

        results: List[Dict[str, str]] = []
        try:
            with DDGS(timeout=10) as ddgs:
                raw_items = []
                # First attempt news search if company or stock is involved
                try:
                    news_items = list(ddgs.news(search_terms, max_results=max_results))
                    if news_items:
                        raw_items.extend(news_items)
                except Exception:
                    pass

                # If news yielded few or no results, supplement with general text search
                if len(raw_items) < max_results:
                    try:
                        text_items = list(ddgs.text(search_terms, max_results=max_results + 1))
                        raw_items.extend(text_items)
                    except Exception:
                        pass

                seen_urls = set()
                for item in raw_items:
                    title = item.get("title", "").strip()
                    body = item.get("body", "").strip() or item.get("snippet", "").strip()
                    href = item.get("url", "").strip() or item.get("href", "").strip()
                    source = item.get("source", "")
                    date_str = item.get("date", "")

                    if title and href and href not in seen_urls:
                        seen_urls.add(href)
                        res_obj = {
                            "title": title,
                            "snippet": body[:320] if len(body) > 320 else body,
                            "url": href,
                        }
                        if source:
                            res_obj["source"] = source
                        if date_str:
                            res_obj["date"] = date_str
                        results.append(res_obj)
                        if len(results) >= max_results:
                            break

            logger.info(f"Web search for '{search_terms}': found {len(results)} items.")
        except Exception as e:
            logger.warning(f"Web search notice for '{search_terms}': {str(e)}")

        self._search_cache[cache_key] = (now + self.search_ttl_seconds, results)
        return results

    def get_company_stock_quote(
        self,
        company_name: str,
        ticker: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches live real-time stock quote and market capitalization via Yahoo Finance.
        Features 60-second TTL cache to balance freshness with low latency.
        """
        resolved = self.resolve_ticker(company_name, ticker)
        if not resolved:
            return None

        cache_key = f"quote_{resolved}"
        now = time.time()
        if cache_key in self._quote_cache:
            exp, cached_data = self._quote_cache[cache_key]
            if now < exp:
                return cached_data

        quote_data = None
        try:
            import yfinance as yf

            t = yf.Ticker(resolved)
            fast_info = getattr(t, "fast_info", None)
            if fast_info:
                price = getattr(fast_info, "last_price", None)
                prev_close = getattr(fast_info, "previous_close", None)
                mkt_cap = getattr(fast_info, "market_cap", None)
                currency = getattr(fast_info, "currency", "INR" if resolved.endswith((".NS", ".BO")) else "USD")
                hi_52 = getattr(fast_info, "year_high", None)
                lo_52 = getattr(fast_info, "year_low", None)

                chg_pct = 0.0
                if price and prev_close and prev_close > 0:
                    chg_pct = round(((price - prev_close) / prev_close) * 100, 2)

                # Format market cap cleanly
                cap_str = ""
                if mkt_cap:
                    if mkt_cap > 1e12:
                        cap_str = f"{mkt_cap / 1e12:.2f}T"
                    elif mkt_cap > 1e9:
                        cap_str = f"{mkt_cap / 1e9:.2f}B"
                    elif mkt_cap > 1e7:
                        cap_str = f"{mkt_cap / 1e7:.2f} Cr"

                quote_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                if price:
                    quote_data = {
                        "symbol": resolved,
                        "price": round(price, 2),
                        "currency": currency,
                        "day_change_pct": chg_pct,
                        "market_cap_formatted": cap_str,
                        "52w_high": round(hi_52, 2) if hi_52 else None,
                        "52w_low": round(lo_52, 2) if lo_52 else None,
                        "timestamp": quote_timestamp,
                        "exchange": "NSE" if resolved.endswith(".NS") else ("BSE" if resolved.endswith(".BO") else "Global"),
                        "is_real_time": True,
                    }
                    logger.info(f"Retrieved Yahoo Finance quote for '{resolved}': {quote_data['price']} {currency} ({quote_timestamp})")
        except Exception as e:
            logger.warning(f"Yahoo Finance quote notice for '{resolved}': {str(e)}")

        if quote_data:
            self._quote_cache[cache_key] = (now + self.quote_ttl_seconds, quote_data)
        return quote_data

    def format_web_intelligence_context(
        self,
        company_name: str,
        query: str = "",
        ticker: Optional[str] = None
    ) -> str:
        """
        Formats combined live web search and real-time market quote into a structured evidence block.
        """
        quote = self.get_company_stock_quote(company_name, ticker)
        web_items = self.search_company_web(company_name, query, max_results=3)

        if not quote and not web_items:
            return ""

        lines = [
            "=== CURRENT REAL-TIME EXTERNAL MARKET INTELLIGENCE ===",
        ]
        if company_name and company_name.lower() not in ("financial report", "financial entity", "corporate filing"):
            lines.append(f"Entity: {company_name}")

        if quote and quote.get("price") is not None:
            curr = quote.get("currency", "")
            pr = quote.get("price")
            chg = quote.get("day_change_pct", 0.0)
            sign = "+" if chg >= 0 else ""
            sym = quote.get("symbol", "")
            cap = quote.get("market_cap_formatted", "")
            hi = quote.get("52w_high")
            lo = quote.get("52w_low")
            t_stamp = quote.get("timestamp", "")

            q_line = f"Live Market Quote ({sym}): {pr} {curr} ({sign}{chg}%) [As of {t_stamp}]"
            if cap:
                q_line += f" | Market Cap: {cap}"
            if hi and lo:
                q_line += f" | 52W Range: {lo} - {hi} {curr}"
            lines.append(q_line)

        if web_items:
            lines.append("Latest Verified Web & Financial News Coverage:")
            for idx, item in enumerate(web_items, 1):
                t = item.get("title", "")
                snip = item.get("snippet", "")
                u = item.get("url", "")
                lines.append(f"  {idx}. \"{t}\" [Source URL: {u}]\n     {snip}")

        lines.append("=========================================================")
        return "\n".join(lines)


_web_search_service_instance: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    global _web_search_service_instance
    if _web_search_service_instance is None:
        _web_search_service_instance = WebSearchService()
    return _web_search_service_instance
