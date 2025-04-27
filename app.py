import streamlit as st
import sys
from pathlib import Path

# --- Adding project root to sys.path ---
# PROJECT_ROOT = Path(__file__).resolve().parent
# sys.path.append(str(PROJECT_ROOT)) 

# --- Importing the RAG function ---
# This will implicitly trigger the loading in chatbot_app.py
try:
    from chatbot_app import get_rag_response # Import only the function
    models_loaded = True


    print("Attempting to import RAG function (models load on import)...")

except ImportError as e:
     st.error(f"Error importing chatbot_app: {e}. Make sure chatbot_app.py is in the project root.")
     models_loaded = False
except Exception as e:
     st.error(f"Error initializing chatbot components during import: {e}")
     st.info("Please check the terminal logs for more details from chatbot_app.py.")
     models_loaded = False

# --- Streamlit App UI ---

st.title("🍽️ Restaurant Menu RAG Chatbot")
st.caption("Ask questions about menus from Punjab Grill, Oakaz, Dominos, Subway, and McDonalds.")

# Initializing chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Displaying previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Getting user input
prompt = st.chat_input("Ask about menu items, prices, descriptions...")

if prompt:
    # Adding user message to history and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generating and display bot response
    if models_loaded:
        with st.spinner("Thinking..."):
            # Calling the RAG function
            response = get_rag_response(prompt, top_k=5)

            with st.chat_message("assistant"):
                st.markdown(response)
            # Adding bot response to history
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
         # If import failed
         with st.chat_message("assistant"):
              st.error("Chatbot components failed to import. Cannot process query.")
         st.session_state.messages.append({"role": "assistant", "content": "Chatbot components failed to import."})