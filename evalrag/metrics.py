"""Evaluation metrics. All scores are between 0 and 1 (higher is better).

These are lightweight, deterministic versions of the RAGAS-style metrics,
so they run free and offline inside CI:
  context_precision  - share of retrieved chunks that come from the correct source document
  context_recall     - share of the reference answer's key words found in the retrieved context
  faithfulness       - share of the answer's key words supported by the retrieved context
                       (low faithfulness = likely hallucination)
  answer_relevance   - TF-IDF cosine similarity between the question and the answer
  answer_correctness - token F1 between the answer and the reference answer
"""
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in ENGLISH_STOP_WORDS]


def _coverage(part, whole):
    part_toks = set(tokens(part))
    if not part_toks:
        return 0.0
    return len(part_toks & set(tokens(whole))) / len(part_toks)


def context_precision(contexts, source):
    return sum(c["source"] == source for c in contexts) / len(contexts) if contexts else 0.0


def context_recall(contexts, reference):
    return _coverage(reference, " ".join(c["text"] for c in contexts))


def faithfulness(answer, contexts):
    return _coverage(answer, " ".join(c["text"] for c in contexts))


def answer_relevance(question, answer):
    try:
        vec = TfidfVectorizer(stop_words="english").fit([question, answer])
    except ValueError:  # empty vocabulary
        return 0.0
    return float(cosine_similarity(vec.transform([question]), vec.transform([answer]))[0][0])


def answer_correctness(answer, reference):
    a, r = tokens(answer), tokens(reference)
    common = sum(min(a.count(t), r.count(t)) for t in set(a))
    if not a or not r or common == 0:
        return 0.0
    p, rc = common / len(a), common / len(r)
    return 2 * p * rc / (p + rc)


METRIC_NAMES = ["context_precision", "context_recall", "faithfulness",
                "answer_relevance", "answer_correctness"]


def score_case(case, answer, contexts):
    return {
        "context_precision": context_precision(contexts, case["source"]),
        "context_recall": context_recall(contexts, case["reference"]),
        "faithfulness": faithfulness(answer, contexts),
        "answer_relevance": answer_relevance(case["question"], answer),
        "answer_correctness": answer_correctness(answer, case["reference"]),
    }
