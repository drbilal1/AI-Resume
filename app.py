import streamlit as st
import openai
from fpdf import FPDF
import tempfile
import os

# --- Configuration ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it to your app's secrets.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": "You are a friendly and professional resume assistant. Your goal is to collect all necessary information from the user to build a comprehensive resume. Ask clear, concise questions one at a time. Once you have enough information, indicate that the resume is ready to be generated."}]
if "resume_ready" not in st.session_state:
    st.session_state.resume_ready = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "last_assistant_message" not in st.session_state:
    st.session_state.last_assistant_message = ""
if "resume_md" not in st.session_state:
    st.session_state.resume_md = ""

# --- Helper Functions ---
def markdown_to_pdf(markdown_text, filename):
    """Convert markdown text to a PDF file"""
    # Create a temporary file to store markdown
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(markdown_text)
        md_path = f.name
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Read markdown file and add to PDF (simplified conversion)
    with open(md_path, "r") as f:
        for line in f:
            # Basic formatting - you can enhance this
            if line.startswith("# "):
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=line[2:].strip(), ln=True)
                pdf.set_font("Arial", size=12)
            elif line.startswith("## "):
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=line[3:].strip(), ln=True)
                pdf.set_font("Arial", size=12)
            else:
                pdf.multi_cell(0, 10, txt=line.strip())
    
    # Save PDF to a temporary file
    pdf_path = filename
    pdf.output(pdf_path)
    
    # Clean up
    os.unlink(md_path)
    
    return pdf_path

# --- Streamlit UI ---
st.set_page_config(page_title="Smart Resume Builder", layout="centered")
st.title("📄 Smart Resume Builder")
st.write("Hello! I'm your AI resume assistant. I'll ask you a series of questions to gather information and then generate a professional resume for you.")

# --- Chat Loop ---
if not st.session_state.resume_ready:
    for msg in st.session_state.chat_history[1:]:
        if msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {msg['content']}")
        elif msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")

    if len(st.session_state.chat_history) == 1 and not st.session_state.last_assistant_message:
        with st.spinner("Thinking..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                initial_assistant_message = response.choices[0].message.content
                st.session_state.chat_history.append({"role": "assistant", "content": initial_assistant_message})
                st.session_state.last_assistant_message = initial_assistant_message 
                st.rerun()
            except openai.APIError as e:
                st.error(f"Error communicating with OpenAI: {e}")
                st.stop()

    user_input = st.text_input("Your answer:", value=st.session_state.user_input, key="user_input_widget")

    if st.button("Send", use_container_width=True):
        if user_input.strip() != "":
            st.session_state.user_input = ""
            st.session_state.last_assistant_message = ""
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("AI is thinking..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.chat_history
                    )
                    assistant_message = response.choices[0].message.content
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                    st.session_state.last_assistant_message = assistant_message

                    if "resume is ready" in assistant_message.lower() or \
                       "generating your resume" in assistant_message.lower() or \
                       "i have enough information" in assistant_message.lower():
                        st.session_state.resume_ready = True
                except openai.APIError as e:
                    st.error(f"Error communicating with OpenAI: {e}")
            
            st.rerun()

# --- Resume Generation and Display ---
else:
    st.subheader("## 📝 Your Generated Resume")
    with st.spinner("Generating your professional resume..."):
        try:
            final_resume_prompt = """Based on our conversation, please generate a full, professional resume in markdown format. 
            Include these sections:
            1. Contact Information
            2. Professional Summary
            3. Work Experience (with bullet points)
            4. Education
            5. Skills
            6. Any other relevant sections
            
            Format it clearly with proper markdown headers (## for sections, ### for subsections)."""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.chat_history + [{"role": "user", "content": final_resume_prompt}]
            )
            st.session_state.resume_md = response.choices[0].message.content
            st.markdown(st.session_state.resume_md)

            # Create PDF and offer download
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = markdown_to_pdf(st.session_state.resume_md, tmp.name)
                
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button(
                    label="📥 Download as PDF",
                    data=pdf_bytes,
                    file_name="resume.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            st.download_button(
                label="📥 Download as .txt",
                data=st.session_state.resume_md,
                file_name="resume.txt",
                mime="text/plain",
                use_container_width=True
            )

        except openai.APIError as e:
            st.error(f"Error generating resume with OpenAI: {e}")
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
    
    if st.button("🔄 Start Over", use_container_width=True):
        for key in ["chat_history", "resume_ready", "user_input", "last_assistant_message", "resume_md"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
