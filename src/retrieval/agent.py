from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


def build_agent(settings: Settings, index: LocalEmbeddingIndex):
    @tool
    def semantic_search_papers(query: str, top_k: int = 4) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        results = index.search(query, top_k=top_k)
        lines = []
        for result in results:
            lines.append(
                f"paper_id: {result.paper_id}\n"
                f"title: {result.title}\n"
                f"score: {result.score:.4f}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or exact title from the local corpus."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return (
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"{record['content']}"
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=(
            "You answer questions about the indexed scholarly paper corpus sourced from Crossref. "
            "Use tools before answering factual questions. "
            "If the indexed corpus does not support the answer, say so clearly."
        ),
        name="paper_corpus_agent",
    )


def run_agent_question(agent: Any, question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    return getattr(final_message, "content", str(final_message))


if __name__ == "__main__":
    import sys

    import pandas as pd

    from core.config import load_settings
    from retrieval.index import LocalEmbeddingIndex
    from retrieval.qa import answer_question

    if hasattr(sys.stdout, "reconfigure"):
        # Paper titles/authors from Crossref often contain characters outside the
        # Windows console's default cp1252 codepage; force UTF-8 so printing never crashes.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=== [ROLE 4B] SMOKE TEST: LLM PROVIDER, AGENT & QA ===")
    settings = load_settings()

    if not settings.paths.clean_csv.exists():
        print(
            f"[WARNING] Clean data not found at {settings.paths.clean_csv}. "
            "Ask the cleaning.py owner (Role 3) to run build_clean_dataframe first, "
            "or run 'python script/run_phase1.py' once Role 1/2/3 are done."
        )
        raise SystemExit(0)

    df = pd.read_csv(settings.paths.clean_csv)
    print(f"--> Building Chroma collection '{settings.baseline_collection_name}' from {len(df)} rows...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)

    print("\n--> Test 1: Semantic search (the 'semantic_search_papers' tool)...")
    for result in index.search("retrieval augmented generation", top_k=2):
        print(f"  [Hit] paper_id={result.paper_id} | score={result.score:.4f} | title={result.title}")

    print("\n--> Test 2: Exact lookup (the 'lookup_paper' tool)...")
    sample_title = df.iloc[0]["title"]
    record = index.lookup(sample_title)
    print(f"  [Lookup] '{sample_title}' -> {'FOUND' if record else 'NOT FOUND'}")

    print("\n--> Test 3: Deterministic QA (qa.answer_question, used by evaluation/metrics.py)...")
    qa_result = answer_question(f"Who authored the paper '{sample_title}'?", settings, index)
    print(f"  [QA Answer] {qa_result.answer}")
    print(f"  [QA Sources] {qa_result.retrieved_doc_ids}")

    print("\n--> Test 4: RAG agent tool-calling (build_agent + run_agent_question)...")
    try:
        agent = build_agent(settings, index)
        answer = run_agent_question(agent, "Summarize the paper related to retrieval augmented generation.")
        print(f"  [Agent Answer]\n{answer}")
    except Exception as exc:
        print(f"[TEST FAILED] Agent could not run (check LLM_PROVIDER/API key in .env): {exc}")
