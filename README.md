# Zomato Gen AI Internship Assignment: Restaurant Data Scraper & RAG Chatbot

## Project Overview

This project implements an end-to-end Generative AI solution combining web scraping with a Retrieval Augmented Generation (RAG) chatbot. The goal is to allow users to ask natural language questions about restaurant menus and receive accurate, contextual responses based on scraped data. This addresses the challenge of finding specific menu details (like dietary options, prices, or item descriptions) that are often difficult to surface through traditional search methods.

## Features

*   **Web Scraping:** Collects menu data from multiple restaurant sources (using both static HTML parsing and Selenium for dynamic sites).
*   **Knowledge Base:** Processes and stores scraped data (item names, descriptions, prices, categories, basic tags) in a ChromaDB vector database using sentence embeddings (`all-MiniLM-L6-v2`).
*   **RAG Chatbot:**
    *   Retrieves relevant menu items from the knowledge base based on user queries.
    *   Uses a powerful local language model (CapybaraHermes-Mistral-7B GGUF via `llama-cpp-python`) to generate natural language answers based *only* on the retrieved context.
    *   Handles queries about item availability, details, prices, and basic dietary information (Veg/Non-Veg).
    *   Provides informative responses when information cannot be found in the current context.
*   **Simple UI:** A Streamlit web application provides an easy-to-use chat interface.

## Architecture

The system follows this general data flow:

1.  **Scraping:** Python scripts in the `scraper/` directory fetch data from target restaurant websites (Punjab Grill, Oakaz, Dominos, Subway, McDonalds) using `requests`/`BeautifulSoup` or `Selenium`/`webdriver-manager`. Workarounds (like `innerText` parsing + filter clicks) were employed for complex dynamic sites (Dominos, McDonalds).
2.  **Data Storage:** Raw scraped data is saved as JSON files in the `data/` directory.
3.  **Knowledge Base Creation:** The `knowledge_base/create_kb.py` script loads the JSON files, cleans/standardizes the data (including price conversion and tag generation), creates text chunks per menu item, generates embeddings using `sentence-transformers`, and indexes them into a persistent ChromaDB database stored in `knowledge_base/chroma_db_menu/`.
4.  **RAG Chatbot:**
    *   The Streamlit UI (`app.py`) takes user input.
    *   The core logic in `chatbot_app.py` is invoked.
    *   The user query is embedded (implicitly by ChromaDB).
    *   ChromaDB is queried to retrieve the top-K relevant menu item chunks (documents).
    *   A detailed prompt containing instructions, the retrieved context, and the user query is constructed.
    *   The local GGUF LLM (`llama-cpp-python`) generates a response based *only* on the prompt.
    *   The response is displayed in the Streamlit UI.

## Setup Instructions

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/Bhuvika-Agrawal/Zomato-Assignment.git
    cd Zomato-Assignment 
    ```
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate Virtual Environment:**
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`
4.  **Install Dependencies:** Ensure you have C++ build tools installed if `llama-cpp-python` fails.
    ```bash
    pip install -r requirements.txt
    ```
5.  **Download LLM Model:**
    *   Download a GGUF model file (e.g., `capybarahermes-2.5-mistral-7b.Q4_K_M.gguf`) from a source like TheBloke on Hugging Face.
    *   Create a folder named `models` in the project root (`Zomato-Assignment/models/`).
    *   Place the downloaded `.gguf` file inside the `models` folder.
    *   **Important:** Update the `GGUF_MODEL_FILENAME` variable inside `chatbot_app.py` to match the exact filename you downloaded.

## Running the Application

1.  **Activate Virtual Environment:** (If not already active)
    ```bash
    .\venv\Scripts\activate 
    ```
2.  **Create the Knowledge Base:** Run the processing script once to generate the ChromaDB index from the scraped JSON data.
    ```bash
    python knowledge_base/create_kb.py
    ```
    *(This will load data, download the embedding model, and create the `knowledge_base/chroma_db_menu` folder)*
3.  **Run the Chatbot UI:**
    ```bash
    streamlit run app.py
    ```
    *   This will start the Streamlit server and should automatically open the chat interface in your web browser (usually at `http://localhost:8501`).
    *   The first time you run this after starting your machine, it will load the large LLM model, which may take some time. Subsequent runs in the same session should be faster due to caching.

## Limitations & Challenges

*   **Scraping Dynamic Sites:** Scraping heavily JavaScript-driven sites (Dominos, McDonalds) proved challenging. Workarounds using `innerText` parsing and filter clicks were implemented, resulting in less structured and potentially noisy/incomplete data compared to static site scraping.
*   **Data Completeness:** Location-specific data (address, hours, precise pricing) and detailed features (allergens, spice levels) were often unavailable on the scraped menu pages or difficult to extract reliably across all sites.
*   **Retrieval Accuracy:** The RAG system's ability to answer depends on retrieving the correct context. For some queries, the current embedding model (`all-MiniLM-L6-v2`) may not retrieve the most relevant item chunk, leading to "information not found" responses even if the data exists somewhere in the KB.
*   **LLM Generation:** While CapybaraHermes is capable, it's running locally on CPU and response generation might be slow. Answers are based strictly on potentially noisy retrieved context and may sometimes be overly simple or slightly misinterpret complex queries.
*   **Conversation History:** Not implemented in this version. Each query is treated independently.

## Future Improvements

*   Implement more robust Selenium scrapers using explicit waits and element selectors for dynamic sites.
*   Scrape location-specific data where possible.
*   Extract richer features (allergens, spice levels) using more advanced parsing or potentially OCR/image analysis if needed.
*   Experiment with different embedding models or fine-tuning for better retrieval accuracy.
*   Explore larger LLMs (if hardware permits) or different prompting techniques for more nuanced generation.
*   Add conversation history management.
*   Implement more sophisticated data cleaning for the scraped JSON files.
