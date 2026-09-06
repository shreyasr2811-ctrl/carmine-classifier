"""
LangChain + Claude explanation layer.

Given a model prediction (label + confidence), retrieves relevant
knowledge base passages via RAG (see rag.py) and asks Claude to produce
a short, plain-language, appropriately-cautious explanation grounded in
those passages.
"""

import os
import sys

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

sys.path.insert(0, os.path.dirname(__file__))
from rag import retrieve  # noqa: E402

SYSTEM_PROMPT = (
    "You are a medical education assistant helping a user understand the "
    "output of an experimental breast histopathology image classifier. "
    "You are NOT a doctor and must never give a diagnosis or medical "
    "advice. Use ONLY the provided reference context plus the model's "
    "prediction to write a short (roughly 120-180 words), plain-language "
    "explanation for a non-technical user. Structure your answer as: "
    "(1) what the prediction means in plain terms, (2) 1-2 sentences on "
    "relevant background from the reference context, (3) important "
    "caveats about model limitations and patch-level vs. whole-slide "
    "results, and (4) a clear recommendation to consult a qualified "
    "medical professional for actual diagnosis. Do not invent medical "
    "facts beyond the reference context."
)


def get_llm(model="claude-sonnet-4-5-20250929", temperature=0.3):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return ChatAnthropic(model=model, temperature=temperature, api_key=api_key, max_tokens=500)


def generate_explanation(label, confidence, llm=None):
    """
    label: "benign" or "malignant"
    confidence: float 0-1, the model's confidence in that label
    """
    query = (
        f"Explain a histopathology patch classification result: predicted "
        f"label={label}, confidence={confidence:.0%}. "
        f"What does this mean, what are the caveats, what should the user do next?"
    )
    context_docs = retrieve(query, k=3)
    context_block = "\n\n".join(f"- {d}" for d in context_docs)

    user_msg = (
        f"Model prediction: {label.upper()} (confidence: {confidence:.0%})\n\n"
        f"Reference context (use only this for factual claims):\n{context_block}\n\n"
        f"Write the explanation now."
    )

    llm = llm or get_llm()
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)])
    return response.content, context_docs


if __name__ == "__main__":
    text, ctx = generate_explanation("malignant", 0.87)
    print(text)
