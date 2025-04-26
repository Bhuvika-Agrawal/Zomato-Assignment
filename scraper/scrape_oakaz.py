from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By # Not used in get_items, but good practice
from selenium.webdriver.support.ui import WebDriverWait # Not used in get_items, but good practice
from selenium.webdriver.support import expected_conditions as EC # Not used in get_items
from selenium.webdriver.chrome.service import Service 
from pathlib import Path # To handle file paths
import json # To save JSON
import re # For potential future cleaning (though not used in current get_items)

# --- Data structure to hold all results ---
# Using a placeholder name, update if known
RESTAURANT_NAME = "Oakaz (from URL)"
menu_data = {
    "restaurant_name": RESTAURANT_NAME,
    "location": "Unknown (from URLs)",
    "address": "Not Found",
    "menu": [], # List to store all items from all categories
    "operating_hours": "Not Found",
    "contact_info": "Not Found",
    "scraped_urls": [] # Store all URLs scraped
}
# --- End Data Structure ---


def get_items(url, category_name): # Added category_name parameter
    """
    Gets items from a specific URL using innerText parsing.
    WARNING: Fragile method, may miss data or misinterpret layout.
             Does not capture descriptions reliably or veg/non-veg status.
    """
    data = []
    print(f"  Fetching items for '{category_name}' from {url}")
    # Setup WebDriver within the function (as in original code)
    # Note: Creating a new driver for each URL is less efficient than reusing one.
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Using Service object is recommended even with webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        # No explicit wait in original, relying on page load speed
        # Adding a small implicit wait or short sleep might sometimes help, but isn't robust
        # time.sleep(2) # Example of a small fixed wait
        page_text = driver.execute_script("return document.body.innerText;").split('\n')
        
        # Parsing logic from original code
        for i in range(len(page_text)):
            line = page_text[i].strip()
            if line.startswith("₹"): # Check if the line starts with the currency symbol
                price = line
                name = ""
                # Try to get the line above as the name
                if i > 0:
                    name = page_text[i - 1].strip()
                
                # Basic validation: Ensure name is not empty and not another price
                if name and not name.startswith("₹"):
                    temp_data = {
                        "item_name": name,
                        "description": "", # Description logic was commented out/unreliable
                        "price": price, # Keep price as string as extracted
                        "category": category_name, # Assign the category
                        "special_tags": [] # Cannot determine veg/non-veg
                        }
                    data.append(temp_data)
                # else: print(f"      Skipping potential item: Price={price}, Line above='{name}'") # Debug log
                    
    except Exception as e:
        print(f"    Error processing URL {url}: {e}")
    finally:
        driver.quit()
    print(f"  Found {len(data)} potential items for '{category_name}'.")
    return data

# --- Category URLs (As provided by user) ---
categories = {
    'Beverages': 'https://oakaz.in/catalog/digital-menu/beverages-3272',
    'Summer Special Food': 'https://oakaz.in/catalog/digital-menu/summer-special-food-5440',
    'Summer Special Drinks': 'https://oakaz.in/catalog/digital-menu/summer-special-drinks-5395',
    'Tandoori starters': 'https://oakaz.in/catalog/digital-menu/tandoori-starters-3273',
    'Chinese Starters': 'https://oakaz.in/catalog/digital-menu/chinese-starters-3274',
    'Indian Main Course': 'https://oakaz.in/catalog/digital-menu/indian-main-course-3275',
    'Chinese and Italian': 'https://oakaz.in/catalog/digital-menu/chinese-italian-3276',
    'Rolls': 'https://oakaz.in/catalog/digital-menu/rolls-3277',
    'Thai Curry and Thai noodles': 'https://oakaz.in/catalog/digital-menu/thai-curry-and-thai-noodles-3278',
    'Jain food': 'https://oakaz.in/catalog/digital-menu/jain-food-3279',
    'Desserts': 'https://oakaz.in/catalog/digital-menu/desserts-3280',
}

# --- Main Loop to Scrape Categories ---
print(f"Starting scrape for {RESTAURANT_NAME}...")
all_items = []
scraped_url_list = []

for cat, url in categories.items():
    print(f"Processing category: {cat}")
    items_in_category = get_items(url, cat) # Pass category name to function
    all_items.extend(items_in_category) # Add found items to the main list
    scraped_url_list.append(url) # Keep track of scraped URLs
    print("-" * 20)

# --- Populate final data structure ---
menu_data["menu"] = all_items
menu_data["scraped_urls"] = scraped_url_list # Store the list of URLs used

# --- Save to JSON ---
print("\n--- Saving Data ---")
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
data_dir = project_root / 'data'
# Use a descriptive filename, indicating the source/method if helpful
json_output_path = data_dir / 'oakaz_menu_innertext.json'
data_dir.mkdir(parents=True, exist_ok=True) # Ensure data directory exists

try:
    # Simple duplicate check based on name/price/category before saving
    final_items = []
    seen_keys = set()
    for item in menu_data['menu']:
        key = (item.get('category'), item.get('item_name'), item.get('price'))
        if key not in seen_keys:
            final_items.append(item)
            seen_keys.add(key)
    menu_data['menu'] = final_items

    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(menu_data, f, indent=2, ensure_ascii=False)
    print(f"Data saved successfully to {json_output_path}")
    print(f"Total unique items saved: {len(menu_data['menu'])}")
except IOError as e:
    print(f"Error: Could not save data to {json_output_path}: {e}")
except Exception as e:
    print(f"An unexpected error occurred during file saving: {e}")

print("Scraping finished.")