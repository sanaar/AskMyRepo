"""Answer a question about a repo using retrieved chunks + Groq's Llama 3.1."""
import os

from groq import Groq

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about a GitHub repository "
    "using only the provided code/doc excerpts. If the excerpts don't contain the "
    "answer, say so instead of guessing. Reference specific file paths when relevant."
)


def _client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set (add it to Streamlit secrets or the environment).")
    return Groq(api_key=api_key)


def answer_question(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(f"[{c['path']}]\n{c['text']}" for c in chunks)
    user_prompt = f"Context from the repo:\n\n{context}\n\nQuestion: {question}"

    response = _client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
