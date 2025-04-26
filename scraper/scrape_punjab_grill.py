import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re
import time # Added import
import traceback # Added import

URL = "https://www.punjabgrill.in/punjab-grill-menu/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

# --- Define output paths ---
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
data_dir = project_root / 'data'
json_output_path = data_dir / 'punjab_grill_menu.json' # Keep original filename
data_dir.mkdir(parents=True, exist_ok=True)

# --- Data Structure (Top Level) ---
# Will contain restaurant info and nested menu details
final_output_data = {
    "restaurant_name": "Punjab Grill",

    "menu_details": {} # Changed 'menu' key, value will be dict keyed by category
}
# --- End Data Structure ---


def extract_items(list_element, category_name, is_veg):
    """Extracts items from a ul.menu-list element."""
    # Keeping the original extraction logic for item details
    items = []
    if not list_element: return items
    list_items = list_element.find_all('li', recursive=False)
    for i, li in enumerate(list_items):
        strong_tag = li.find('strong', recursive=False)
        if not strong_tag: continue
        strong_text = strong_tag.get_text(strip=True)
        description = ""
        br_tag = strong_tag.find_next_sibling('br')
        current_element = br_tag
        desc_parts = []
        while current_element := getattr(current_element, 'next_sibling', None):
             if getattr(current_element, 'name', None) in ['li', 'strong', 'img', 'noscript', 'ul']: break
             if isinstance(current_element, str) and current_element.strip():
                 desc_parts.append(current_element.strip().replace('&', '&'))
        description = " ".join(desc_parts)
        parts = strong_text.split()
        price_str = None
        name = strong_text.replace('&', '&')
        if len(parts) > 1 and parts[-1].isdigit():
            price_str = parts[-1]
            name = " ".join(parts[:-1]).strip().replace('&', '&')
        price_float = None
        if price_str:
            try:
                cleaned_price = re.sub(r'[^\d.]', '', price_str)
                price_float = float(cleaned_price)
            except ValueError:
                print(f"Warning: Could not convert price '{price_str}' for item '{name}'")
                price_float = None
        veg_status = is_veg
        special_tags = ["Vegetarian"] if is_veg else ["Non-Vegetarian"]
        # Return only item details, category will be the key in the main dict
        items.append({
            "item_name": name, "description": description, "price": price_float,
            "is_vegetarian": veg_status, "special_tags": special_tags
            # Category is implicitly known from where this list will be stored
        })
    return items

# --- Main Script ---
# Dictionary to hold menu items grouped by category
menu_by_category = {}
processed_pane_ids = set() # Avoid reprocessing duplicate panes

try:
    print(f"Fetching URL: {URL}")
    response = requests.get(URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    print(f"Status Code: {response.status_code}")
    time.sleep(1)

    soup = BeautifulSoup(response.content, 'lxml')
    print("Successfully parsed HTML. Starting extraction...")

    category_blocks = soup.select('div.appetizer')
    print(f"Found {len(category_blocks)} category blocks.")

    total_items_extracted = 0

    for block in category_blocks:
        heading_tag = block.find('h3', class_='appetizer-list-heading')
        category_name = heading_tag.get_text(strip=True).replace('&', '&') if heading_tag else "Unknown Category"

        # Initialize category in dictionary if not present
        if category_name != "Unknown Category" and category_name not in menu_by_category:
            menu_by_category[category_name] = [] # Store items in a list for this category

        tab_lists = block.find_all('div', class_='appetizer-list')
        if not tab_lists:
             if 'appetizer-list' in block.get('class', []): tab_lists = [block]
             else: continue

        for tab_list_section in tab_lists:
            nav_tabs = tab_list_section.find('ul', class_='nav-tabs')
            tab_content = tab_list_section.find('div', class_='tab-content')
            if not nav_tabs or not tab_content: continue

            tabs = nav_tabs.find_all('a', href=True)
            for tab_link in tabs:
                href = tab_link.get('href', '')
                if not href.startswith('#') or len(href) == 1: continue
                pane_id = href[1:]
                if pane_id in processed_pane_ids: continue

                is_veg = not any(pane_id.endswith(suffix) for suffix in ['tab2', 'tab2abc', 'tab2abc0', 'tab2abc1'])

                content_pane = tab_content.find('div', id=pane_id)
                if not content_pane:
                     print(f"Warning: Could not find content pane with ID: {pane_id}")
                     continue

                menu_ul = content_pane.find('ul', class_='menu-list')
                if menu_ul:
                    # Extract items for this specific pane
                    extracted_items = extract_items(menu_ul, category_name, is_veg)
                    if category_name != "Unknown Category":
                        # Append items to the list for this category
                        menu_by_category[category_name].extend(extracted_items)
                        total_items_extracted += len(extracted_items)
                    processed_pane_ids.add(pane_id)

    # --- Assign the category-structured data to the final output ---
    final_output_data['menu_details'] = menu_by_category
    print(f"\n--- Extraction Complete ---")
    print(f"Total items extracted: {total_items_extracted}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching URL {URL}: {e}")
except Exception as e:
    print(f"An unexpected error occurred during script execution: {e}")
    traceback.print_exc()

# --- Save Data to JSON ---
print("\n--- Saving Data ---")
try:
    with open(json_output_path, 'w', encoding='utf-8') as f:
        # Save the final_output_data which includes the nested menu_by_category
        json.dump(final_output_data, f, indent=2, ensure_ascii=False)
    print(f"Data saved successfully to {json_output_path}")
    # Print number of categories saved
    print(f"Saved data for {len(final_output_data['menu_details'])} categories.")
except IOError as e:
    print(f"Error: Could not save data to {json_output_path}: {e}")
except Exception as e:
    print(f"An unexpected error occurred during file saving: {e}")

print("Scraping finished.")