
Smart Study Planner — Fixed RAG + Pro UI

This version fixes the common Streamlit Cloud import problem caused by heavy RAG dependencies being imported before the app can start.


Features


Colorful professional Streamlit UI

PDF study-material upload

RAG + FAISS semantic search

AI-generated 3/7/14/30/custom day study plans

Goal selection: Learn, Exam preparation, Revision, Exam + Revision

Daily study-hour limit

Groq openai/gpt-oss-120b

AI Study Coach

Manual tasks

Progress tracking


Deploy on Streamlit Cloud


Replace the files in your existing GitHub repository with the files in this ZIP.

Keep the Streamlit app connected to the same repository.

Make sure requirements.txt is in the repository root.

Commit and push the changes.

Streamlit Cloud should automatically rebuild the existing app.


Groq API key

Enter your Groq API key in the app sidebar. Never commit the API key to GitHub.


Important

The RAG module now loads faiss, sentence-transformers, numpy, and pypdf when RAG is actually used. This prevents a dependency import failure from crashing the entire application at startup.


If PDF processing fails, the app will show the dependency error instead of only displaying Streamlit's generic redacted error.

