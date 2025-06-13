import streamlit as st
import openai
from fpdf import FPDF
import tempfile
import os
import re

# --- Configuration ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it to your app's secrets.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{
        "role": "system",
        "content": """
        You are a professional resume assistant. Follow these rules strictly:
        1. Ask ONE question per message.
        2. Follow this order:
           - Full name
           - Phone number
           - Email address
           - Address
           - Professional summary
           - Work experience (company, position, dates, responsibilities)
           - Education (degree, institution, year)
           - Skills (technical and soft skills)
        3. Wait for user's response before proceeding.
        4. Never combine questions.
        """
    }]
if "resume_ready" not in st.session_state:
    st.session_state.resume_ready = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "resume_md" not in st.session_state:
    st.session_state.resume_md = ""

# --- Helper Functions ---
def enforce_single_question(message):
    """Ensure the assistant only asks one question"""
    if "?" in message:
        questions = [q.strip() for q in message.split("?") if q.strip()]
        if len(questions) > 1:
            return questions[0] + "?"
    return message

def markdown_to_pdf(markdown_text, filename):
    """Convert markdown to PDF with improved formatting"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Process markdown lines
    for line in markdown_text.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(5)  # Add space for empty lines
            continue
            
        # Handle headers
        if line.startswith("# "):
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, line[2:], ln=True)
            pdf.set_font("Arial", size=12)
        elif line.startswith("## "):
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, line[3:], ln=True)
            pdf.set_font("Arial", size=12)
        elif line.startswith("### "):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, line[4:], ln=True)
            pdf.set_font("Arial", size=12)
        else:
            # Handle bullet points
            if line.startswith("- "):
                pdf.cell(10)  # Indent bullets
                line = line[2:]
            pdf.multi_cell(0, 10, line)
    
    pdf.output(filename)

# --- Streamlit UI ---
st.set_page_config(page_title="Smart Resume Builder", layout="centered")
st.title("📄 Smart Resume Builder")
st.write("I'll guide you through creating a professional resume. Please answer one question at a time.")

# --- Chat Interface ---
if not st.session_state.resume_ready:
    # Display chat history (skip system message)
    for msg in st.session_state.chat_history[1:]:
        if msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {msg['content']}")
        elif msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")

    # Generate initial question if needed
    if len(st.session_state.chat_history) == 1:
        with st.spinner("Preparing your resume builder..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                initial_msg = enforce_single_question(response.choices[0].message.content)
                st.session_state.chat_history.append({"role": "assistant", "content": initial_msg})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

    # User input
    user_input = st.text_input("Your response:", key="user_input")
    
    if st.button("Submit", type="primary"):
        if user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.user_input = ""
            
            with st.spinner("Processing..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.chat_history
                    )
                    assistant_msg = enforce_single_question(response.choices[0].message.content)
                    
                    # Check if resume is complete
                    if "resume is ready" in assistant_msg.lower() or \
                       "next steps" in assistant_msg.lower():
                        st.session_state.resume_ready = True
                    else:
                        st.session_state.chat_history.append({"role": "assistant", "content": assistant_msg})
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- Resume Generation ---
else:
    st.success("✅ Resume information complete! Generating your resume...")
    
    with st.spinner("Formatting your resume..."):
        try:
            # Generate markdown resume
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    *st.session_state.chat_history,
                    {"role": "user", "content": "Generate a professional resume in markdown format with these sections: Contact, Summary, Experience, Education, Skills. Use proper formatting."}
                ]
            )
            st.session_state.resume_md = response.choices[0].message.content
            
            # Display markdown
            st.markdown(st.session_state.resume_md)
            
            # Generate PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name
                markdown_to_pdf(st.session_state.resume_md, pdf_path)
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=f.read(),
                        file_name="professional_resume.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
            # Text download
            st.download_button(
                label="⬇️ Download Markdown",
                data=st.session_state.resume_md,
                file_name="resume.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Error generating resume: {e}")
    
    if st.button("🔄 Start Over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
