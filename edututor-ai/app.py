import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
from typing import Dict, Any, List, Tuple

from utils import (
    ensure_demo_files_exist,
    authenticate_user,
    register_user,
    load_student_data,
    save_student_result,
    export_pdf_report,
)
from ai_engine import (
    generate_study_notes,
    generate_flashcards,
    generate_quiz_items,
    grade_quiz_submission,
)


APP_TITLE = "EduTutor AI – Personalized Learning and Assessment"
SUBJECT_OPTIONS = ["Mathematics", "Science", "Computer Science", "History", "Geography", "English"]
DIFFICULTY_OPTIONS = ["Easy", "Medium", "Hard"]


def init_session_state() -> None:
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "quiz_items" not in st.session_state:
        st.session_state.quiz_items = []
    if "use_llm" not in st.session_state:
        st.session_state.use_llm = False


def login_ui() -> None:
    st.header("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", type="primary"):
        user = authenticate_user(email=email.strip().lower(), password=password)
        if user:
            st.session_state.auth_user = user
            st.success(f"Welcome, {user.get('name') or user['email']}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials. Please try again or sign up.")

    st.divider()
    with st.expander("New here? Create an account"):
        name = st.text_input("Name", key="signup_name")
        email_s = st.text_input("Email", key="signup_email")
        password_s = st.text_input("Password", type="password", key="signup_password")
        role = st.selectbox("Role", options=["student", "teacher"], index=0, key="signup_role")
        if st.button("Sign Up"):
            ok, msg = register_user(name=name, email=email_s, password=password_s, role=role)
            if ok:
                st.success("Account created. You can now log in.")
            else:
                st.error(msg)


def student_dashboard(user: Dict[str, Any]) -> None:
    st.header("Student Dashboard")
    st.caption(f"Logged in as {user['email']}")

    with st.sidebar:
        st.checkbox("Use LLM (Hugging Face)", value=st.session_state.use_llm, key="use_llm")

    tab_notes, tab_flash, tab_quiz, tab_progress = st.tabs([
        "Study Notes", "Flashcards", "Quiz", "Progress & Reports",
    ])

    with tab_notes:
        subject = st.selectbox("Select Subject", SUBJECT_OPTIONS, key="notes_subject")
        difficulty = st.select_slider("Difficulty", DIFFICULTY_OPTIONS, value="Medium", key="notes_difficulty")
        topic_text = st.text_area("Enter topic, paste syllabus text, or notes")
        if st.button("Generate Notes"):
            if not topic_text.strip():
                st.warning("Please provide a topic or syllabus text.")
            else:
                notes = generate_study_notes(topic=topic_text, subject=subject, difficulty=difficulty, use_llm=st.session_state.use_llm)
                st.subheader("AI-Generated Notes")
                st.write(notes)

    with tab_flash:
        subject_f = st.selectbox("Select Subject", SUBJECT_OPTIONS, key="flash_subject")
        difficulty_f = st.select_slider("Difficulty", DIFFICULTY_OPTIONS, value="Medium", key="flash_difficulty")
        topic_text_f = st.text_area("Topic for flashcards", key="flash_topic")
        num_cards = st.slider("Number of flashcards", 3, 10, 5)
        if st.button("Generate Flashcards"):
            if not topic_text_f.strip():
                st.warning("Please enter a topic for flashcards.")
            else:
                cards = generate_flashcards(topic=topic_text_f, subject=subject_f, difficulty=difficulty_f, num_cards=num_cards, use_llm=st.session_state.use_llm)
                st.subheader("Flashcards")
                for idx, (q, a) in enumerate(cards, start=1):
                    with st.expander(f"Card {idx}: {q}"):
                        st.write(f"Answer: {a}")

    with tab_quiz:
        subject_q = st.selectbox("Select Subject", SUBJECT_OPTIONS, key="quiz_subject")
        difficulty_q = st.select_slider("Difficulty", DIFFICULTY_OPTIONS, value="Medium", key="quiz_difficulty")
        topic_text_q = st.text_area("Topic for quiz", key="quiz_topic")
        num_mcq = st.slider("Number of MCQs", 1, 10, 3)
        num_short = st.slider("Number of Short Answers", 0, 10, 2)
        if st.button("Create Quiz"):
            if not topic_text_q.strip():
                st.warning("Please provide a topic for the quiz.")
            else:
                quiz_items = generate_quiz_items(topic=topic_text_q, subject=subject_q, difficulty=difficulty_q, num_mcq=num_mcq, num_short=num_short, use_llm=st.session_state.use_llm)
                st.session_state.quiz_items = quiz_items

        if st.session_state.quiz_items:
            st.subheader("Your Quiz")
            answers: Dict[str, Any] = {}
            for idx, item in enumerate(st.session_state.quiz_items):
                qid = f"q_{idx}"
                if item["type"] == "mcq":
                    st.write(f"Q{idx+1}. {item['question']}")
                    answers[qid] = st.radio("Choose one:", options=item["options"], key=f"ans_{idx}")
                else:
                    st.write(f"Q{idx+1}. {item['question']}")
                    answers[qid] = st.text_area("Your answer:", key=f"ans_{idx}")
                st.divider()

            if st.button("Submit Quiz", type="primary"):
                result = grade_quiz_submission(st.session_state.quiz_items, answers)
                st.success(f"Score: {result['score']} / {result['total']}")
                st.write("Feedback:")
                for fb in result["feedback_list"]:
                    st.write(f"- {fb}")

                save_student_result(
                    email=user["email"],
                    student_name=user.get("name") or user["email"],
                    subject=subject_q,
                    topic=topic_text_q[:100],
                    difficulty=difficulty_q,
                    quiz_type="MCQ+Short",
                    score=int(result["score"]),
                    total=int(result["total"]),
                    weak_areas=", ".join(result.get("weak_areas", [])),
                    feedback_summary="; ".join(result.get("feedback_list", []))[:500],
                )
                st.info("Result saved to progress log.")

    with tab_progress:
        df = load_student_data()
        if df.empty:
            st.info("No progress yet. Take a quiz to see analytics.")
        else:
            df_user = df[df["email"] == user["email"]].copy()
            if df_user.empty:
                st.info("No results for your account yet.")
            else:
                st.subheader("Your Recent Results")
                st.dataframe(df_user.sort_values("timestamp", ascending=False).head(20), use_container_width=True)

                avg_score = (df_user["score"].sum() / df_user["total"].sum()) * 100 if df_user["total"].sum() > 0 else 0
                st.metric("Average Score", f"{avg_score:.1f}%")

                # Download PDF report
                if st.button("Export PDF Report"):
                    pdf_bytes = export_pdf_report(df_user, student_name=user.get("name") or user["email"])
                    st.download_button("Download Report PDF", data=pdf_bytes, file_name="edututor_report.pdf", mime="application/pdf")


def teacher_dashboard(user: Dict[str, Any]) -> None:
    st.header("Teacher / Parent Dashboard")
    st.caption(f"Logged in as {user['email']}")

    df = load_student_data()
    if df.empty:
        st.info("No student results available yet.")
        return

    student_filter = st.multiselect("Filter by students", options=sorted(df["student_name"].dropna().unique().tolist()))
    subject_filter = st.multiselect("Filter by subjects", options=sorted(df["subject"].dropna().unique().tolist()))

    df_v = df.copy()
    if student_filter:
        df_v = df_v[df_v["student_name"].isin(student_filter)]
    if subject_filter:
        df_v = df_v[df_v["subject"].isin(subject_filter)]

    st.subheader("Overview")
    if df_v.empty:
        st.info("No data matches the filters.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        class_avg = (df_v["score"].sum() / df_v["total"].sum()) * 100 if df_v["total"].sum() > 0 else 0
        st.metric("Class Average", f"{class_avg:.1f}%")
    with col2:
        recent = df_v.sort_values("timestamp", ascending=False).head(1)
        st.metric("Most Recent Score", (recent["score"].iloc[0] / recent["total"].iloc[0]) * 100 if not recent.empty else 0)
    with col3:
        n_students = df_v["email"].nunique()
        st.metric("Active Students", n_students)

    st.subheader("Performance by Subject")
    pivot = df_v.groupby("subject").apply(lambda g: (g["score"].sum() / g["total"].sum()) * 100 if g["total"].sum() > 0 else np.nan).reset_index(name="avg_pct")
    st.bar_chart(pivot.set_index("subject"))

    st.subheader("Recommendations")
    weak_map = (
        df_v.dropna(subset=["weak_areas"])  # type: ignore
        .assign(weak_list=lambda d: d["weak_areas"].str.split(", "))
        .explode("weak_list")
    )
    if not weak_map.empty:
        weak_counts = weak_map["weak_list"].value_counts().head(5)
        st.write("Common weak areas:")
        for topic, count in weak_counts.items():
            st.write(f"- {topic} ({count})")

        st.write("AI Suggestions:")
        for topic in weak_counts.index.tolist():
            st.write(f"- Reinforce '{topic}' with spaced repetition and targeted practice sets.")
    else:
        st.write("No weak areas identified yet.")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    ensure_demo_files_exist()

    st.title(APP_TITLE)
    st.caption("IBM Hackathon 2025 – InnovateX Collaboration")

    if st.session_state.get("auth_user") is None:
        login_ui()
    else:
        user = st.session_state.auth_user
        with st.sidebar:
            st.write(f"Logged in as: {user['email']} ({user['role']})")
            if st.button("Logout"):
                st.session_state.auth_user = None
                st.experimental_rerun()

        if user["role"] == "student":
            student_dashboard(user)
        else:
            teacher_dashboard(user)


if __name__ == "__main__":
    init_session_state()
    main()