"""The RAG application under test: a small campus help-desk bot.

Retrieval uses TF-IDF over sentence chunks of the documents in data/kb.
Generation has two modes:
  * "extractive" (default, free, offline): answers with the retrieved
    sentences most similar to the question.
  * "claude": sends the retrieved context and the prompt template to the
    Anthropic API. Needs ANTHROPIC_API_KEY in the environment.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent.parent


def split_sentences(text):
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(lines)) if s.strip()]


def load_chunks(kb_dir, chunk_size):
    """Split every document into chunks of `chunk_size` sentences."""
    chunks = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        sents = split_sentences(path.read_text())
        for i in range(0, len(sents), chunk_size):
            chunks.append({"source": path.stem, "text": " ".join(sents[i:i + chunk_size])})
    return chunks


class RAGApp:
    def __init__(self, config):
        self.config = config
        self.chunks = load_chunks(ROOT / config.get("kb_dir", "data/kb"), config["chunk_size"])
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in self.chunks])

    def retrieve(self, question):
        scores = cosine_similarity(self.vectorizer.transform([question]), self.matrix)[0]
        top = scores.argsort()[::-1][: self.config["top_k"]]
        return [self.chunks[i] for i in top]

    def generate(self, question, contexts):
        mode = self.config.get("generator", "extractive")
        if mode == "claude":
            return self._generate_claude(question, contexts)
        sentences = [s for c in contexts for s in split_sentences(c["text"])]
        if self.config.get("answer_style") == "first_sentence":
            return sentences[0]
        vec = TfidfVectorizer(stop_words="english").fit(sentences + [question])
        sims = cosine_similarity(vec.transform([question]), vec.transform(sentences))[0]
        best = sims.argsort()[::-1][: self.config.get("max_sentences", 1)]
        return " ".join(sentences[i] for i in sorted(best))

    def _generate_claude(self, question, contexts):
        prompt = self.config["prompt_template"].format(
            context="\n".join(c["text"] for c in contexts), question=question)
        body = json.dumps({
            "model": self.config.get("model", "claude-haiku-5-5"),
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body,
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)["content"][0]["text"].strip()

    def answer(self, question):
        contexts = self.retrieve(question)
        return {"answer": self.generate(question, contexts), "contexts": contexts}
