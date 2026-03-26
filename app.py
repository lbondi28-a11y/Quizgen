import streamlit as st
from openai import OpenAI
from PIL import Image
import pytesseract

# Connect to AI
client = OpenAI()

# Title
st.title("AI Quiz Generator")

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
    image = Image.open(image_file)
    image_text = pytesseract.image_to_string(image)

# Combine all notes
study_material = notes + "\n" + image_text

# -----------------------
# Generate Quiz
# -----------------------
if st.button("Generate Quiz"):

    if subject.strip() == "" or study_material.strip() == "":
        st.warning("Please enter your subject and study material.")

    else:
        prompt = f"""
        You are a teacher.

        Subject: {subject}
        Quiz type: {quiz_type}

        Study material:
        {study_material}

        Create 5 quiz questions in the same language as the notes.
        """

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}]
        )

        quiz = response.choices[0].message.content

        st.subheader("Generated Quiz")
        st.write(quiz)
