import json
from pathlib import Path
import re
import sys # For traceback
import traceback
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm # For progress bars



# Defining the directory structure relative to this script
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data'
KB_DIR = PROJECT_ROOT / 'knowledge_base' 
CHROMA_DB_PATH = str(KB_DIR / 'chroma_db_menu') # Path to store ChromaDB files as string
CONSOLIDATED_JSON_PATH = DATA_DIR / 'consolidated_menu_items.json' # Path to input file

# Defining the input JSON files for the 5 specified restaurants
INPUT_FILES = {
    "Punjab Grill": DATA_DIR / "punjab_grill_menu.json",
    "Oakaz": DATA_DIR / "oakaz_menu_innertext.json", 
    "Dominos": DATA_DIR / "dominos.json", 
    "Subway": DATA_DIR / "subway_menu_unofficial_cleaned.json", 
    "McDonalds": DATA_DIR / "macd.json" 
}

# --- Helper Functions (clean_price, standardize_tags) ---

def clean_price(price_str):
    if price_str is None: return None
    if isinstance(price_str, (int, float)): return float(price_str)
    if not isinstance(price_str, str): return None
    match = re.search(r'(\d[\d,]*\.?\d*)', price_str)
    if match:
        num_str = match.group(1).replace(',', '')
        try: return float(num_str)
        except ValueError: return None
    return None

def standardize_tags(item_data, restaurant_name, category_name):
    tags = []
    if "special_tags" in item_data and isinstance(item_data["special_tags"], list):
        filtered_tags = [t for t in item_data["special_tags"] if t not in ['Veg Only', 'Non Veg Only', 'Veg', 'Non-Veg', 'desserts and bevrages']]
        tags.extend(filtered_tags)
    if "is_vegetarian" in item_data:
         if item_data["is_vegetarian"] is True and "Vegetarian" not in tags: tags.append("Vegetarian")
         elif item_data["is_vegetarian"] is False and "Non-Vegetarian" not in tags: tags.append("Non-Vegetarian")
    if not any(t in ["Vegetarian", "Non-Vegetarian"] for t in tags) and "filter_mode" in item_data:
        mode = item_data["filter_mode"]
        if mode == 'Veg' or mode == 'Veg Only': tags.append("Vegetarian")
        elif mode == 'Non-Veg' or mode == 'Non Veg Only': tags.append("Non-Vegetarian")
    is_food_tagged = any(t in ["Vegetarian", "Non-Vegetarian"] for t in tags)
    if not is_food_tagged:
        lower_cat = str(category_name).lower()
        if "bev" in lower_cat or "drink" in lower_cat: tags.append("Beverage")
        elif "dessert" in lower_cat or "cake" in lower_cat or "cookie" in lower_cat: tags.append("Dessert")
        elif "side" in lower_cat or "bread" in lower_cat or "dip" in lower_cat or "more" in lower_cat or "fries" in lower_cat: tags.append("Side")
        elif "pasta" in lower_cat: tags.append("Pasta")
        elif "combo" in lower_cat or "meal" in lower_cat or "feast" in lower_cat: tags.append("Combo/Meal")
        elif "wrap" in lower_cat or "roll" in lower_cat: tags.append("Wrap/Roll")
    is_other_tagged = any(t in ["Beverage", "Dessert", "Side", "Pasta", "Combo/Meal", "Wrap/Roll"] for t in tags)
    if not is_food_tagged and not is_other_tagged:
         item_name_lower = str(item_data.get("item_name","")).lower()
         if any(kw in item_name_lower for kw in ["chicken", "egg", "b.m.t", "tuna", "meatball", "keema", "turkey", "steak", "lamb", "mutton", "fish", "prawn", "pepperoni"]): tags.append("Non-Vegetarian (Inferred)")
         elif any(kw in item_name_lower for kw in ["paneer", "aloo", "veg", "corn", "peas", "bean", "shammi", "chilli", "hara bhara", "mushroom", "gobhi", "subz", "patty"]): tags.append("Vegetarian (Inferred)")
    return list(set(tags))



# STEP 1: Loading and Consolidating Data

all_menu_items_raw = []
print("Starting Knowledge Base Creation...")
for restaurant_name, filepath in INPUT_FILES.items():
    print(f"\nProcessing file: {filepath.name} for Restaurant: {restaurant_name}")
    if not filepath.is_file(): print(f"  ERROR: File not found: {filepath}. Skipping."); continue
    items_to_process = []; structure_found = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
        menu_content_list = data.get("menu")
        if isinstance(menu_content_list, list):
             if menu_content_list and isinstance(menu_content_list[0], dict) and ("item_name" in menu_content_list[0] or "name" in menu_content_list[0]):
                 print("  Detected structure: Flat 'menu' list.")
                 for item in menu_content_list:
                      if isinstance(item, dict): item['category'] = item.get('category', 'Unknown'); items_to_process.append(item)
                 structure_found = True
        elif "menu_by_category_filter" in data and isinstance(data["menu_by_category_filter"], dict):
             print("  Detected structure: 'menu_by_category_filter' nested dict (Dominos).")
             menu_content = data["menu_by_category_filter"]
             for category, filter_dict in menu_content.items():
                 if isinstance(filter_dict, dict):
                     for filter_mode, item_list in filter_dict.items():
                         if isinstance(item_list, list):
                             for item in item_list:
                                 if isinstance(item, dict): item['category'] = item.get('category', category); item['filter_mode'] = item.get('filter_mode', filter_mode); items_to_process.append(item)
             structure_found = True
        elif "menu_details" in data and isinstance(data.get("menu_details"), dict):
             menu_content = data["menu_details"]; first_cat_value = next(iter(menu_content.values()), None)
             if isinstance(first_cat_value, dict) and any(k in ["Veg Only", "Non Veg Only", "desserts and bevrages"] for k in first_cat_value.keys()):
                  print("  Detected structure: 'menu_details' > Category > Filter dict (McD/Oakaz).")
                  for category, filter_dict in menu_content.items():
                      if isinstance(filter_dict, dict):
                          for filter_mode, item_list in filter_dict.items():
                              if isinstance(item_list, list):
                                  for item in item_list:
                                      if isinstance(item, dict): item['category'] = item.get('category', category); item['filter_mode'] = item.get('filter_mode', filter_mode); items_to_process.append(item)
                  structure_found = True
             elif isinstance(first_cat_value, list):
                  print("  Detected structure: 'menu_details' > Category > List [Items] (Punjab Grill).")
                  for category, item_list in menu_content.items():
                      if isinstance(item_list, list):
                           for item in item_list:
                                if isinstance(item, dict): item['category'] = category; items_to_process.append(item)
                  structure_found = True
             elif isinstance(first_cat_value, dict):
                  print("  Detected structure: 'menu_details' > Category > ItemName dict (Subway Int).")
                  for category, items_dict in menu_content.items():
                      if isinstance(items_dict, dict):
                           for item_name, item_info in items_dict.items():
                               if isinstance(item_info, dict): item_info['item_name'] = item_name; item_info['category'] = category; items_to_process.append(item_info)
                  structure_found = True
        elif "menu" in data and isinstance(data["menu"], dict) and ("Veg" in data["menu"] or "Non-Veg" in data["menu"]):
             print("  Detected structure: Cleaned Subway ('menu' > V/NV > ItemName).")
             menu_content = data["menu"]
             for veg_nonveg_key, items_dict in menu_content.items():
                 if isinstance(items_dict, dict):
                     for item_name, item_info in items_dict.items():
                         if isinstance(item_info, dict):
                             item_info['item_name'] = item_name; item_info['category'] = item_info.get('original_category', 'Unknown')
                             if veg_nonveg_key == "Veg": item_info['is_vegetarian'] = True
                             elif veg_nonveg_key == "Non-Veg": item_info['is_vegetarian'] = False
                             items_to_process.append(item_info)
             structure_found = True
        if not structure_found: print(f"  ERROR: Could not find recognizable menu structure in {filepath.name}"); continue
        items_added = 0
        for item in items_to_process:
            item_name = item.get("item_name") or item.get("name"); category = item.get("category") or "Unknown"
            if not item_name or category == item_name: continue
            price_raw = item.get("price"); price_clean = clean_price(price_raw)
            description = item.get("description", "")
            if isinstance(description, str):
                if price_raw and description.strip() == str(price_raw).strip(): description = ""
                if description.startswith("Image from Swiggy"): description = ""
            category = str(category) if category is not None else "Unknown"
            tags = standardize_tags(item, restaurant_name, category)
            standardized_item = {"restaurant_name": restaurant_name, "category": category, "item_name": item_name.strip(), "description": description.strip(), "price": price_clean, "special_tags": tags }
            all_menu_items_raw.append(standardized_item); items_added += 1 # Appending to raw list first
        if items_added > 0: print(f"  Successfully processed and standardized {items_added} items.")
        elif structure_found: print(f"  Structure found, but 0 valid items were processed/standardized.")
    except json.JSONDecodeError: print(f"  ERROR: Invalid JSON file: {filepath}. Skipping.")
    except Exception as e: print(f"  ERROR: An unexpected error occurred processing {filepath.name}: {e}"); traceback.print_exc()

# --- Final Duplicate Check ---
print(f"\n--------------------------------------------------")
final_unique_items = []
seen_keys = set()
duplicates_skipped = 0
for item in all_menu_items_raw: # Processing the raw combined list
     key = (item.get('restaurant_name'), str(item.get('category','Unknown')).strip().lower(), str(item.get('item_name','')).strip().lower(), item.get('price'), tuple(sorted(item.get('special_tags',[]))) )
     if key not in seen_keys: final_unique_items.append(item); seen_keys.add(key)
     else: duplicates_skipped += 1
print(f"Consolidated {len(final_unique_items)} unique menu items (removed {duplicates_skipped} duplicates).")
if not final_unique_items:
    print("ERROR: No items were consolidated. Cannot proceed with embedding.")
    sys.exit(1) # Exit if no data

# --- Save the consolidated list ---
consolidated_output_path = DATA_DIR / 'consolidated_menu_items.json'
print(f"Saving consolidated items to {consolidated_output_path}")
try:
    with open(consolidated_output_path, 'w', encoding='utf-8') as f:
        json.dump(final_unique_items, f, indent=2, ensure_ascii=False)
    print("Consolidated data saved.")
except Exception as e: print(f"Error saving consolidated data: {e}")




# STEP 2: Chunking (One item per chunk)

print("\nCreating text chunks for embedding...")
documents = [] # List of text strings to be embedded
metadatas = [] # List of metadata dictionaries corresponding to documents
ids = []       # List of unique IDs for each document

for i, item in enumerate(tqdm(final_unique_items, desc="Chunking Items")):
    # Creating a readable string representation of the item
    price_str = f"Price: {item['price']}" if item['price'] is not None else "Price: N/A"
    tags_str = f"Tags: {', '.join(item['special_tags'])}" if item['special_tags'] else "Tags: None"
    desc_str = f"Description: {item['description']}" if item['description'] else ""

    chunk_text = (
        f"Restaurant: {item['restaurant_name']}. "
        f"Category: {item['category']}. "
        f"Item: {item['item_name']}. "
        f"{price_str}. "
        f"{tags_str}. "
        f"{desc_str}"
    )
    documents.append(chunk_text)

    # Storing original structured data as metadata
    # Ensure all metadata values are basic types (str, int, float, bool)
    metadata = item.copy() # Start with a copy
    # Convert tags list to a string for ChromaDB compatibility if needed, or keep as list if supported
    metadata['special_tags'] = ", ".join(metadata.get('special_tags', [])) # Example: comma-separated string
    # Ensure price is string or None (ChromaDB metadata prefers simple types)
    metadata['price'] = str(metadata['price']) if metadata['price'] is not None else ""

    metadatas.append(metadata)
    # Creating a unique ID for each item chunk
    ids.append(f"item_{i}_{item['restaurant_name'].replace(' ','_')}_{item['item_name'][:20].replace(' ','_')}")

print(f"Created {len(documents)} text chunks.")
# STEP 3 & 4: Embedding & Indexing (Using ChromaDB)
print("\nInitializing ChromaDB and Embedding Model...")
# Using a HuggingFace embedding function through ChromaDB's utility

hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


# This will create files in the 'chroma_db_menu' folder
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

collection_name = "restaurant_menus"
print(f"Getting or creating Chroma collection: {collection_name}")

collection = chroma_client.get_or_create_collection(
    name=collection_name,
    embedding_function=hf_ef 

    )

# --- Add documents to ChromaDB ---


batch_size = 100 # Process 100 items at a time
num_items = len(documents)
print(f"Adding {num_items} items to ChromaDB in batches of {batch_size}...")

for i in tqdm(range(0, num_items, batch_size), desc="Indexing Batches"):
    batch_ids = ids[i : i + batch_size]
    batch_documents = documents[i : i + batch_size]
    batch_metadatas = metadatas[i : i + batch_size]

    try:
         # Add batch to the collection
         collection.add(
             ids=batch_ids,
             documents=batch_documents,
             metadatas=batch_metadatas
         )
    except Exception as chroma_error:
         print(f"\nError adding batch {i//batch_size + 1} to ChromaDB: {chroma_error}")

         # print("Attempting to add items individually...")
         # for j in range(len(batch_ids)):
         #      try:
         #           collection.add(ids=[batch_ids[j]], documents=[batch_documents[j]], metadatas=[batch_metadatas[j]])
         #      except Exception as item_error:
         #           print(f"  Failed to add item ID: {batch_ids[j]}, Error: {item_error}")
         #           print(f"  Item Data: {batch_documents[j]}")
         #           print(f"  Item Metadata: {batch_metadatas[j]}")


print(f"\n--------------------------------------------------")
print(f"Knowledge Base Creation Complete!")
print(f"Indexed {collection.count()} items in ChromaDB collection '{collection_name}'.")
print(f"Database stored at: {CHROMA_DB_PATH}")
print("--------------------------------------------------")