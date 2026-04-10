# ✏️ We're bringing in special helpers (called "libraries") that do cool stuff for us!
import json       # json helps us read and write data that looks like a treasure map with labels
import re         # re lets us search for patterns in text, like finding all the spaces in a sentence
import requests   # requests lets us send messages to the internet, like sending a letter and waiting for a reply
import streamlit as st  # streamlit builds our whole website so people can see buttons and stuff
import os         # os lets us talk to the computer itself, like reading secret notes it saved for us

# 🏠 Set up the browser tab — give it a title and center everything on the page
st.set_page_config(page_title="AI Quiz Generator (Groq)", layout="centered")

# -------------------------
# 🔐 Security: read secrets from terminal env vars (no UI key input)
# -------------------------
# Ask the computer if it has a secret password stored called "GROQ_API_KEY"
# If it doesn't have one, we just get an empty string ""
# .strip() removes any sneaky spaces hiding at the beginning or end
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Same thing — ask the computer for the app password that protects our quiz maker
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()

# 🚪 Password gate — only runs if someone actually set an APP_PASSWORD
if APP_PASSWORD:
    # Check if we've stored whether the user already signed in (session_state is like our notebook)
    if "authed" not in st.session_state:
        # They haven't signed in yet, so write False in our notebook
        st.session_state["authed"] = False

    # If the user is NOT yet signed in, show them the login screen
    if not st.session_state["authed"]:
        # Show the big title at the top of the page
        st.title("AI Quiz Generator (Groq)")
        # Show a password box — the letters are hidden as dots so nobody can peek
        pw = st.text_input("App password", type="password")
        # Show a "Sign in" button — if clicked, run the code inside
        if st.button("Sign in"):
            # Check if what they typed matches the real password
            if pw == APP_PASSWORD:
                # ✅ Correct! Write True in our notebook so we remember they signed in
                st.session_state["authed"] = True
                # Refresh the page so the quiz maker appears
                st.rerun()
            else:
                # ❌ Wrong password — show a red error message
                st.error("Wrong password.")
        # Stop here — don't show anything else until they're signed in
        st.stop()

# 🔑 If the secret AI key is missing, tell the user how to add it and then stop
if not GROQ_API_KEY:
    # Show a red error message explaining what went wrong
    st.error("Missing GROQ_API_KEY. Set it in the terminal and restart Streamlit.")
    # Show example commands they can type in the terminal to fix it
    st.code(
        'export GROQ_API_KEY="gsk_..."\nexport APP_PASSWORD="..."  # optional\nstreamlit run app.py --server.address=127.0.0.1 --server.port=8501'
    )
    # Stop — we can't do anything without the AI key
    st.stop()

# -------------------------
# 🖥️ UI — the things people actually see on the page
# -------------------------
# Show the big title at the top of the page
st.title("AI Quiz Generator (Groq)")

# -------------------------
# 🗒️ State — our notebook that remembers things while the page is open
# -------------------------
# If there's no quiz saved yet, write None (meaning "nothing") in our notebook
if "quiz" not in st.session_state:
    st.session_state["quiz"] = None

# If we haven't locked the notes yet, start with locked = False (unlocked)
if "locked" not in st.session_state:
    st.session_state["locked"] = False

# -------------------------
# 🔄 Start over button area
# -------------------------
# Split the top area into two side-by-side columns (like two boxes next to each other)
col1, col2 = st.columns(2)

# Put a button in the left column
with col1:
    # If the user clicks "Start Over / Edit Notes", erase everything and start fresh
    if st.button("Start Over / Edit Notes"):
        # Forget the quiz we made — set it back to nothing
        st.session_state["quiz"] = None
        # Unlock the notes so the user can edit them again
        st.session_state["locked"] = False
        # Go through everything saved in our notebook...
        for k in list(st.session_state.keys()):
            # ...and delete any saved answers (they start with "answer_")
            if k.startswith("answer_"):
                del st.session_state[k]

# Put a small helpful message in the right column
with col2:
    st.caption("Notes hide after Generate. Click Start Over to edit them again.")

# -------------------------
# 🔀 Helpers: Accessible "drag-like" reorder UI (no installs)
# -------------------------
def move_item(lst: list, i: int, direction: int) -> list:
    """direction: -1 for up, +1 for down"""
    # If the list is empty OR the position i is out of range, give back the list unchanged
    if not lst or i < 0 or i >= len(lst):
        return lst

    # Figure out which position we're swapping with (one above or one below)
    j = i + direction

    # If the swap position would go off the edge of the list, do nothing
    if j < 0 or j >= len(lst):
        return lst

    # Make a copy of the list so we don't accidentally change the original
    new_lst = lst[:]

    # Swap the two items — like swapping two cards in your hand
    new_lst[i], new_lst[j] = new_lst[j], new_lst[i]

    # Give back the new list with the items swapped
    return new_lst

def reorder_ui(title: str, items: list[str], state_key: str) -> list[str]:
    """
    Renders a reorder UI using Up/Down buttons.
    Returns the reordered list (also stored in st.session_state[state_key]).
    """
    # If a title was given, show it on the page
    if title:
        st.write(title)

    # Check if we already have a saved order in our notebook for this list
    if (
        state_key not in st.session_state           # we haven't saved anything yet
        or not isinstance(st.session_state[state_key], list)  # what we saved isn't a list
        or not st.session_state[state_key]          # the saved list is empty
    ):
        # Save a fresh copy of the items into our notebook
        st.session_state[state_key] = items[:]

    # Grab the current order from our notebook
    current = st.session_state[state_key]

    # Loop through each item in the list, keeping track of its position number (idx)
    for idx, item in enumerate(current):
        # Create three columns: a tiny one for ↑, a tiny one for ↓, and a wide one for the item text
        c1, c2, c3 = st.columns([0.12, 0.12, 0.76])

        # ↑ Up button — disabled if this item is already at the top (idx == 0)
        with c1:
            if st.button("↑", key=f"{state_key}_up_{idx}", disabled=(idx == 0)):
                # Move this item up one spot and save the new order
                st.session_state[state_key] = move_item(current, idx, -1)
                # Refresh the page so the new order shows up right away
                st.rerun()

        # ↓ Down button — disabled if this item is already at the bottom
        with c2:
            if st.button("↓", key=f"{state_key}_down_{idx}", disabled=(idx == len(current) - 1)):
                # Move this item down one spot and save the new order
                st.session_state[state_key] = move_item(current, idx, +1)
                # Refresh the page so the new order shows up right away
                st.rerun()

        # Show the actual text of this item in the wide column
        with c3:
            st.write(item)

    # Give back the current order (whatever is saved in our notebook)
    return st.session_state[state_key]

# -------------------------
# 📝 Notes UI (only when NOT locked)
# -------------------------
# A list of all the quiz types the user can pick from
QUIZ_TYPES = [
    "Multiple Choice",         # Pick one right answer from four choices
    "Select All That Apply",   # Pick ALL the right answers (there could be more than one!)
    "True / False",            # Is the statement true or false?
    "Fill in the Blank",       # Complete the sentence by typing the missing word
    "Short Answer",            # Write a short answer in your own words
    "Matching",                # Connect things in Column A to things in Column B
    "Ordering",                # Put the items in the correct order
    "Flashcards (Study Mode)", # Flip virtual cards to study terms and definitions
]

# Only show the settings if the notes are not locked (quiz hasn't been generated yet)
if not st.session_state["locked"]:
    # Show a dropdown menu so the user can pick what kind of quiz they want
    st.selectbox("Quiz type", options=QUIZ_TYPES, key="quiz_type")

    # Show a number picker — the user chooses how many questions they want (1 to 15)
    st.number_input(
        "Number of questions",
        min_value=1,    # Can't have fewer than 1 question
        max_value=15,   # Can't have more than 15 questions
        value=5,        # Default is 5 questions
        step=1,         # Goes up or down by 1 at a time
        key="num_questions",
    )

    # Show a big text box where the user pastes their study notes
    st.text_area("What are you studying? (paste your notes here)", key="notes")
else:
    # Quiz is in progress — hide the notes and show a friendly reminder
    st.info("Notes hidden while you take the quiz. Click Start Over to edit them.")

# -------------------------
# 🤖 Groq helpers — functions that talk to the AI
# -------------------------
def call_groq_json(prompt: str, api_key: str) -> dict:
    # The web address of the Groq AI — like the address of a restaurant we're ordering from
    url = "https://api.groq.com/openai/v1/chat/completions"

    # Headers are like the envelope we put our letter in — they say who we are
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # The actual message we're sending to the AI
    payload = {
        "model": "llama-3.1-8b-instant",  # Which AI brain to use (like picking a specific helper)
        "messages": [
            # Tell the AI to only reply with JSON (a special organized format), no fancy extras
            {"role": "system", "content": "Return ONLY valid JSON. No markdown. No extra text."},
            # The real question / instructions we want the AI to answer
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,  # Low temperature means the AI gives more predictable answers (less wild guesses)
    }

    # Send our message to the AI and wait up to 60 seconds for a reply
    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    # If something went wrong (like a bad API key), this will shout about it right away
    resp.raise_for_status()

    # Dig into the AI's reply and grab the actual text it wrote for us
    content = resp.json()["choices"][0]["message"]["content"]

    # Sometimes the AI wraps its answer in code fences like ```json ... ``` — we need to peel those off
    if content.startswith("```"):
        # Remove the opening ``` or ```json tag
        content = content.removeprefix("```json").removeprefix("```").strip()
        # Remove the closing ``` tag if it's still there
        if content.endswith("```"):
            content = content[:-3].strip()

    # Try to turn the text into a real Python dictionary (the organized treasure-map format)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Oops! The AI didn't follow the rules — show an error and show what it sent back
        st.error(f"Groq returned invalid JSON: {e}")
        st.write("Raw model output (first 2000 chars):")
        st.code(content[:2000])   # Show the first 2000 characters of the bad reply
        st.write("Raw model output (last 2000 chars):")
        st.code(content[-2000:])  # Show the last 2000 characters of the bad reply
        raise  # Re-throw the error so the app knows something broke


def _slug_quiz_type(label: str) -> str:
    # A lookup table — like a decoder ring that turns a pretty name into a short code name
    mapping = {
        "Multiple Choice":         "multiple_choice",
        "Select All That Apply":   "select_all",
        "True / False":            "true_false",
        "Fill in the Blank":       "fill_in_blank",
        "Short Answer":            "short_answer",
        "Matching":                "matching",
        "Ordering":                "ordering",
        "Flashcards (Study Mode)": "flashcard",
    }
    # Look up the label and return its short code name
    return mapping[label]

def build_prompt(subject: str, study_material: str, quiz_type_label: str, n: int) -> str:
    # Convert the pretty quiz type name (like "Multiple Choice") to a short code ("multiple_choice")
    qt = _slug_quiz_type(quiz_type_label)

    # This is the blueprint (shape) of the JSON we want the AI to return — like a form to fill in
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

    # Based on which quiz type was chosen, write specific rules for the AI to follow
    if qt == "multiple_choice":
        # Rules for multiple choice — 4 options, one right answer (given as a number 0-3)
        rules = f"""
Create exactly {n} questions of type "multiple_choice".
- choices: exactly 4 strings
- correct: integer 0..3
- acceptable_answers: []
""".strip()

    elif qt == "select_all":
        # Rules for select-all — several options, multiple right answers
        rules = f"""
Create exactly {n} questions of type "select_all".
- choices: 5 to 7 strings
- correct: list of integers (e.g., [0,2,4]) representing ALL correct choices (sorted ascending)
- There must be at least 2 correct choices and at least 1 incorrect choice
- acceptable_answers: []
""".strip()

    elif qt == "true_false":
        # Rules for true/false — only two choices, answer is a boolean (true or false)
        rules = f"""
Create exactly {n} questions of type "true_false".
- choices: exactly ["True","False"]
- correct: boolean true/false
- acceptable_answers: []
""".strip()

    elif qt == "fill_in_blank":
        # Rules for fill-in-the-blank — sentence has a _____ the student must complete
        rules = f"""
Create exactly {n} questions of type "fill_in_blank".
- prompt contains exactly one blank: _____
- choices: []
- correct: primary answer string
- acceptable_answers: include correct plus close variants
""".strip()

    elif qt == "short_answer":
        # Rules for short answer — student writes a sentence or two in their own words
        rules = f"""
Create exactly {n} questions of type "short_answer".
- choices: []
- correct: model answer string
- acceptable_answers: include key phrases / equivalent answers
""".strip()

    elif qt == "matching":
        # Rules for matching — pairs of things that belong together (like a word and its definition)
        rules = f"""
Create exactly {n} questions of type "matching".
- choices: []
- correct: list of pairs like [["A","B"], ...] with 4 to 6 pairs
- acceptable_answers: []
""".strip()

    elif qt == "ordering":
        # Rules for ordering — student puts a list of items in the correct sequence
        rules = f"""
Create exactly {n} questions of type "ordering".
- prompt asks to put the items in the correct order
- choices: 4 to 7 items (these are the items to order)
- correct: list of integers that is the correct order of indices (e.g., [2,0,3,1])
- acceptable_answers: []
""".strip()

    else:  # flashcard — flip a card to see the answer
        rules = f"""
Create exactly {n} questions of type "flashcard".
- prompt is the front of the flashcard (term / question)
- choices: []
- correct: the back of the flashcard (definition / answer)
- acceptable_answers: []
- explanation: can be same as correct or a short extra tip
""".strip()

    # Glue everything together into one big message (the "prompt") we'll send to the AI
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
# ▶️ Generate (lock immediately so notes disappear before finishing quiz)
# -------------------------
# Show the big "Generate Quiz" button — it's highlighted as the primary action
if st.button("Generate Quiz", type="primary"):
    # Grab the secret AI key from our saved secret (the computer's environment)
    groq_key_val = GROQ_API_KEY  # from terminal env var (hidden)

    # Get the notes the user pasted and remove extra spaces from the edges
    notes_val = st.session_state.get("notes", "").strip()

    # Get the quiz type the user chose (defaults to "Multiple Choice" if nothing chosen)
    quiz_type_val = st.session_state.get("quiz_type", "Multiple Choice")

    # Get the number of questions the user picked and make sure it's a whole number
    n_val = int(st.session_state.get("num_questions", 5))

    # Make sure we actually have an AI key before trying anything
    if not groq_key_val:
        st.warning("Missing GROQ_API_KEY. Set it in the terminal and rerun Streamlit.")

    # Make sure the user actually pasted some notes to study from
    elif not notes_val:
        st.warning("Please paste notes so I have study material.")

    else:
        # Lock the notes — hide them so the user can focus on taking the quiz
        st.session_state["locked"] = True

        # Go through our notebook and delete any leftover answers from a previous quiz
        for k in list(st.session_state.keys()):
            if k.startswith("answer_"):
                del st.session_state[k]

        # Give the quiz a generic subject name (could be made more specific later)
        subject_val = "Study Notes"

        # Build the big instruction message we'll send to the AI
        prompt = build_prompt(subject_val, notes_val, quiz_type_val, n_val)

        # Show a spinning animation while we wait for the AI to come up with questions
        with st.spinner("Generating quiz with Groq..."):
            try:
                # Send the prompt to the AI and save the quiz it gives us back
                st.session_state["quiz"] = call_groq_json(prompt, groq_key_val)
                # Refresh the page so the quiz appears immediately
                st.rerun()
            except Exception as e:
                # Something broke — unlock the notes so the user can try again
                st.session_state["locked"] = False
                st.error("Could not generate quiz.")
                # Show the actual error message so we can figure out what went wrong
                st.exception(e)

# -------------------------
# ✅ Helpers for checking answers
# -------------------------
def norm(s: str) -> str:
    # Take whatever string we got (or "" if it's None), trim spaces, and make it all lowercase
    s = (s or "").strip().lower()
    # Replace any run of whitespace (tabs, multiple spaces) with a single space
    s = re.sub(r"\s+", " ", s)
    # Give back the cleaned-up version
    return s

def is_close_text_answer(user: str, acceptable: list[str]) -> bool:
    # Clean up what the user typed
    u = norm(user)
    # If the user didn't type anything, it's definitely wrong
    if not u:
        return False
    # Clean up all the acceptable answers and put them in a set (a bag with no duplicates)
    # We skip any None values so we don't crash
    acc = {norm(a) for a in (acceptable or []) if a is not None}
    # Check if what the user typed exactly matches any of the acceptable answers
    return u in acc

# -------------------------
# 📋 Render quiz — show the questions on the page
# -------------------------
# Look in our notebook for a saved quiz
quiz = st.session_state.get("quiz")

# Only show the quiz section if we actually have a quiz saved
if quiz:
    # Show the quiz title as a section heading (use "Generated Quiz" if there's no title)
    st.subheader(quiz.get("quiz_title", "Generated Quiz"))

    # Pull out the list of questions from the quiz data
    questions = quiz.get("questions", [])

    # Make sure questions is actually a non-empty list — if not, something went wrong
    if not isinstance(questions, list) or not questions:
        st.error("Quiz JSON did not include a valid questions list. Try generating again.")
        # Show the raw quiz data so we can see what the AI actually returned
        st.json(quiz)
    else:
        # Loop through every question — i is the position (0, 1, 2...), q is the question itself
        for i, q in enumerate(questions):
            qnum = i + 1          # Question numbers start at 1, not 0 (more human-friendly!)
            qtype = q.get("type", "")      # What kind of question is this?
            prompt = q.get("prompt", "")   # The actual question text
            choices = q.get("choices", []) or []  # The list of answer options (might be empty)

            # Show the question number and text in bold
            st.write(f"**{qnum}.** {prompt}")

            # The unique name we'll use to save this question's answer in our notebook
            key = f"answer_{qnum}"

            # --- Show the right kind of answer widget for each question type ---

            if qtype == "multiple_choice":
                # Show radio buttons — the user can pick exactly ONE option
                st.radio(
                    "Select one:",
                    options=list(range(len(choices))),  # Options are 0, 1, 2, 3 (index numbers)
                    format_func=lambda ix: choices[ix], # But display the actual text, not the number
                    key=key,
                    label_visibility="collapsed",  # Hide the "Select one:" label (it's already obvious)
                )

            elif qtype == "select_all":
                # Show a multi-select box — the user can pick MULTIPLE options
                st.multiselect(
                    "Select all that apply:",
                    options=list(range(len(choices))),  # Same trick — use index numbers internally
                    format_func=lambda ix: choices[ix], # But show the real text to the user
                    key=key,
                    label_visibility="collapsed",
                )

            elif qtype == "true_false":
                # Show two radio buttons side by side: True and False
                st.radio(
                    "Select one:",
                    options=["True", "False"],
                    key=key,
                    horizontal=True,          # Put True and False next to each other, not stacked
                    label_visibility="collapsed",
                )

            elif qtype == "fill_in_blank":
                # Show a single-line text box for typing the missing word
                st.text_input("Your answer:", key=key, label_visibility="collapsed")

            elif qtype == "short_answer":
                # Show a bigger multi-line text box for writing a sentence or two
                st.text_area("Your answer:", key=key, label_visibility="collapsed")

            elif qtype == "ordering":
                # Tell the user what they need to do
                st.caption("Reorder the items into the correct sequence (top → bottom):")
                # Show the up/down button reorder widget with the list of items
                reorder_ui("", choices, key)

            elif qtype == "matching":
                # Tell the user how matching works
                st.caption("Match Column A to Column B by reordering Column B until they line up.")

                # Get the list of correct pairs (each pair is like ["word", "definition"])
                pairs = q.get("correct") or []

                # Pull out just the left-side items (Column A)
                left_items = [a for a, _ in pairs]

                # Pull out just the right-side items (Column B) — these are what the user will reorder
                right_items = [b for _, b in pairs]

                # Split the screen into two side-by-side columns
                cA, cB = st.columns(2)

                with cA:
                    st.write("**Column A**")
                    # Show each left-side item — these are fixed, the user can't move them
                    for a in left_items:
                        st.write(a)

                with cB:
                    st.write("**Column B (reorder this)**")
                    # Show the right-side items with up/down buttons so the user can rearrange them
                    reorder_ui("", right_items, key)

            elif qtype == "flashcard":
                # Let the user know this is a flashcard they can flip
                st.caption("Flashcard (study mode):")
                # Hide the answer inside a collapsible section — click to reveal!
                with st.expander("Show answer"):
                    # Show the correct answer (the back of the flashcard)
                    st.write(q.get("correct", ""))
                    # If there's an extra explanation tip, show it in small text
                    if q.get("explanation"):
                        st.caption(q.get("explanation", ""))

            else:
                # We don't know this question type — show an error and the raw data
                st.error(f"Unknown question type: {qtype}")
                st.json(q)

            # Draw a horizontal line between questions so they're easy to tell apart
            st.divider()

        # Check whether ALL questions in this quiz are flashcards
        all_flashcards = all((q.get("type") == "flashcard") for q in questions)

        # Only show the "Finish Quiz" button if there are real questions to grade (not just flashcards)
        if not all_flashcards and st.button("Finish Quiz / Check Answers"):
            score = 0  # Start the score at zero — the user hasn't gotten any right yet

            # Count how many questions are NOT flashcards (those are the ones we can grade)
            total = len([q for q in questions if q.get("type") != "flashcard"])

            # Go through every question again to check the answers
            for i, q in enumerate(questions):
                qnum = i + 1                          # Question number (starting from 1)
                qtype = q.get("type", "")             # What kind of question is this?
                explanation = q.get("explanation", "") # The helpful explanation to show afterward
                user_val = st.session_state.get(f"answer_{qnum}")  # What the user answered

                # Skip flashcards — we can't grade them since the user just flips them to study
                if qtype == "flashcard":
                    continue

                correct = q.get("correct")            # The right answer (from the AI)
                acceptable = q.get("acceptable_answers") or []  # Other OK answers (for text questions)
                choices = q.get("choices", []) or []  # The list of options (if any)

                correct_now = False   # Assume the user got it wrong until we check
                correct_display = "" # We'll fill this in with a human-readable correct answer

                if qtype == "multiple_choice":
                    try:
                        # The correct answer is stored as a number (0, 1, 2, or 3)
                        correct_index = int(correct)
                        # Turn that number into the actual text of the correct choice
                        correct_display = choices[correct_index]
                        # Check if the user picked the same number as the right answer
                        correct_now = int(user_val) == correct_index
                    except Exception:
                        # Something went wrong with the data — mark it wrong to be safe
                        correct_now = False

                elif qtype == "select_all":
                    try:
                        # The correct answer is a list of numbers — turn each one into an integer
                        correct_list = list(map(int, correct or []))
                        # Do the same for what the user picked
                        user_list = list(map(int, user_val or []))
                        # The user is only right if they picked EXACTLY the same set (order doesn't matter)
                        correct_now = sorted(user_list) == sorted(correct_list)
                        # Build a human-readable list of the correct choices for display
                        correct_display = ", ".join([choices[ix] for ix in correct_list])
                    except Exception:
                        correct_now = False

                elif qtype == "true_false":
                    # Turn the correct value into a real True/False boolean
                    correct_bool = bool(correct)
                    # Convert that to the string "True" or "False" for comparison
                    correct_display = "True" if correct_bool else "False"
                    # Check if what the user selected matches the correct string
                    correct_now = (str(user_val) == correct_display)

                elif qtype in ("fill_in_blank", "short_answer"):
                    # The correct answer is just a plain string
                    correct_display = str(correct)
                    # Check if what the user typed (cleaned up) matches the correct answer or any acceptable variant
                    correct_now = is_close_text_answer(str(user_val), [str(correct)] + list(acceptable))

                elif qtype == "ordering":
                    try:
                        # The correct order is stored as a list of index numbers (like [2, 0, 3, 1])
                        target_order = list(map(int, correct or []))
                        # Convert those index numbers into the actual item text in the right order
                        target_items = [choices[ix] for ix in target_order]

                        # Get what the user actually arranged (list of item texts)
                        user_items = user_val or []
                        # The user is right only if their order exactly matches the target order
                        correct_now = list(user_items) == list(target_items)

                        # Build a pretty display like "Step 1 → Step 2 → Step 3"
                        correct_display = " → ".join(target_items)
                    except Exception:
                        correct_now = False

                elif qtype == "matching":
                    try:
                        # The correct pairs are like [["A", "B"], ["C", "D"], ...]
                        pairs = correct or []
                        # Pull out just the right-side items in the correct order
                        target_right = [b for _, b in pairs]

                        # Get what the user arranged for the right column
                        user_right = user_val or []
                        # The user is right only if their right-column order matches perfectly
                        correct_now = list(user_right) == list(target_right)

                        # Build a display showing each correct pair on its own line
                        correct_display = "\n".join([f"{a} -> {b}" for a, b in pairs])
                    except Exception:
                        correct_now = False

                # --- Show whether the user got this question right or wrong ---
                if correct_now:
                    score += 1  # Add one to the score 🎉
                    st.success(f"Q{qnum}: Correct")
                else:
                    st.error(f"Q{qnum}: Incorrect")
                    # If we know the correct answer, show it so the user can learn
                    if correct_display:
                        st.write(f"**Correct answer:** {correct_display}")

                # Show the explanation in a collapsible section the user can click open
                with st.expander(f"Explanation for Q{qnum}"):
                    st.write(explanation)

            # Show the final score in big heading text (like "### Score: 4/5")
            st.markdown(f"### Score: {score}/{total}")