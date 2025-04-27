import time
import json
from pathlib import Path
import re
import chromadb
from chromadb.utils import embedding_functions
# --- Using LlamaCPP ---
from llama_cpp import Llama
import sys
import traceback

# --- Configuration ---
CURRENT_DIR = Path(__file__).resolve().parent # Assumes chatbot_app.py is in project root
KB_DIR = CURRENT_DIR / 'knowledge_base'
CHROMA_DB_PATH = str(KB_DIR / 'chroma_db_menu')
COLLECTION_NAME = "restaurant_menus"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# --- GGUF Model Configuration ---
MODEL_DIR = CURRENT_DIR / 'models'

GGUF_MODEL_FILENAME = "capybarahermes-2.5-mistral-7b.Q4_K_M.gguf" 
MODEL_PATH = str(MODEL_DIR / GGUF_MODEL_FILENAME)



# --- Loading Existing Knowledge Base (ChromaDB) ---

print("Loading Knowledge Base from ChromaDB...")
collection = None # Initialize
llm = None # Initialize
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)
    collection = chroma_client.get_collection(name=COLLECTION_NAME, embedding_function=hf_ef)
    print(f"Loaded ChromaDB collection '{COLLECTION_NAME}' with {collection.count()} items.")
except Exception as e:
    print(f"Error loading ChromaDB collection: {e}")
    print(f"Please ensure 'create_kb.py' ran successfully and the database exists at {CHROMA_DB_PATH}.")




# --- Loading GGUF Language Model using llama-cpp-python ---

print(f"Loading GGUF Model: {MODEL_PATH}...")
if collection is not None: # Only load LLM if KB loaded
    if not Path(MODEL_PATH).is_file():
        print(f"ERROR: Model file not found at {MODEL_PATH}")
        print(f"Please download the '{GGUF_MODEL_FILENAME}' GGUF model and place it in the '{MODEL_DIR}' folder.")
    else:
        try:
            llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=2048, n_threads=None, n_gpu_layers=0, verbose=False
            )
            print("GGUF Language Model loaded successfully.")
        except Exception as e:
            print(f"Error loading GGUF Language Model: {e}")
            print("Ensure 'llama-cpp-python' is installed correctly and the model path is correct.")
            traceback.print_exc()



# --- RAG Core Function ---
def get_rag_response(query, top_k=5):
    """Performs RAG using LlamaCPP model."""
    # Checking if models loaded correctly before proceeding
    if llm is None or collection is None:
         return "Error: Chatbot components (LLM or KB) not loaded properly."

    print(f"\nProcessing query: {query}")

    # 1. Retrieval
    print(f"  Retrieving top {top_k} relevant documents...")
    try:
        results = collection.query(query_texts=[query], n_results=top_k, include=['documents'])
    except Exception as e: print(f"  Error querying ChromaDB: {e}"); return "Sorry, error retrieving info."

    if not results or not results.get('documents') or not results['documents'][0]:
        print("  No relevant documents found."); return "I couldn't find specific info in the menus."

    context_list = results['documents'][0]
    context = "\n\n".join(context_list)
    # print(f"  Context:\n{context}\n--------------------") # Debug Context

    # 2. Prompt Construction 
    prompt = f"""[INST] **CRITICAL INSTRUCTIONS:**
1. Your task is to answer the user's question about restaurant menus.
2. Base your answer **STRICTLY AND ONLY** on the information present in the 'CONTEXT' section below.
3. **DO NOT** use any outside knowledge or make assumptions.
4. If the exact item or information requested in the 'USER QUESTION' is **NOT FOUND** within the 'CONTEXT', you MUST respond with: "I cannot find information about that in the provided menu details."
5. Be concise and directly answer the question using details from the context if available.

**CONTEXT:**
{context}

**USER QUESTION:** {query} [/INST]
**ANSWER:**"""

    # 3. Generation using llama-cpp-python
    print("  Generating response...")
    response = "Sorry, I encountered an error generating a response."
    try:
        output = llm(prompt, max_tokens=250, stop=["</s>", "[INST]", "User Question:", "\n\n"], temperature=0.7, top_p=0.9, echo=False)
        if output and 'choices' in output and len(output['choices']) > 0 and 'text' in output['choices'][0]:
             response = output['choices'][0]['text'].strip()
             if response.startswith("[/INST]"): response = response[len("[/INST]"):].strip()
             if response.startswith("ANSWER:"): response = response[len("ANSWER:"):].strip()
#              print(f"  Raw LLM Output: {response}")
        else: print(f"  Warning: Unexpected output format from llama_cpp: {output}")
    except Exception as e: print(f"  Error during response generation: {e}"); traceback.print_exc()

    return response

# --- Interaction Loop 
# if __name__ == "__main__":
#     print("\nRestaurant Menu Chatbot Initialized (using LlamaCPP). Type 'quit' to exit.")
#     if llm is None or collection is None:
#          print("Cannot start interaction loop: LLM or KB failed to load.")
#     else:
#          while True:
#              try:
#                  user_query = input("You: ")
#                  if user_query.lower() == 'quit': break
#                  if not user_query.strip(): continue
#                  bot_response = get_rag_response(user_query, top_k=5)
#                  print(f"Bot: {bot_response}")
#              except EOFError: print("\nExiting..."); break
#              except KeyboardInterrupt: print("\nExiting..."); break