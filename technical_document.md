# Technical Documentation: Restaurant Menu RAG Chatbot

**Zomato Gen AI Internship Assignment**
**Your Name** 
**Date**

## 1. Introduction

This document details the technical implementation of the Restaurant Menu RAG Chatbot, developed as part of the Zomato Gen AI Internship assignment. The system aims to answer user queries about restaurant menus by combining web scraping techniques with a Retrieval-Augmented Generation (RAG) architecture utilizing open-source language models.

## 2. System Architecture

The system consists of several key components:

1.  **Web Scrapers:** Python scripts responsible for collecting data from target restaurant websites. Different techniques were employed based on site structure (static vs. dynamic).
2.  **Data Storage:** Scraped menu information is stored in structured JSON files (`data/` directory).
3.  **Knowledge Base Creation Script:** (`knowledge_base/create_kb.py`) Processes the raw JSON data, cleans and standardizes it, generates text chunks, computes embeddings, and indexes the data into a vector database.
4.  **Vector Database:** ChromaDB is used as a persistent vector store (`knowledge_base/chroma_db_menu/`) holding the embeddings and associated metadata/text chunks.
5.  **RAG Chatbot Logic:** (`chatbot_app.py`) Contains the core RAG pipeline:
    *   Loads the ChromaDB knowledge base.
    *   Loads the local GGUF Language Model (LLM).
    *   Takes a user query, embeds it (implicitly via ChromaDB's embedding function).
    *   Retrieves relevant text chunks (context) from ChromaDB.
    *   Constructs a detailed prompt including instructions, context, and the query.
    *   Calls the LLM to generate a response based *only* on the prompt.
6.  **User Interface:** (`app.py`) A simple web application built with Streamlit provides a chat interface for users to interact with the RAG chatbot.

**Data Flow:**
*Websites -> Scrapers -> Raw JSON Files -> KB Creation Script -> ChromaDB Vector Store -> Chatbot Logic (Retrieval) -> LLM (Generation) -> Streamlit UI -> User*

## 3. Implementation Details & Design Decisions

### 3.1. Web Scraping Component (`scraper/`)

*   **Target Restaurants:** Punjab Grill, Oakaz, Dominos, Subway, McDonalds.
*   **Libraries Used:**
    *   `requests`: For fetching HTML from static websites (Punjab Grill, CCD, Indian Accent).
    *   `BeautifulSoup4` (`bs4` with `lxml` parser): For parsing static HTML content.
    *   `selenium` & `webdriver-manager`: For controlling a Chrome browser to handle dynamic JavaScript-driven websites (Dominos, McDonalds workarounds).
*   **Scraping Strategies & Challenges:**
    *   **Static Sites (Punjab Grill, CCD, Indian Accent):** Relatively straightforward. Identified key HTML tags/classes for categories, items, names, prices, descriptions using CSS selectors. Data quality is generally good.
    *   **Dynamic Sites (Dominos, McDonalds):** Proved significantly challenging due to JavaScript rendering, location prompts, and complex DOM structures. Initial attempts using robust Selenium selectors and waits faced synchronization issues and timeouts under the project deadline.
    *   **Workaround Implemented (Dominos, McDonalds):** Adopted a less robust but functional workaround using Selenium to automate filter/category *clicks* and then extracting data using `driver.execute_script("return document.body.innerText;")`. This relies heavily on the specific text layout and line indexing observed during testing.
        *   *Limitations:* This method is fragile to layout changes, struggles with inconsistent formatting, cannot reliably extract descriptions or structured tags (like veg/non-veg), and resulted in significant data noise/redundancy, especially for McDonalds combos/offers being parsed as individual items. Veg/Non-Veg status for these was inferred based *only* on the filter clicked during scraping.
    *   **Data Output:** Each scraper saves its results to a separate JSON file in the `data/` directory. Structures vary based on the scraping method (flat list vs. category/filter nesting).
*   **Assumptions:** Assumed generic menus for sites not strictly enforcing location, used workarounds for dynamic sites. Did not deeply scrape contact/hours due to variability and site complexity.

### 3.2. Knowledge Base Creation (`knowledge_base/create_kb.py`)

*   **Input:** Reads JSON files from the `data/` directory for the 5 target restaurants.
*   **Data Loading & Consolidation:** Includes logic to handle the different JSON structures produced by the various scrapers (flat lists, nested category/filter dictionaries). Standardizes extracted items into a common format.
*   **Data Cleaning:**
    *   **Price:** Uses regex (`re.search(r'(\d[\d,.]*)', ...)`) to extract numeric values from price strings (e.g., "Rs.109", "₹ 200/-") and converts to float.
    *   **Tags:** Implements a `standardize_tags` function to create a list of relevant tags (e.g., "Vegetarian", "Non-Vegetarian", "Beverage", "Side", "Dessert"). It prioritizes explicit tags found during scraping, then uses filter info from workarounds, category names, and finally keyword inference as fallbacks.
*   **Chunking Strategy:** One document chunk per unique menu item. Each chunk is a formatted string containing key details: `"Restaurant: [Name], Category: [Cat], Item: [ItemName], Price: [Price], Tags: [Tags], Description: [Desc]"`. This keeps item-specific information together.
*   **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`. Chosen for its balance of performance, speed, and small size, suitable for running locally and freely available via Hugging Face. Used via ChromaDB's `SentenceTransformerEmbeddingFunction`.
*   **Vector Store:** `ChromaDB`. Chosen for its ease of setup, persistent storage (saves DB to disk in `knowledge_base/chroma_db_menu/`), and integration with Sentence Transformers embedding functions. Data is added in batches for efficiency. Collection name: `restaurant_menus`.

### 3.3. RAG Chatbot (`chatbot_app.py`)

*   **Architecture:** Implements the standard Retrieve-Augment-Generate pattern.
*   **Retrieval:**
    *   Uses the loaded ChromaDB `collection`.
    *   Takes the user query text.
    *   Calls `collection.query(query_texts=[query], n_results=top_k, ...)` which implicitly uses the `all-MiniLM-L6-v2` embedding function to find the `top_k` (default 5) most semantically similar document chunks from the indexed menu items.
    *   Extracts the `documents` (text chunks) from the results to form the context.
*   **Augmentation (Prompt Engineering):**
    *   A detailed prompt template is used, specifically designed for instruction-following models like Mistral/Llama variants.
    *   It uses `[INST] ... [/INST]` tags.
    *   Includes CRITICAL INSTRUCTIONS emphasizing answering *only* from the provided context and stating when information is not found.
    *   Injects the retrieved `context` and the `User Question`.
*   **Generation:**
    *   **LLM:** Uses a quantized GGUF model (`CapybaraHermes-2.5-Mistral-7B-GGUF` recommended, path configurable via `GGUF_MODEL_FILENAME`). Chosen as a powerful, freely available model capable of good instruction following that can run locally on CPU (albeit potentially slowly) via `llama-cpp-python`. This avoids restricted paid APIs and meets hardware constraints.
    *   **Library:** `llama-cpp-python` is used to load and run the GGUF model efficiently.
    *   **Parameters:** Uses standard generation parameters (`max_tokens`, `stop` sequences, `temperature`) to control the output. `echo=False` prevents repeating the prompt.
*   **Query Handling:** Handles different query types implicitly through semantic retrieval and LLM instruction following (item details, prices, tags).
*   **Edge Cases:** Includes logic to return a specific message if ChromaDB finds no relevant documents. The prompt explicitly instructs the LLM to state when information isn't in the retrieved context. Basic out-of-scope filtering is not explicitly implemented but could be added.
*   **Conversation History:** Not implemented due to time constraints. Each query is handled independently.

### 3.4. User Interface (`app.py`)

*   **Framework:** Streamlit. Chosen for its simplicity and speed in creating interactive web UIs directly from Python.
*   **Functionality:**
    *   Displays a title and caption.
    *   Uses `st.session_state` to maintain basic chat history within a single session.
    *   Displays past messages using `st.chat_message`.
    *   Provides a text input box (`st.chat_input`) for user queries.
    *   On submission, calls the `get_rag_response` function from `chatbot_app.py`.
    *   Shows a loading spinner (`st.spinner`) while waiting for the response.
    *   Displays the bot's response.
*   **Model Loading:** Uses `@st.cache_resource` to load the ChromaDB collection and the Llama model once per session, preventing slow reloads on every user interaction.

## 4. Challenges Faced & Solutions Implemented

*   **Challenge:** Scraping dynamic websites (Dominos, McDonalds) with complex JavaScript rendering, location requirements, and potentially anti-scraping measures.
    *   **Solution/Workaround:** Initial attempts with robust Selenium selectors/waits were time-consuming and faced synchronization issues. Switched to a pragmatic workaround combining Selenium clicks (for filters/categories) with less reliable `innerText` parsing, specifically tailoring the parsing logic for each site. **Acknowledged Limitation:** This resulted in noisy and incomplete data for these restaurants.
*   **Challenge:** Handling diverse JSON structures produced by different scraping methods.
    *   **Solution:** Implemented conditional logic in `create_kb.py` to detect the structure (flat list vs. various nested dictionaries) based on key names and data types, allowing consolidation into a standard format.
*   **Challenge:** Inconsistent or missing data points (location, hours, specific tags like allergens/spice).
    *   **Solution:** Focused on extracting core available data (name, desc, price, category). Used inference and keyword matching in `standardize_tags` to generate basic tags (Veg/Non-Veg, Beverage, Side) where explicit tags were missing. Acknowledged missing data in documentation.
*   **Challenge:** Ensuring the LLM answers *only* from retrieved context and handles "not found" cases.
    *   **Solution:** Employed a strong, explicit prompt with clear instructions for the LLM (using Mistral/Llama instruct format). Added logic in the RAG function to return a specific message if ChromaDB retrieval yields no results. Tested and iterated on the prompt.
*   **Challenge:** Running capable LLMs locally without specialized hardware or paid APIs.
    *   **Solution:** Utilized a quantized GGUF version of a strong open-source model (CapybaraHermes-Mistral-7B) via the `llama-cpp-python` library, enabling efficient CPU-based inference.
*   **Challenge:** Environment/Dependency issues (`Side-by-side configuration`).
    *   **Solution:** Used `webdriver-manager` to simplify driver setup. Recreated virtual environment and used force-reinstall for problematic packages.

## 5. Future Improvement Opportunities

*   **Improve Scrapers:** Replaceing `innerText` workarounds with robust Selenium scrapers using explicit waits and reliable element selectors for dynamic sites (Dominos, McD, Pizza Hut, etc.).
*   **Richer Data:** Enhanceing scrapers to capture location-specific details (hours, address, phone), price variations (size/crust), and more granular tags (allergens, spice levels, cuisine type).
*   **Data Cleaning:** Implementing more sophisticated post-processing/cleaning for scraped data to reduce noise before indexing.
*   **Retrieval Enhancement:** Experimenting with different embedding models (e.g., `multi-qa` models), chunking strategies (e.g., splitting long descriptions), or fine-tuning embeddings for better relevance. Explore hybrid search (keyword + vector).
*   **Advanced RAG:** Implementing techniques like query rewriting, conversational memory (history), or using metadata during retrieval/generation.
*   **LLM Exploration:** Testing larger local models (if hardware permits) or explore techniques like prompt chaining for more complex reasoning or comparisons.
*   **UI Enhancements:** Adding features like displaying source snippets, handling multiple results, or user feedback mechanisms.
*   **Error Handling:** Implementing more granular error handling and logging throughout the pipeline.