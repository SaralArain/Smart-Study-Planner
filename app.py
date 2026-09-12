import streamlit as st
from datetime import date
from planner import add_task, generate_schedule, priority_label, days_left_text
try:
    from rag import build_index, search_rag, get_context_for_plan
    RAG_IMPORT_ERROR = None
except Exception as e:
    RAG_IMPORT_ERROR = str(e)

    def _rag_unavailable(*args, **kwargs):
        raise RuntimeError(
            "RAG is unavailable. Check the RAG dependencies in requirements.txt. "
            f"Details: {RAG_IMPORT_ERROR}"
        )

    build_index = search_rag = get_context_for_plan = _rag_unavailable
from ai import parse_tasks_with_llm, ask_study_coach, generate_pdf_study_plan

st.set_page_config(page_title="Smart Study Planner", page_icon="🎓", layout="wide")

if RAG_IMPORT_ERROR:
    st.warning(
        "⚠️ RAG module could not be loaded. "
        "You can still open the app, but PDF/RAG features need the dependencies. "
        f"Details: {RAG_IMPORT_ERROR}"
    )

defaults = {
    "tasks": [], "study_log": [], "streak": 0, "last_log_date": None,
    "chat_history": [], "api_key": "", "rag_chunks": [],
    "pdf_name": "", "ai_plan": None, "plan_goal": "", "plan_days": 0,
    "plan_daily_hours": 0
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown(""" <style> .stApp { background: linear-gradient(135deg,#07111f 0%,#111827 45%,#312e81 100%); } .block-container {max-width: 1200px; padding-top: 2rem;} .hero { padding: 28px; border-radius: 24px; margin-bottom: 22px; background: linear-gradient(135deg,rgba(59,130,246,.28),rgba(168,85,247,.28)); border: 1px solid rgba(255,255,255,.15); } .hero h1 {font-size: 42px; margin-bottom: 5px;} .metric { padding: 18px; border-radius: 18px; text-align:center; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12); } .metric .num {font-size: 28px; font-weight: 700;} .task { padding: 14px 17px; border-radius: 14px; margin: 9px 0; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.10); border-left: 5px solid #60a5fa; } .plan-card { padding: 20px; border-radius: 18px; margin: 12px 0; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); } .small {opacity:.75; font-size:14px;} </style> """, unsafe_allow_html=True)

with st.sidebar:
    st.title("🎓 Smart Study Planner")
    st.caption("AI • RAG • FAISS • Groq")
    st.session_state.api_key = st.text_input(
        "Groq API key", type="password", value=st.session_state.api_key
    )
    st.divider()
    done = sum(t["done"] for t in st.session_state.tasks)
    total = len(st.session_state.tasks)
    st.write(f"🔥 **{st.session_state.streak} day** streak")
    st.progress(done / total if total else 0, text=f"{done}/{total} manual tasks complete")
    if st.session_state.pdf_name:
        st.success("📄 Material loaded")
        st.caption(st.session_state.pdf_name)
    if st.session_state.ai_plan:
        st.success("✨ AI plan active")

st.markdown(""" <div class="hero"> <h1>🎓 Smart Study Planner</h1> <p>Upload your study material, choose your time, and let AI build your personalized study plan.</p> </div> """, unsafe_allow_html=True)

tabs = st.tabs(["🏠 Dashboard", "✨ Create Plan", "🗓️ My Plan", "📚 Material", "➕ Tasks", "🤖 AI Coach"])

# Dashboard
with tabs[0]:
    st.subheader("Your study dashboard")
    completed_plan = 0
    total_plan = 0

    # Count AI plan tasks
    if st.session_state.ai_plan:
        for d in st.session_state.ai_plan.get("days", []):
            for i, _ in enumerate(d.get("tasks", [])):
                total_plan += 1
                if st.session_state.get(f"myplan_done_{d.get('day')}_{i}", False):
                    completed_plan += 1

    # Count manual tasks
    total_plan += len(st.session_state.tasks)
    completed_plan += sum(
        1 for t in st.session_state.tasks if t.get("done", False)
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric"><div class="num">📚 {total_plan}</div><div>Plan tasks</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric"><div class="num">✅ {completed_plan}</div><div>Completed</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric"><div class="num">🔥 {st.session_state.streak}</div><div>Streak</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric"><div class="num">📄 {"Yes" if st.session_state.pdf_name else "No"}</div><div>Study material</div></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("🎯 Today's focus")
    if st.session_state.ai_plan:
        entry = next(
            (d for d in st.session_state.ai_plan.get("days", [])
             if d.get("date") == date.today().isoformat()), None
        )
        if entry:
            st.info(f"Today's focus: **{entry.get('focus', 'Study session')}**")
            for task in entry.get("tasks", []):
                st.write(
                    f"📚 **{task.get('topic','')}** — "
                    f"{task.get('activity','')} "
                    f"({task.get('hours',0):g}h)"
                )
        else:
            st.success("Your plan is ready. Open My Plan to continue.")
    elif st.session_state.tasks:
        hours = st.slider("Available study hours today", 1, 12, 3, key="dash_hours")
        plan = generate_schedule(st.session_state.tasks, hours, 1)
        for s, n, h, p in plan.get(date.today(), []):
            st.markdown(f'<div class="task"><b>{s}: {n}</b> — {h:g}h</div>', unsafe_allow_html=True)
    else:
        st.info("Start by uploading a PDF in **✨ Create Plan**.")

# Create Plan
with tabs[1]:
    st.subheader("✨ Create your personalized plan")
    st.write("Turn lecture notes, chapters, or exam material into a day-by-day plan.")

    pdf = st.file_uploader("📄 Upload your study PDF", type=["pdf"], key="create_pdf")

    c1, c2 = st.columns(2)
    with c1:
        goal = st.selectbox(
            "🎯 Your goal",
            ["Learn the material", "Exam preparation", "Revision", "Exam + Revision"]
        )
    with c2:
        duration = st.selectbox(
            "📅 Plan duration",
            ["3 Days", "7 Days", "14 Days", "1 Month", "Custom"]
        )

    if duration == "Custom":
        days = st.number_input("Number of days", min_value=1, max_value=365, value=10)
    elif duration == "1 Month":
        days = 30
    else:
        days = int(duration.split()[0])

    daily_hours = st.slider("⏰ Available study time per day", 1, 12, 2)

    if pdf:
        st.info(f"Selected: **{pdf.name}**")
        if st.button("🔎 Read & Prepare PDF", type="secondary"):
            try:
                with st.spinner("Reading your PDF and building the study knowledge base..."):
                    chunks = build_index(pdf)
                st.session_state.rag_chunks = chunks
                st.session_state.pdf_name = pdf.name
                st.session_state.ai_plan = None
                st.success(f"✅ Ready! {len(chunks)} study sections indexed.")
            except Exception as e:
                st.error(f"Could not process PDF: {e}")

    if st.session_state.rag_chunks:
        st.divider()
        st.markdown(
            f"**Plan settings:** {int(days)} days · {daily_hours} hours/day · {goal}"
        )
        if st.button("🚀 Generate My AI Study Plan", type="primary"):
            if not st.session_state.api_key:
                st.warning("Enter your Groq API key in the sidebar first.")
            else:
                context = get_context_for_plan(st.session_state.rag_chunks, 12)
                with st.spinner("GPT-OSS-120B is designing your plan..."):
                    plan, error = generate_pdf_study_plan(
                        context, int(days), float(daily_hours), goal,
                        st.session_state.api_key
                    )
                if error:
                    st.error(error)
                else:
                    st.session_state.ai_plan = plan
                    st.session_state.plan_goal = goal
                    st.session_state.plan_days = int(days)
                    st.session_state.plan_daily_hours = float(daily_hours)
                    st.success("🎉 Your personalized plan is ready!")
                    st.rerun()

# My Plan
with tabs[2]:
    st.subheader("🗓️ My AI Study Plan")
    if not st.session_state.ai_plan:
        st.info("Create a plan from your PDF first.")
    else:
        p = st.session_state.ai_plan
        st.markdown(f"## {p.get('title', 'Study Plan')}")
        st.write(p.get("summary", ""))
        st.caption(
            f"🎯 {st.session_state.plan_goal} • "
            f"📅 {st.session_state.plan_days} days • "
            f"⏰ {st.session_state.plan_daily_hours:g} hours/day"
        )
        for d in p.get("days", []):
            day_num = d.get("day")
            tasks = d.get("tasks", [])
            with st.expander(
                f"📅 Day {day_num} — {d.get('date')} · {d.get('total_hours',0):g}h",
                expanded=(day_num == 1)
            ):
                st.write(f"**Focus:** {d.get('focus','')}")
                for i, t in enumerate(tasks):
                    st.checkbox(
                        f"**{t.get('topic','')}** — {t.get('activity','')} "
                        f"({t.get('hours',0):g}h)",
                        key=f"myplan_done_{day_num}_{i}"
                    )

# Material
with tabs[3]:
    st.subheader("📚 Study Material")
    if not st.session_state.rag_chunks:
        st.info("Upload and process a PDF in **✨ Create Plan**.")
    else:
        st.success(f"📖 {st.session_state.pdf_name} is ready for RAG search.")
        q = st.text_input("🔍 Search your material", placeholder="What are the most important topics?")
        if st.button("Search PDF") and q.strip():
            results = search_rag(q, st.session_state.rag_chunks, 5)
            for r in results:
                st.info(r)

# Manual Tasks
with tabs[4]:
    st.subheader("➕ Manual Tasks")
    c1, c2 = st.columns(2)
    with c1:
        subject = st.text_input("Subject", placeholder="Mathematics")
        name = st.text_input("Task name", placeholder="Chapter 5")
    with c2:
        deadline = st.date_input("Deadline", min_value=date.today())
        priority = st.slider("Priority", 1, 5, 3)
        hours = st.number_input("Hours needed", 1.0, 50.0, 4.0)

    if st.button("➕ Add Task", type="primary"):
        if subject.strip() and name.strip():
            add_task(st.session_state.tasks, subject.strip(), name.strip(), deadline, priority, hours)
            st.success("Task added!")
            st.rerun()
        else:
            st.warning("Enter both subject and task name.")

    for i, t in enumerate(st.session_state.tasks):
        progress = int(100 * t["hours_done"] / t["hours_needed"]) if t["hours_needed"] else 0
        st.markdown(
            f'<div class="task"><b>{t["subject"]}: {t["name"]}</b><br>'
            f'{days_left_text(t["deadline"])} · Priority {t["priority"]} · {progress}% complete</div>',
            unsafe_allow_html=True
        )
        a, b = st.columns(2)
        with a:
            if not t["done"] and st.button("✅ Mark done", key=f"done{i}"):
                t["done"] = True
                t["hours_done"] = t["hours_needed"]
                st.rerun()
        with b:
            if st.button("🗑️ Delete", key=f"delete{i}"):
                st.session_state.tasks.pop(i)
                st.rerun()

# AI Coach
with tabs[5]:
    st.subheader("🤖 AI Study Coach")
    st.caption("Ask questions, get explanations, make quizzes, or adjust your study plan.")

    if not st.session_state.api_key:
        st.warning("Enter your Groq API key in the sidebar.")
    else:
        st.markdown("### ⚡ Quick actions")
        q1, q2, q3, q4 = st.columns(4)
        quick = None
        with q1:
            if st.button("📅 What today?"): quick = "What should I study today?"
        with q2:
            if st.button("🧠 Explain"): quick = "Explain the most important topic from my material like a beginner."
        with q3:
            if st.button("📝 Quiz me"): quick = "Quiz me with 5 questions based on my uploaded study material. Ask one at a time."
        with q4:
            if st.button("🎯 Exam tips"): quick = "What are the most important topics I should revise for an exam?"

        st.divider()
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]):
                st.write(m["content"])

        message = st.chat_input("Ask your AI coach anything about your study...")
        message = message or quick

        if message:
            st.session_state.chat_history.append({"role": "user", "content": message})
            rag_context = ""
            if st.session_state.rag_chunks:
                rag_context = "\n\n".join(search_rag(message, st.session_state.rag_chunks, 6))

            plan_context = ""
            if st.session_state.ai_plan:
                plan_context = str(st.session_state.ai_plan)

            with st.spinner("AI Coach is thinking..."):
                reply = ask_study_coach(
                    message, st.session_state.api_key,
                    st.session_state.tasks, rag_context, plan_context
                )
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()
