import json
from datetime import date
from groq import Groq

MODEL = "openai/gpt-oss-120b"


def _client(api_key):
    return Groq(api_key=api_key)


def _json(raw):
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "", 1).strip()
    return json.loads(cleaned)


def parse_tasks_with_llm(text, api_key):
    prompt = f"""Today's date is {date.today().isoformat()}. Student message: {text} Return ONLY valid JSON: [{{"subject":"string","name":"string","deadline":"YYYY-MM-DD","priority":1,"hours_needed":2}}] Priority: 5 = exam/major grade 3 = normal 1 = minor"""

    try:
        r = _client(api_key).chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return _json(r.choices[0].message.content), None
    except Exception as e:
        return None, f"AI error: {e}"


def generate_pdf_study_plan(pdf_context, days, daily_hours, goal, api_key):
    prompt = f"""You are an expert personal study planner. Create a realistic plan from the uploaded study material. Goal: {goal} Duration: {days} days Daily study time: {daily_hours} hours Rules: - Use only topics supported by the uploaded material. - Prioritize important and foundational topics. - Break large topics into manageable study sessions. - Include review/practice sessions near the end. - Never schedule more than the daily study-hour limit. - Make activities specific and beginner-friendly. - Return ONLY valid JSON. Format: {{ "title":"string", "summary":"string", "days":[ {{ "day":1, "date":"YYYY-MM-DD", "focus":"string", "tasks":[ {{"topic":"string","activity":"string","hours":1.0}} ], "total_hours":1.0 }} ] }} Uploaded study material: {pdf_context}"""

    try:
        r = _client(api_key).chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return _json(r.choices[0].message.content), None
    except Exception as e:
        return None, f"AI plan error: {e}"


def ask_study_coach(message, api_key, tasks, rag_context="", plan_context=""):
    task_text = "\n".join(
        f"- {t['subject']}: {t['name']}, due {t['deadline']}, priority {t['priority']}"
        for t in tasks
    ) or "No manual tasks yet."

    system = f"""You are Smart Study Coach, a friendly and practical AI tutor. Your job: 1. Help the student understand their uploaded study material. 2. Help them follow and adjust their study plan. 3. Explain difficult topics simply when asked. 4. Create quizzes and practice questions when asked. 5. Recommend what to study next using the available plan/material. 6. If the student falls behind, suggest a realistic recovery plan. 7. Be concise, encouraging and beginner-friendly. 8. When answering questions about uploaded material, rely on the supplied material. 9. Say when the supplied material does not contain the answer. 10. Do not pretend a topic is in the PDF if it is not in the supplied context. Manual tasks: {task_text} Current AI study plan: {plan_context} Relevant uploaded material: {rag_context} """

    try:
        r = _client(api_key).chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {e}"
