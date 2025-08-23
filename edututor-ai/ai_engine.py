from typing import List, Tuple, Dict, Any
import random
import re

try:
    from transformers import pipeline  # type: ignore
except Exception:  # pragma: no cover - optional dependency in demo
    pipeline = None  # type: ignore


_llm = None

def _get_llm_pipeline():
    global _llm
    if _llm is not None:
        return _llm
    if pipeline is None:
        return None
    try:
        _llm = pipeline("text-generation", model="distilgpt2")
    except Exception:
        _llm = None
    return _llm


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def generate_study_notes(topic: str, subject: str, difficulty: str, use_llm: bool = False) -> str:
    topic = topic.strip()
    header = f"Subject: {subject} | Difficulty: {difficulty}\nTopic: {topic}\n\n"

    if use_llm:
        llm = _get_llm_pipeline()
        if llm is not None:
            try:
                prompt = (
                    f"Create concise study notes for {subject} on '{topic}'. "
                    f"Target level: {difficulty}. Use bullet points and short explanations."
                )
                out = llm(prompt, max_new_tokens=250, do_sample=True, temperature=0.7)
                text = out[0]["generated_text"][len(prompt):]
                return header + _clean_text(text)
            except Exception:
                pass

    # Fallback heuristic notes
    points = [
        f"Core concept overview of '{topic}'.",
        f"Key formulas/definitions relevant to {subject}.",
        "Common pitfalls and misconceptions.",
        f"Examples ranging from {difficulty.lower()} to challenging.",
        "Mini checklist for quick revision.",
    ]
    bullets = "\n".join([f"- {p}" for p in points])
    return header + bullets


def generate_flashcards(topic: str, subject: str, difficulty: str, num_cards: int = 5, use_llm: bool = False) -> List[Tuple[str, str]]:
    base_cards = [
        (f"Define the main idea of {topic} in {subject}.", f"The main idea is ... (level {difficulty})."),
        (f"Give an example related to {topic}.", f"An example is ... relevant to {subject}."),
        (f"State a common misconception about {topic}.", f"A misconception is ... and the correction is ..."),
        (f"Provide a key formula/theorem for {topic}.", f"One key formula/theorem is ..."),
        (f"Explain how to apply {topic} in practice.", f"Apply it by ..."),
    ]

    cards = base_cards * ((num_cards + len(base_cards) - 1) // len(base_cards))
    cards = cards[:num_cards]

    if use_llm:
        llm = _get_llm_pipeline()
        if llm is not None:
            try:
                prompt = (
                    f"Create {num_cards} flashcards as Q&A for {subject} on '{topic}', "
                    f"level {difficulty}. Format as 'Q: ... | A: ...' per line."
                )
                out = llm(prompt, max_new_tokens=300, do_sample=True, temperature=0.7)
                text = out[0]["generated_text"][len(prompt):]
                pairs = []
                for line in text.splitlines():
                    if "|" in line:
                        qpart, apart = line.split("|", 1)
                        q = qpart.split(":", 1)[-1].strip()
                        a = apart.split(":", 1)[-1].strip()
                        if q and a:
                            pairs.append((q, a))
                if len(pairs) >= 1:
                    return pairs[:num_cards]
            except Exception:
                pass

    return cards


def _generate_mcq(topic: str, subject: str, difficulty: str, n: int) -> List[Dict[str, Any]]:
    questions = []
    for i in range(n):
        correct = random.choice(["A", "B", "C", "D"])
        stem = f"{subject}: On '{topic}', which option is correct? (Level: {difficulty})"
        options = [
            f"Option A related to {topic}",
            f"Option B about {subject}",
            f"Option C factual detail",
            f"Option D common misconception",
        ]
        questions.append({
            "type": "mcq",
            "question": stem,
            "options": options,
            "answer": options[ord(correct) - ord('A')],
            "explanation": f"The correct answer is {correct} due to core concept alignment.",
            "topic_tag": topic,
        })
    return questions


def _generate_short(topic: str, subject: str, difficulty: str, n: int) -> List[Dict[str, Any]]:
    questions = []
    starters = [
        "Explain the concept of",
        "Give a short definition of",
        "List two key points about",
        "Describe a real-world application of",
    ]
    for i in range(n):
        q = f"{random.choice(starters)} {topic} in {subject}. (Level: {difficulty})"
        ideal = f"An ideal answer should mention the core definition, one example, and a {difficulty.lower()} nuance."
        questions.append({
            "type": "short",
            "question": q,
            "ideal_answer": ideal,
            "keywords": [kw.strip() for kw in topic.split() if len(kw) > 3][:4],
            "topic_tag": topic,
        })
    return questions


def generate_quiz_items(topic: str, subject: str, difficulty: str, num_mcq: int, num_short: int, use_llm: bool = False) -> List[Dict[str, Any]]:
    mcqs = _generate_mcq(topic, subject, difficulty, num_mcq)
    shorts = _generate_short(topic, subject, difficulty, num_short)
    return mcqs + shorts


def grade_quiz_submission(items: List[Dict[str, Any]], answers: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    total = len(items)
    feedback_list: List[str] = []
    weak_areas: List[str] = []

    for idx, item in enumerate(items):
        ans_key = f"q_{idx}"
        user_ans = str(answers.get(ans_key, "")).strip()

        if item["type"] == "mcq":
            correct = item["answer"].strip()
            if user_ans == correct:
                score += 1
                feedback_list.append(f"Q{idx+1}: Correct.")
            else:
                feedback_list.append(f"Q{idx+1}: Incorrect. {item['explanation']}")
                weak_areas.append(item.get("topic_tag", ""))
        else:
            ideal = item.get("ideal_answer", "")
            keywords = item.get("keywords", [])
            user_tokens = set(re.findall(r"[A-Za-z0-9]+", user_ans.lower()))
            keyword_hits = sum(1 for kw in keywords if kw.lower() in user_tokens)
            if keyword_hits >= max(1, len(keywords) // 2):
                score += 1
                feedback_list.append(f"Q{idx+1}: Good. Covered key points.")
            else:
                miss = [kw for kw in keywords if kw.lower() not in user_tokens]
                feedback_list.append(f"Q{idx+1}: Needs improvement. Mention: {', '.join(miss) if miss else 'more specifics'}.")
                weak_areas.extend(miss or [item.get("topic_tag", "")])

    return {
        "score": score,
        "total": total,
        "feedback_list": feedback_list,
        "weak_areas": [w for w in weak_areas if w],
    }