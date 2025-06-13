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
           - Full name → Phone → Email → Address → Summary → Experience → Education → Skills
        3. After all information is collected, say: "RESUME READY"
        """
    }]
if "resume_ready" not in st.session_state:
    st.session_state.resume_ready = False
if "current_input" not in st.session_state:
    st.session_state.current_input = ""
if "resume_md" not in st.session_state:
    st.session_state.resume_md = ""
if "needs_rerun" not in st.session_state:
    st.session_state.needs_rerun = False

# --- Helper Functions ---
def enforce_single_question(message):
    """Force single question by taking text before first '?'"""
    return message.split("?")[0] + "?" if "?" in message else message

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

# --- Main App Logic ---
def main():
    st.set_page_config(page_title="Resume Builder", layout="centered")
    st.title("📝 Professional Resume Builder")
    
    # Display chat history
    for msg in st.session_state.chat_history[1:]:
        st.chat_message(msg["role"]).write(msg["content"])

    # Generate next question if needed
    if not st.session_state.resume_ready and len(st.session_state.chat_history) % 2 == 1:
        with st.spinner("Preparing next question..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                new_question = enforce_single_question(response.choices[0].message.content)
                st.session_state.chat_history.append({"role": "assistant", "content": new_question})
                if "RESUME READY" in new_question:
                    st.session_state.resume_ready = True
                st.session_state.current_input = ""
                st.session_state.needs_rerun = True
            except Exception as e:
                st.error(f"Error: {e}")

    # Handle user input
    if not st.session_state.resume_ready:
        user_input = st.text_input(
            "Your answer:", 
            key="user_input",
            value=st.session_state.current_input
        )
        
        if st.button("Submit"):
            if user_input.strip():
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.current_input = ""
                st.session_state.needs_rerun = True

    # Generate resume when ready
    else:
        st.success("✅ Resume ready!")
        with st.spinner("Generating resume..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        *st.session_state.chat_history,
                        {"role": "user", "content": "Generate markdown resume with: Contact, Summary, Experience, Education, Skills"}
                    ]
                )
                st.session_state.resume_md = response.choices[0].message.content
                st.markdown(st.session_state.resume_md)
                
                # PDF Generation
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    markdown_to_pdf(st.session_state.resume_md, tmp.name)
                    with open(tmp.name, "rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            f.read(),
                            "resume.pdf",
                            "application/pdf"
                        )
                    os.unlink(tmp.name)
                
                # Markdown Download
                st.download_button(
                    "⬇️ Download Markdown",
                    st.session_state.resume_md,
                    "resume.md",
                    "text/markdown"
                )
                
            except Exception as e:
                st.error(f"Generation error: {e}")

        if st.button("🔄 Start Over"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.needs_rerun = True

# --- Run Logic ---
if __name__ == "__main__":
    main()
    if st.session_state.needs_rerun:
        st.session_state.needs_rerun = False
        st.rerun()
