import streamlit as st
from PIL import Image
import easyocr
import streamlit.components.v1 as components



st.set_page_config(page_title="AI Quiz Generator (Browser LLM)")

st.title("AI Quiz Generator (Using Browser LLM)")

# -----------------------
# User Inputs
# -----------------------
subject = st.text_input("Subject")

quiz_type = st.selectbox(
    "Quiz Type",
    ["Multiple Choice", "Open Answer", "True/False", "Fill in the Blank"]
)

notes = st.text_area("What are you studying?")

# Upload image (optional)

image_file = st.file_uploader(
    "Upload a picture of your notes",
    type=["png", "jpg", "jpeg"]
)

image_text = ""

if image_file is not None:
    # Open the uploaded image
    image = Image.open(image_file)
    
    # Initialize EasyOCR reader (English)
    reader = easyocr.Reader(['en'])
    
    # Run OCR on the image
    result = reader.readtext(image)
    
    # Combine detected text into a single string
    image_text = " ".join([text for (_, text, _) in result])
    
    # Show the uploaded image
    st.image(image, caption="Uploaded Image", use_column_width=True)

# -----------------------
# Combine all notes
# -----------------------
study_material = (notes + "\n" + image_text).strip()

# -----------------------
# Generate Quiz
# -----------------------
# ------------------------
# 1️⃣ Page setup
# ------------------------
st.set_page_config(page_title="Quiz Generator", page_icon="📝")
st.title("AI Quiz Generator")
st.write("Enter your subject and study material below to generate a quiz.")

# ------------------------
# 2️⃣ Inputs
# ------------------------
subject = st.text_input("Subject")
study_material = st.text_area("Study Material")
quiz_type = st.selectbox("Quiz Type", ["Multiple Choice", "Short Answer"])

# ------------------------
# 3️⃣ Session state for quiz
# ------------------------
if "quiz" not in st.session_state:
    st.session_state.quiz = []

# ------------------------
# 4️⃣ Function to generate quiz
# ------------------------
def generate_quiz_from_prompt(prompt):
    # Placeholder: replace with GPT/OpenAI API call if you want real questions
    return [
        "Question 1: ...",
        "Question 2: ...",
        "Question 3: ...",
        "Question 4: ...",
        "Question 5: ..."
    ]

# ------------------------
# 5️⃣ Button to generate quiz
# ------------------------
if st.button("Generate Quiz"):
    if subject.strip() == "" or study_material.strip() == "":
        st.warning("Please enter your subject and study material.")
    else:
        prompt = f"""
Create 5 {quiz_type} quiz questions for the subject "{subject}".
Use ONLY the following study material:
{study_material}
Make the questions clear and student-friendly.
"""
        st.session_state.quiz = generate_quiz_from_prompt(prompt)

# ------------------------
# 6️⃣ Display the quiz
# ------------------------
if st.session_state.quiz:
    st.subheader("Generated Quiz")
    for q in st.session_state.quiz:
        st.write(q)
  
        components.html(f"""
        <div id="output" style="white-space: pre-wrap; font-family: sans-serif;"></div>
        <script type="module">
        import {{ GPT4AllWeb }} from "https://cdn.jsdelivr.net/npm/gpt4all-web/dist/gpt4all.min.js";

        async function runGPT4All() {{
            const output = document.getElementById("output");
            output.innerText = "Loading model... (this may take a few seconds)";

            // Initialize GPT4All-Web
            const model = new GPT4AllWeb();

            // Load Tiny LLM (hosted on CDN or your server)
            await model.loadModel("https://gpt4all.io/models/gpt4all-lora-tiny.bin");

            // Generate quiz
            const response = await model.prompt(`{prompt}`);
            output.innerText = response;
        }}

        runGPT4All();
        </script>
        """, height=500)
  