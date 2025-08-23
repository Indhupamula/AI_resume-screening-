# EduTutor AI – Personalized Learning and Assessment System

Built for InnovateX: IBM Hackathon 2025 – Driving Digital Innovation with IBM.

## Project Description
Traditional classrooms often follow a one-size-fits-all approach. EduTutor AI delivers personalized learning paths, automated assessments, instant feedback, and data-driven insights to improve student engagement and reduce teacher workload. The system adapts difficulty in real-time and offers targeted recommendations.

## Features
- Authentication with demo login/signup (email/password stored in JSON)
- Role-based dashboards for Students and Teachers/Parents
- Student tools: topic-based study notes, flashcards, and adaptive quizzes (MCQ + short answer)
- AI-powered content generation (optional Hugging Face LLM fallback)
- Automated grading with instant feedback
- Analytics dashboard with progress trends and weak area highlights
- Export PDF reports (FPDF)

## Tech Stack
- Python, Streamlit (UI)
- AI: Hugging Face Transformers / LangChain-ready
- Data: Pandas, NumPy
- Visualization: Plotly/Matplotlib
- PDF: FPDF

## Repository Structure
```
/edututor-ai
├── app.py                # Streamlit frontend (UI)
├── ai_engine.py          # Backend AI content generation + assessments
├── utils.py              # Helpers (auth, data, analytics, PDF)
├── student_data.csv      # Demo dataset (app will create if missing)
├── users.json            # Demo users (auto-created)
├── requirements.txt      # Dependencies
└── README.md             # Setup + usage
```

## Run Locally
1. Clone this repository or copy the folder.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Launch the app:
```bash
streamlit run app.py
```
4. Open the URL shown in the terminal (usually `http://localhost:8501`).

### Demo Accounts
- Student: `student@example.com` / `student123`
- Teacher: `teacher@example.com` / `teacher123`

## Notes
- For the hackathon demo, the LLM integration is optional. Toggle "Use LLM" in the sidebar to attempt Hugging Face generation (uses `distilgpt2`). If models can't be downloaded in your environment, the app falls back to structured heuristics.
- PDF export embeds a Matplotlib trend chart and summary stats.