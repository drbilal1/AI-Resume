import streamlit as st
import openai
from fpdf import FPDF
import tempfile
import os

# --- Configuration ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# --- Session State Setup ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{
        "role": "system",
        "content": """
        You are a professional resume assistant. Follow these rules STRICTLY:
        1. Ask ONLY ONE question per message.
        2. Follow this exact order:
           - Ask for full name (wait for response)
           - Then ask for phone number (wait)
           - Then ask for email (wait)
           - Then ask for address (wait)
           - Then ask for professional summary (wait)
           - Then ask about work experience (one position at a time)
           - Then ask about education
           - Finally ask about skills
        3. Never combine questions.
        4. After all information is collected, say: "RESUME READY: Your resume is now complete."
        """
    }]
if "resume_ready" not in st.session_state:
    st.session_state.resume_ready = False
if "current_input" not in st.session_state:
    st.session_state.current_input = ""
if "resume_md" not in st.session_state:
    st.session_state.resume_md = ""
if "awaiting_reply" not in st.session_state:
    st.session_state.awaiting_reply = False

# --- Helper Functions ---
def enforce_single_question(message):
    """Force single question by taking text before first '?'"""
    if "?" in message:
        return message.split("?")[0] + "?"
    return message

def markdown_to_pdf(markdown_text, filename):
    """Convert markdown to PDF with formatting"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    for line in markdown_text.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
            
        if line.startswith("# "):
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, line[2:], ln=True)
        elif line.startswith("## "):
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, line[3:], ln=True)
        elif line.startswith("- "):
            pdf.cell(10)
            pdf.multi_cell(0, 5, line[2:])
        else:
            pdf.multi_cell(0, 5, line)
        pdf.set_font("Arial", size=12)
    
    pdf.output(filename)

# --- Streamlit UI ---
st.set_page_config(page_title="Resume Builder", layout="centered")
st.title("📝 Professional Resume Builder")
st.write("I'll guide you step-by-step to create your resume. Please answer one question at a time.")

# --- Chat Interface ---
if not st.session_state.resume_ready:
    # Display chat history (without system message)
    for msg in st.session_state.chat_history[1:]:
        st.chat_message(msg["role"]).write(msg["content"])

    # Generate next question when needed
    if not st.session_state.awaiting_reply:
        with st.spinner("Preparing next question..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                new_question = enforce_single_question(response.choices[0].message.content)
                st.session_state.chat_history.append({"role": "assistant", "content": new_question})
                st.session_state.awaiting_reply = True
                st.session_state.current_input = ""  # Clear previous input
                st.rerun()
            except Exception as e:
                st.error(f"Error generating question: {e}")
                st.stop()

    # User input with proper state management
    user_input = st.text_input(
        "Your answer:",
        key="user_input_widget",
        value=st.session_state.current_input,
        on_change=lambda: None
    )

    if st.button("Submit", type="primary"):
        if user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.awaiting_reply = False
            st.session_state.current_input = ""  # Clear input
            st.rerun()

# --- Resume Generation ---
else:
    st.success("✅ All information collected! Generating your resume...")
    
    with st.spinner("Creating professional resume..."):
        try:
            # Generate markdown
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    *st.session_state.chat_history,
                    {"role": "user", "content": "Generate a well-formatted markdown resume with: Contact, Summary, Experience, Education, and Skills sections."}
                ]
            )
            st.session_state.resume_md = response.choices[0].message.content
            
            # Display
            st.markdown(st.session_state.resume_md)
            
            # PDF Generation
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                markdown_to_pdf(st.session_state.resume_md, tmp.name)
                with open(tmp.name, "rb") as f:
                    st.download_button(
                        "⬇️ Download PDF",
                        f.read(),
                        "professional_resume.pdf",
                        "application/pdf",
                        use_container_width=True
                    )
                os.unlink(tmp.name)  # Clean up
            
            # Markdown Download
            st.download_button(
                "⬇️ Download Markdown",
                st.session_state.resume_md,
                "resume.md",
                "text/markdown",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Generation error: {e}")
    
    if st.button("🔄 Start New Resume", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
