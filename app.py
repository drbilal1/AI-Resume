import streamlit as st
import openai

# --- Configuration ---
# Load OpenAI API key from Streamlit secrets. This is the recommended way to handle secrets
# in Streamlit Cloud. Make sure you have your "OPENAI_API_KEY" configured in your app's
# secrets on Streamlit Cloud.
# Accessing secrets: st.secrets["OPENAI_API_KEY"]
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it to your app's secrets.")
    st.stop() # Stop the app if API key is not found

# Initialize the OpenAI client for the new API (v1.x.x+)
# This client handles authentication and communication with the OpenAI API.
client = openai.OpenAI(api_key=api_key)

# --- Session State Initialization ---
# Initialize session state variables if they don't already exist.
# This ensures that the state persists across reruns of the Streamlit app.
if "chat_history" not in st.session_state:
    # The system message sets the persona for the AI assistant.
    # It instructs the AI to collect resume details by asking one question at a time.
    st.session_state.chat_history = [{"role": "system", "content": "You are a friendly and professional resume assistant. Your goal is to collect all necessary information from the user to build a comprehensive resume. Ask clear, concise questions one at a time. Once you have enough information, indicate that the resume is ready to be generated."}]
if "resume_ready" not in st.session_state:
    # This boolean flag controls whether the app is in chat mode or resume display mode.
    st.session_state.resume_ready = False
if "user_input" not in st.session_state:
    # Stores the current user input in the text_input widget.
    st.session_state.user_input = ""
if "last_assistant_message" not in st.session_state:
    # Stores the last message from the assistant to avoid re-generating the initial prompt repeatedly.
    st.session_state.last_assistant_message = ""

# --- Streamlit UI ---
st.set_page_config(page_title="Smart Resume Builder", layout="centered")
st.title("📄 Smart Resume Builder")
st.write("Hello! I'm your AI resume assistant. I'll ask you a series of questions to gather information and then generate a professional resume for you.")

# --- Chat Loop ---
# This block handles the conversational part of the application.
if not st.session_state.resume_ready:
    # Display chat history, starting from the second message to skip the initial system prompt.
    for msg in st.session_state.chat_history[1:]:
        if msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {msg['content']}")
        elif msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")

    # Display the initial assistant prompt if it hasn't been displayed yet
    # This prevents the initial system message from showing up repeatedly at the start.
    if len(st.session_state.chat_history) == 1 and not st.session_state.last_assistant_message:
        with st.spinner("Thinking..."):
            try:
                # Generate the first question from the AI using the new API syntax
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                initial_assistant_message = response.choices[0].message.content # Accessing content using dot notation
                st.session_state.chat_history.append({"role": "assistant", "content": initial_assistant_message})
                st.session_state.last_assistant_message = initial_assistant_message 
                st.rerun() # Rerun to display the initial message - CHANGED FROM st.experimental_rerun()
            except openai.APIError as e:
                st.error(f"Error communicating with OpenAI: {e}")
                st.stop() # Stop execution if there's an API error


    # Input from user
    # The text_input widget stores its value in st.session_state.user_input using the 'key' argument.
    user_input = st.text_input("Your answer:", value=st.session_state.user_input, key="user_input_widget")

    # Send button logic
    if st.button("Send", use_container_width=True):
        if user_input.strip() != "": # Ensure user input is not empty
            # Clear the input box after sending
            st.session_state.user_input = ""
            st.session_state.last_assistant_message = "" # Clear last assistant message to allow next prompt

            # Append user response to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("AI is thinking..."):
                try:
                    # Send the entire chat history to OpenAI to maintain context using the new API syntax
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.chat_history
                    )
                    assistant_message = response.choices[0].message.content # Accessing content using dot notation

                    # Add assistant reply to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                    st.session_state.last_assistant_message = assistant_message

                    # Check if the assistant indicates that the resume is ready
                    # This check is case-insensitive and looks for key phrases.
                    if "resume is ready" in assistant_message.lower() or \
                       "generating your resume" in assistant_message.lower() or \
                       "i have enough information" in assistant_message.lower():
                        st.session_state.resume_ready = True

                except openai.APIError as e:
                    st.error(f"Error communicating with OpenAI: {e}")
            
            st.rerun() # Rerun the app to update the display with new messages - CHANGED FROM st.experimental_rerun()

# --- Resume Generation and Display ---
# This block executes once `st.session_state.resume_ready` becomes True.
else:
    st.subheader("## 📝 Your Generated Resume")
    with st.spinner("Generating your professional resume..."):
        try:
            # Send a final prompt to the LLM to generate the resume in Markdown format using the new API syntax
            final_resume_prompt = "Based on our conversation, please generate a full, professional resume in markdown format. Include sections like Contact Information, Summary/Objective, Work Experience, Education, Skills, and any other relevant sections we discussed. Format it clearly and professionally."
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.chat_history + [{"role": "user", "content": final_resume_prompt}]
            )
            resume_md = response.choices[0].message.content # Accessing content using dot notation
            st.markdown(resume_md)

            # Optionally allow download of the resume as a text file
            st.download_button(
                label="📥 Download as .txt",
                data=resume_md,
                file_name="resume.txt",
                mime="text/plain",
                use_container_width=True
            )

        except openai.APIError as e:
            st.error(f"Error generating resume with OpenAI: {e}")
    
    # Button to start over the resume building process
    if st.button("🔄 Start Over", use_container_width=True):
        # Clear all relevant session state variables
        for key in ["chat_history", "resume_ready", "user_input", "last_assistant_message"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun() # Rerun to go back to the chat interface - CHANGED FROM st.experimental_rerun()


If you need any further modifications or additional details, feel free to let me know.
