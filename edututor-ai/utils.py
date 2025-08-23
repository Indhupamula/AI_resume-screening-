import os
import io
import json
import uuid
import tempfile
from typing import Dict, Any, Tuple
from datetime import datetime

import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt

BASE_DIR = "/workspace/edututor-ai"
USERS_PATH = os.path.join(BASE_DIR, "users.json")
DATA_PATH = os.path.join(BASE_DIR, "student_data.csv")


DEMO_USERS = [
    {"email": "student@example.com", "password": "student123", "role": "student", "name": "Student Demo"},
    {"email": "teacher@example.com", "password": "teacher123", "role": "teacher", "name": "Teacher Demo"},
]


def ensure_demo_files_exist() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEMO_USERS, f, indent=2)
    if not os.path.exists(DATA_PATH):
        # Create with headers
        df = pd.DataFrame(columns=[
            "email", "student_name", "subject", "topic", "difficulty", "quiz_type", "score", "total", "timestamp", "weak_areas", "feedback_summary"
        ])
        df.to_csv(DATA_PATH, index=False)


def _load_users() -> list:
    if not os.path.exists(USERS_PATH):
        return []
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_users(users: list) -> None:
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def register_user(name: str, email: str, password: str, role: str) -> Tuple[bool, str]:
    email = (email or "").strip().lower()
    password = (password or "").strip()
    name = (name or "").strip()
    if not email or not password or role not in {"student", "teacher"}:
        return False, "Please provide name, email, password, and valid role."
    users = _load_users()
    if any(u.get("email") == email for u in users):
        return False, "Email already registered."
    users.append({"email": email, "password": password, "role": role, "name": name})
    _save_users(users)
    return True, "Registered"


def authenticate_user(email: str, password: str) -> Dict[str, Any] | None:
    email = (email or "").strip().lower()
    password = (password or "").strip()
    for u in _load_users():
        if u.get("email") == email and u.get("password") == password:
            return u
    return None


def load_student_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        ensure_demo_files_exist()
    try:
        return pd.read_csv(DATA_PATH)
    except Exception:
        return pd.DataFrame(columns=[
            "email", "student_name", "subject", "topic", "difficulty", "quiz_type", "score", "total", "timestamp", "weak_areas", "feedback_summary"
        ])


def save_student_result(
    email: str,
    student_name: str,
    subject: str,
    topic: str,
    difficulty: str,
    quiz_type: str,
    score: int,
    total: int,
    weak_areas: str,
    feedback_summary: str,
) -> None:
    ensure_demo_files_exist()
    timestamp = datetime.utcnow().isoformat()
    row = {
        "email": email,
        "student_name": student_name,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "quiz_type": quiz_type,
        "score": score,
        "total": total,
        "timestamp": timestamp,
        "weak_areas": weak_areas,
        "feedback_summary": feedback_summary,
    }
    df = load_student_data()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(DATA_PATH, index=False)


class _PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "EduTutor AI – Progress Report", border=0, ln=1, align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", size=8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


def _matplotlib_summary_plot(df: pd.DataFrame, student_name: str) -> str:
    # Returns path to temp PNG
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig, ax = plt.subplots(figsize=(6, 3))
        if not df.empty:
            # Compute percentage scores over time
            df_plot = df.copy()
            df_plot["pct"] = (df_plot["score"] / df_plot["total"]) * 100
            df_plot = df_plot.sort_values("timestamp")
            ax.plot(df_plot["timestamp"], df_plot["pct"], marker="o")
            ax.set_title(f"Performance Over Time – {student_name}")
            ax.set_xlabel("Attempt")
            ax.set_ylabel("Score (%)")
            ax.grid(True, alpha=0.3)
            ax.set_xticks(range(len(df_plot["timestamp"])));
            ax.set_xticklabels(range(1, len(df_plot["timestamp"]) + 1))
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
        fig.tight_layout()
        fig.savefig(tmp.name, dpi=150)
        plt.close(fig)
        return tmp.name


def export_pdf_report(df: pd.DataFrame, student_name: str) -> bytes:
    pdf = _PDF()
    pdf.add_page()

    # Summary stats
    pdf.set_font("Arial", size=11)
    total_attempts = len(df)
    avg = ((df["score"].sum() / df["total"].sum()) * 100) if df["total"].sum() else 0
    pdf.multi_cell(0, 8, txt=(
        f"Student: {student_name}\n"
        f"Attempts: {total_attempts}\n"
        f"Average Score: {avg:.1f}%\n"
    ))

    # Top subjects and weak areas
    if not df.empty:
        by_subject = (
            df.groupby("subject").apply(lambda g: (g["score"].sum() / g["total"].sum()) * 100 if g["total"].sum() else 0)
            .sort_values(ascending=False)
        )
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Performance by Subject", ln=1)
        pdf.set_font("Arial", size=10)
        for subj, pct in by_subject.items():
            pdf.cell(0, 6, f"- {subj}: {pct:.1f}%", ln=1)

        weak_map = df.dropna(subset=["weak_areas"]).copy()
        if not weak_map.empty:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Common Weak Areas", ln=1)
            pdf.set_font("Arial", size=10)
            counts: Dict[str, int] = {}
            for areas in weak_map["weak_areas"].astype(str).tolist():
                for t in [a.strip() for a in areas.split(",") if a.strip()]:
                    counts[t] = counts.get(t, 0) + 1
            for topic, c in sorted(counts.items(), key=lambda x: -x[1])[:6]:
                pdf.cell(0, 6, f"- {topic} ({c})", ln=1)

    # Add chart image
    img_path = _matplotlib_summary_plot(df, student_name)
    try:
        pdf.image(img_path, w=180)
    except Exception:
        pass
    try:
        os.remove(img_path)
    except Exception:
        pass

    return bytes(pdf.output(dest='S').encode('latin1'))