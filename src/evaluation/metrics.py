from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
import os
import sys
import types
from typing import Any

from datasets import Dataset
from pydantic import BaseModel, Field

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


class JudgeVerdict(BaseModel):
    score: int = Field(ge=1, le=5)
    correct: bool
    reasoning: str


@dataclass(frozen=True)
class EvaluationBundle:
    summary: dict[str, Any]
    answers: list[dict[str, Any]]

    def get(self, key: str, default: Any = None) -> Any:
        """Hỗ trợ gọi .get(key, default) trực tiếp từ EvaluationBundle để tương thích với dict."""
        return self.summary.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Hỗ trợ truy cập bundle[key] tương tự dict."""
        return self.summary[key]


def evaluate_pipeline(
    settings: Settings,
    index: LocalEmbeddingIndex | None = None,
    test_set_path: Any = None,
    metrics_output_path: Any = None,
    answers_output_path: Any = None,
    *,
    df: Any = None,
    test_set: list[dict[str, Any]] | Any = None,
    embeddings_path: Any = None,
    output_metrics_path: Any = None,
    output_answers_path: Any = None,
) -> EvaluationBundle:
    # 1. Xác định Index
    if index is not None:
        actual_index = index
    elif embeddings_path is not None:
        actual_index = LocalEmbeddingIndex.load(settings, embeddings_path)
    elif df is not None:
        actual_index = LocalEmbeddingIndex.build(df, settings)
    else:
        raise ValueError("[CONSOLE TEST ERROR] Cần truyền 'index', 'embeddings_path', hoặc 'df' cho evaluate_pipeline.")

    # 2. Xác định Test Set
    if test_set is not None:
        if isinstance(test_set, list):
            actual_test_set = test_set
        elif isinstance(test_set, (str, os.PathLike)):
            actual_test_set = read_json(test_set)
        else:
            actual_test_set = test_set
    elif test_set_path is not None:
        if isinstance(test_set_path, (str, os.PathLike)):
            actual_test_set = read_json(test_set_path)
        else:
            actual_test_set = test_set_path
    else:
        raise ValueError("[CONSOLE TEST ERROR] Cần truyền 'test_set' hoặc 'test_set_path' cho evaluate_pipeline.")

    # 3. Xác định đường dẫn file đầu ra
    out_metrics_path = output_metrics_path or metrics_output_path
    out_answers_path = output_answers_path or answers_output_path

    answers: list[dict[str, Any]] = []

    for item in actual_test_set:
        result = answer_question(item["question"], settings=settings, index=actual_index)
        judge = _judge_answer(settings, item["question"], item["ground_truth"], result.answer)
        retrieval_hit = any(doc_id in item["ground_truth_doc_ids"] for doc_id in result.retrieved_doc_ids)
        answers.append(
            {
                "id": item["id"],
                "question_type": item["question_type"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "ground_truth_doc_ids": item["ground_truth_doc_ids"],
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_contexts": result.retrieved_contexts,
                "retrieval_hit": retrieval_hit,
                "token_f1": _token_f1(item["ground_truth"], result.answer),
                "judge": judge.model_dump(),
            }
        )

    summary = {
        "samples": len(answers),
        "retrieval_hit_rate": mean(1.0 if item["retrieval_hit"] else 0.0 for item in answers) if answers else 0.0,
        "mean_token_f1": mean(item["token_f1"] for item in answers) if answers else 0.0,
        "judge_accuracy": mean(1.0 if item["judge"]["correct"] else 0.0 for item in answers) if answers else 0.0,
        "mean_judge_score": mean(item["judge"]["score"] for item in answers) if answers else 0.0,
    }
    summary["ragas"] = _run_ragas(settings, answers)

    bundle = EvaluationBundle(summary=summary, answers=answers)
    if out_metrics_path:
        write_json(out_metrics_path, summary)
    if out_answers_path:
        write_json(out_answers_path, answers)
    return bundle

    ref_tokens = normalize_whitespace(reference).lower().split()
    pred_tokens = normalize_whitespace(prediction).lower().split()
    if not ref_tokens or not pred_tokens:
        return 0.0
    ref_set = set(ref_tokens)
    pred_set = set(pred_tokens)
    overlap = len(ref_set & pred_set)
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_set)
    recall = overlap / len(ref_set)
    return 2 * precision * recall / (precision + recall)


def _judge_answer(settings: Settings, question: str, reference: str, prediction: str) -> JudgeVerdict:
    prompt = f"""
Evaluate the model answer against the reference answer.

Question: {question}
Reference answer: {reference}
Model answer: {prediction}

Return:
- score from 1 to 5
- correct = true only when the answer is materially correct
- short reasoning
""".strip()
    try:
        llm = build_llm(settings=settings, temperature=0.0).with_structured_output(JudgeVerdict)
        return llm.invoke(prompt)
    except Exception:
        score = 5 if _token_f1(reference, prediction) >= 0.95 else 3 if _token_f1(reference, prediction) >= 0.5 else 1
        return JudgeVerdict(
            score=score,
            correct=score >= 3,
            reasoning="Fallback heuristic judge used because the LLM evaluator was unavailable.",
        )


def _run_ragas(settings: Settings, answers: list[dict[str, Any]]) -> dict[str, Any]:
    if os.getenv("RUN_RAGAS", "").lower() not in {"1", "true", "yes"}:
        return {"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}
    try:
        if "langchain_community.chat_models.vertexai" not in sys.modules:
            shim = types.ModuleType("langchain_community.chat_models.vertexai")
            shim.ChatVertexAI = type("ChatVertexAI", (), {})
            sys.modules["langchain_community.chat_models.vertexai"] = shim
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        dataset = Dataset.from_dict(
            {
                "question": [item["question"] for item in answers],
                "answer": [item["answer"] for item in answers],
                "ground_truth": [item["ground_truth"] for item in answers],
                "contexts": [item["retrieved_contexts"] for item in answers],
            }
        )
        result = evaluate(
            dataset,
            metrics=[answer_relevancy, context_precision, context_recall, faithfulness],
            llm=build_llm(settings=settings, temperature=0.0),
            embeddings=MiniLMEmbeddings(settings.embedding_model),
        )
        return dict(result)
    except Exception as exc:  # pragma: no cover
        return {"error": f"Ragas evaluation failed: {exc}"}



