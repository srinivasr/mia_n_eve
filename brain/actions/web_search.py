#web_search.py

from utils.logger import setup_logger
logger = setup_logger(__name__)


def _gemini_search(query: str) -> str:
    import ollama
    from memory.config_manager import get_ollama_url, get_ollama_model
    results = _ddg_search(query, max_results=10)
    ddg_text = _format_ddg(query, results)
    
    client = ollama.Client(host=get_ollama_url())
    prompt = f"Based on these search results, answer the query: '{query}'\n\nResults:\n{ddg_text}"
    response = client.chat(model=get_ollama_model(), messages=[{"role": "user", "content": prompt}])
    
    text = response.get("message", {}).get("content", "").strip()
    if not text:
        raise ValueError("Model returned an empty response.")
    return text


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title":   r.get("title",  ""),
                "snippet": r.get("body",   ""),
                "url":     r.get("href",   ""),
            })
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()

def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        logger.info(f"Gemini compare failed: {e} — falling back to DDG")

    # DDG fallback: fetch results per item and merge
    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
    return "\n".join(lines)

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    if player:
        player.write_log(f"[Search] {query or ', '.join(items)}")

    logger.info(f"Query: {query!r}  Mode: {mode}")

    try:
        if mode == "compare" and items:
            logger.info(f"Comparing: {items}")
            result = _compare(items, aspect)
            logger.info("Compare done.")
            return result

        logger.info("Trying DuckDuckGo...")
        try:
            results = _ddg_search(query)
            if results:
                logger.info(f"DDG OK: {len(results)} result(s).")
                return _format_ddg(query, results)
        except Exception as e:
            logger.info(f"DDG failed ({e}) — trying Gemini...")

        result = _gemini_search(query)
        logger.info("Gemini OK.")
        return result

    except Exception as e:
        logger.exception("Operation failed")
        return f"Search failed, sir: {e}"