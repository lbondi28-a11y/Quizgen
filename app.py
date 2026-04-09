import json
import re
import requests
import streamlit as st
import os

st.set_page_config(page_title="AI Quiz Generator (Groq)", layout="centered")

# -------------------------
# Security: read secrets from terminal env vars (no UI key input)
# -------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()

# Password gate (optional but recommended)
if APP_PASSWORD:
    if "authed" not in st.session_state:
        st.session_state["authed"] = False

    if not st.session_state["authed"]:
        st.title("AI Quiz Generator (Groq)")
        pw = st.text_input("App password", type="password")
        if st.button("Sign in"):
            if pw == APP_PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        st.stop()

# Require Groq key (never shown in UI)
if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY. Set it in the terminal and restart Streamlit.")
    st.code(
        'export GROQ_API_KEY="gsk_..."\nexport APP_PASSWORD="..."  # optional\nstreamlit run app.py --server.address=127.0.0.1 --server.port=8501'
    )
    st.stop()

# -------------------------
# UI
# -------------------------
st.title("AI Quiz Generator (Groq)")

# -------------------------
# State
# -------------------------
if "quiz" not in st.session_state:
    st.session_state["quiz"] = None
if "locked" not in st.session_state:
    st.session_state["locked"] = False

# -------------------------
# Start over
# -------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("Start Over / Edit Notes"):
        st.session_state["quiz"] = None
        st.session_state["locked"] = False
        for k in list(st.session_state.keys()):
            if k.startswith("answer_"):
                del st.session_state[k]
with col2:
    st.caption("Notes hide after Generate. Click Start Over to edit them again.")

# -------------------------
# Helpers: Accessible "drag-like" reorder UI (no installs)
# -------------------------
def move_item(lst: list, i: int, direction: int) -> list:
    """direction: -1 for up, +1 for down"""
    if not lst or i < 0 or i >= len(lst):
        return lst
    j = i + direction
    if j < 0 or j >= len(lst):
        return lst
    new_lst = lst[:]
    new_lst[i], new_lst[j] = new_lst[j], new_lst[i]
    return new_lst

def reorder_ui(title: str, items: list[str], state_key: str) -> list[str]:
    """
    Renders a reorder UI using Up/Down buttons.
    Returns the reordered list (also stored in st.session_state[state_key]).
    """
    if title:
        st.write(title)

    if (
        state_key not in st.session_state
        or not isinstance(st.session_state[state_key], list)
        or not st.session_state[state_key]
    ):
        st.session_state[state_key] = items[:]

    current = st.session_state[state_key]

    for idx, item in enumerate(current):
        c1, c2, c3 = st.columns([0.12, 0.12, 0.76])
        with c1:
            if st.button("↑", key=f"{state_key}_up_{idx}", disabled=(idx == 0)):
                st.session_state[state_key] = move_item(current, idx, -1)
                st.rerun()
        with c2:
            if st.button("↓", key=f"{state_key}_down_{idx}", disabled=(idx == len(current) - 1)):
                st.session_state[state_key] = move_item(current, idx, +1)
                st.rerun()
        with c3:
            st.write(item)

    return st.session_state[state_key]

# -------------------------
# Notes UI (only when NOT locked)
# -------------------------
QUIZ_TYPES = [
    "Multiple Choice",
    "Select All That Apply",
    "True / False",
    "Fill in the Blank",
    "Short Answer",
    "Matching",
    "Ordering",
    "Flashcards (Study Mode)",
]

if not st.session_state["locked"]:
    st.selectbox("Quiz type", options=QUIZ_TYPES, key="quiz_type")
    st.number_input(
        "Number of questions",
        min_value=1,
        max_value=15,
        value=5,
        step=1,
        key="num_questions",
    )
    st.text_area("What are you studying? (paste your notes here)", key="notes")
else:
    st.info("Notes hidden while you take the quiz. Click Start Over to edit them.")

# -------------------------
# Groq helpers
# -------------------------
def call_groq_json(prompt: str, api_key: str) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Return ONLY valid JSON. No markdown. No extra text."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```").strip()
        if content.endswith("```"):
            content = content[:-3].strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        st.error(f"Groq returned invalid JSON: {e}")
        st.write("Raw model output (first 2000 chars):")
        st.code(content[:2000])
        st.write("Raw model output (last 2000 chars):")
        st.code(content[-2000:])
        raise


def _slug_quiz_type(label: str) -> str:
    mapping = {
        "Multiple Choice": "multiple_choice",
        "Select All That Apply": "select_all",
        "True / False": "true_false",
        "Fill in the Blank": "fill_in_blank",
        "Short Answer": "short_answer",
        "Matching": "matching",
        "Ordering": "ordering",
        "Flashcards (Study Mode)": "flashcard",
    }
    return mapping[label]

def build_prompt(subject: str, study_material: str, quiz_type_label: str, n: int) -> str:
    qt = _slug_quiz_type(quiz_type_label)

    schema = r"""
{
  "quiz_title": "string",
  "questions": [
    {
      "type": "multiple_choice | select_all | true_false | fill_in_blank | short_answer | matching | ordering | flashcard",
      "prompt": "string",
      "choices": ["string"],
      "correct": "varies by type",
      "acceptable_answers": ["string"],
      "explanation": "string"
    }
  ]
}
""".strip()

    if qt == "multiple_choice":
        rules = f"""
Create exactly {n} questions of type "multiple_choice".
- choices: exactly 4 strings
- correct: integer 0..3
- acceptable_answers: []
""".strip()

    elif qt == "select_all":
        rules = f"""
Create exactly {n} questions of type "select_all".
- choices: 5 to 7 strings
- correct: list of integers (e.g., [0,2,4]) representing ALL correct choices (sorted ascending)
- There must be at least 2 correct choices and at least 1 incorrect choice
- acceptable_answers: []
""".strip()

    elif qt == "true_false":
        rules = f"""
Create exactly {n} questions of type "true_false".
- choices: exactly ["True","False"]
- correct: boolean true/false
- acceptable_answers: []
""".strip()

    elif qt == "fill_in_blank":
        rules = f"""
Create exactly {n} questions of type "fill_in_blank".
- prompt contains exactly one blank: _____
- choices: []
- correct: primary answer string
- acceptable_answers: include correct plus close variants
""".strip()

    elif qt == "short_answer":
        rules = f"""
Create exactly {n} questions of type "short_answer".
- choices: []
- correct: model answer string
- acceptable_answers: include key phrases / equivalent answers
""".strip()

    elif qt == "matching":
        rules = f"""
Create exactly {n} questions of type "matching".
- choices: []
- correct: list of pairs like [["A","B"], ...] with 4 to 6 pairs
- acceptable_answers: []
""".strip()

    elif qt == "ordering":
        rules = f"""
Create exactly {n} questions of type "ordering".
- prompt asks to put the items in the correct order
- choices: 4 to 7 items (these are the items to order)
- correct: list of integers that is the correct order of indices (e.g., [2,0,3,1])
- acceptable_answers: []
""".strip()

    else:  # flashcard
        rules = f"""
Create exactly {n} questions of type "flashcard".
- prompt is the front of the flashcard (term / question)
- choices: []
- correct: the back of the flashcard (definition / answer)
- acceptable_answers: []
- explanation: can be same as correct or a short extra tip
""".strip()

    return f"""
You are generating a quiz based ONLY on the study material below.

Use ONLY the study material below. Do not use outside knowledge.

Return ONLY JSON matching EXACTLY this schema (no markdown, no extra keys):
{schema}

{rules}

General requirements:
- Keep prompts clear and student-friendly.
- Every question must include a helpful explanation (flashcards can repeat the answer).

Study material:
{study_material}
""".strip()

# -------------------------
# Generate (lock immediately so notes disappear before finishing quiz)
# -------------------------
if st.button("Generate Quiz", type="primary"):
    groq_key_val = GROQ_API_KEY  # from terminal env var (hidden)
    notes_val = st.session_state.get("notes", "").strip()
    quiz_type_val = st.session_state.get("quiz_type", "Multiple Choice")
    n_val = int(st.session_state.get("num_questions", 5))

    if not groq_key_val:
        st.warning("Missing GROQ_API_KEY. Set it in the terminal and rerun Streamlit.")
    elif not notes_val:
        st.warning("Please paste notes so I have study material.")
    else:
        st.session_state["locked"] = True

        # Clear old answers
        for k in list(st.session_state.keys()):
            if k.startswith("answer_"):
                del st.session_state[k]
        subject_val = "Study Notes"
        prompt = build_prompt(subject_val, notes_val, quiz_type_val, n_val)
        with st.spinner("Generating quiz with Groq..."):
            try:
                st.session_state["quiz"] = call_groq_json(prompt, groq_key_val)
                st.rerun()
            except Exception as e:
                st.session_state["locked"] = False
                st.error("Could not generate quiz.")
                st.exception(e)

# -------------------------
# Helpers for checking answers
# -------------------------
def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def is_close_text_answer(user: str, acceptable: list[str]) -> bool:
    u = norm(user)
    if not u:
        return False
    acc = {norm(a) for a in (acceptable or []) if a is not None}
    return u in acc

# -------------------------
# Render quiz
# -------------------------
quiz = st.session_state.get("quiz")
if quiz:
    st.subheader(quiz.get("quiz_title", "Generated Quiz"))

    questions = quiz.get("questions", [])
    if not isinstance(questions, list) or not questions:
        st.error("Quiz JSON did not include a valid questions list. Try generating again.")
        st.json(quiz)
    else:
        for i, q in enumerate(questions):
            qnum = i + 1
            qtype = q.get("type", "")
            prompt = q.get("prompt", "")
            choices = q.get("choices", []) or []

            st.write(f"**{qnum}.** {prompt}")
            key = f"answer_{qnum}"

            if qtype == "multiple_choice":
                st.radio(
                    "Select one:",
                    options=list(range(len(choices))),
                    format_func=lambda ix: choices[ix],
                    key=key,
                    label_visibility="collapsed",
                )

            elif qtype == "select_all":
                st.multiselect(
                    "Select all that apply:",
                    options=list(range(len(choices))),
                    format_func=lambda ix: choices[ix],
                    key=key,
                    label_visibility="collapsed",
                )

            elif qtype == "true_false":
                st.radio(
                    "Select one:",
                    options=["True", "False"],
                    key=key,
                    horizontal=True,
                    label_visibility="collapsed",
                )

            elif qtype == "fill_in_blank":
                st.text_input("Your answer:", key=key, label_visibility="collapsed")

            elif qtype == "short_answer":
                st.text_area("Your answer:", key=key, label_visibility="collapsed")

            elif qtype == "ordering":
                st.caption("Reorder the items into the correct sequence (top → bottom):")
                reorder_ui("", choices, key)

            elif qtype == "matching":
                st.caption("Match Column A to Column B by reordering Column B until they line up.")
                pairs = q.get("correct") or []
                left_items = [a for a, _ in pairs]
                right_items = [b for _, b in pairs]

                cA, cB = st.columns(2)
                with cA:
                    st.write("**Column A**")
                    for a in left_items:
                        st.write(a)

                with cB:
                    st.write("**Column B (reorder this)**")
                    reorder_ui("", right_items, key)

            elif qtype == "flashcard":
                st.caption("Flashcard (study mode):")
                with st.expander("Show answer"):
                    st.write(q.get("correct", ""))
                    if q.get("explanation"):
                        st.caption(q.get("explanation", ""))

            else:
                st.error(f"Unknown question type: {qtype}")
                st.json(q)

            st.divider()

        all_flashcards = all((q.get("type") == "flashcard") for q in questions)

        if not all_flashcards and st.button("Finish Quiz / Check Answers"):
            score = 0
            total = len([q for q in questions if q.get("type") != "flashcard"])

            for i, q in enumerate(questions):
                qnum = i + 1
                qtype = q.get("type", "")
                explanation = q.get("explanation", "")
                user_val = st.session_state.get(f"answer_{qnum}")

                if qtype == "flashcard":
                    continue

                correct = q.get("correct")
                acceptable = q.get("acceptable_answers") or []
                choices = q.get("choices", []) or []

                correct_now = False
                correct_display = ""

                if qtype == "multiple_choice":
                    try:
                        correct_index = int(correct)
                        correct_display = choices[correct_index]
                        correct_now = int(user_val) == correct_index
                    except Exception:
                        correct_now = False

                elif qtype == "select_all":
                    try:
                        correct_list = list(map(int, correct or []))
                        user_list = list(map(int, user_val or []))
                        correct_now = sorted(user_list) == sorted(correct_list)
                        correct_display = ", ".join([choices[ix] for ix in correct_list])
                    except Exception:
                        correct_now = False

                elif qtype == "true_false":
                    correct_bool = bool(correct)
                    correct_display = "True" if correct_bool else "False"
                    correct_now = (str(user_val) == correct_display)

                elif qtype in ("fill_in_blank", "short_answer"):
                    correct_display = str(correct)
                    correct_now = is_close_text_answer(str(user_val), [str(correct)] + list(acceptable))

                elif qtype == "ordering":
                    try:
                        target_order = list(map(int, correct or []))
                        target_items = [choices[ix] for ix in target_order]

                        user_items = user_val or []
                        correct_now = list(user_items) == list(target_items)

                        correct_display = " → ".join(target_items)
                    except Exception:
                        correct_now = False

                elif qtype == "matching":
                    try:
                        pairs = correct or []
                        target_right = [b for _, b in pairs]

                        user_right = user_val or []
                        correct_now = list(user_right) == list(target_right)

                        correct_display = "\n".join([f"{a} -> {b}" for a, b in pairs])
                    except Exception:
                        correct_now = False

                if correct_now:
                    score += 1
                    st.success(f"Q{qnum}: Correct")
                else:
                    st.error(f"Q{qnum}: Incorrect")
                    if correct_display:
                        st.write(f"**Correct answer:** {correct_display}")

                with st.expander(f"Explanation for Q{qnum}"):
                    st.write(explanation)

            st.markdown(f"### Score: {score}/{total}")