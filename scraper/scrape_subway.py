import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path # Added for path handling

# Define Restaurant Name
RESTAURANT_NAME = "Subway (India - Unofficial Source)"

# Step 1: Fetch the page
url = "https://subwaymenupedia.com/subway-menu-prices-india/"
print(f"Fetching URL: {url}")
response = requests.get(url)
response.raise_for_status()  # Raise error if request failed
print("Successfully fetched page.")

# Step 2: Parse the page
soup = BeautifulSoup(response.text, "html.parser")
print("Successfully parsed HTML.")

# Step 3: Initialize intermediate dictionary (original logic)
menu_details_by_category = {}

# Step 4: Go through each section (original logic)
current_category = None

for tag in soup.find_all(["h2", "h3", "h4", "h5", "p"]):
    # h2 and h3 are categories
    if tag.name == "h2":
        current_category = tag.get_text(strip=True)
        # Check if category is likely valid menu category
        if current_category and len(current_category) < 50 and 'comment' not in current_category.lower():
            menu_details_by_category[current_category] = {}
        else:
            current_category = None # Reset if header looks invalid
    elif tag.name == "h3":
        current_category = tag.get_text(strip=True)
        if current_category and len(current_category) < 50 and 'comment' not in current_category.lower():
            menu_details_by_category[current_category] = {}
        else:
             current_category = None # Reset if header looks invalid
    # h4 or h5 are item names
    elif tag.name in ["h4", "h5"]:
        if current_category is None or current_category not in menu_details_by_category:
            continue  # Skip if no valid category yet or category was reset

        item_name = tag.get_text(strip=True)

        # Try to find the price nearby (original logic)
        price_tag = tag.find_next(["p", "div"])
        price = None
        description = None

        if price_tag:
            text = price_tag.get_text(strip=True)
            if "₹" in text:
                price = text
            else:
                description = text
                # Check next p/div for price
                next_price_tag = price_tag.find_next(["p", "div"])
                if next_price_tag and "₹" in next_price_tag.get_text(strip=True):
                    price = next_price_tag.get_text(strip=True)

        # Save data (original logic)
        if item_name and price:
            # Check if price is reasonable (basic validation)
            if len(price) < 20: # Avoid overly long price strings
                 menu_details_by_category[current_category][item_name] = {
                     "price": price
                 }

# --- Create Final Output Structure ---
final_output_data = {
    "restaurant_name": RESTAURANT_NAME,
    # Add other top-level fields as desired (using placeholders)

    "menu_details": menu_details_by_category # Nest the scraped data
}


# Step 5: Save to JSON
print("\n--- Saving Data to JSON ---")
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
data_dir = project_root / 'data'
# Use a descriptive filename
json_output_path = data_dir / 'subway_menu_unofficial.json'
data_dir.mkdir(parents=True, exist_ok=True)

try:
    # Save the final_output_data dictionary
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output_data, f, indent=4, ensure_ascii=False)
    print(f"Data saved successfully to {json_output_path}!")
    # Optional: Print number of categories found
    print(f"Found data for {len(menu_details_by_category)} categories.")

except Exception as e:
    print(f"Error saving data: {e}")


# --- Optional Cleaning Step (Kept as separate logic for clarity) ---
# This part remains unchanged from the original script, operating on the saved file.
# Note: It saves to a *different* cleaned file and removes the intermediate one.

print("\nCleaning data...")
try:
    # Load the JSON file just saved
    with open(json_output_path, "r", encoding="utf-8") as f:
        # We need to access the nested menu details
        loaded_data = json.load(f)
        data_to_clean = loaded_data.get("menu_details", {}) # Get the nested dict

    # Prepare final cleaned data structure (original logic)
    final_cleaned_data_structure = {
        "restaurant_name": RESTAURANT_NAME + " (Cleaned)",



        "menu": { # Changed key name for clarity
             "Veg": {},
             "Non-Veg": {}
        }
    }

    # Define simple veg and non-veg keywords (original logic)
    veg_keywords = ["Paneer", "Aloo", "Veg", "Corn", "Peas", "Bean", "Shammi", "Chilli", "Hara Bhara", "Vegetarian", "Mexican Patty"]
    nonveg_keywords = ["Chicken", "Egg", "B.M.T", "Tuna", "Meatball", "Keema", "Roast", "Smoked", "Peri Peri", "Turkey", "Steak"]

    def is_veg(name):
        # Ignore non-veg keywords even if veg keyword is present
        if is_nonveg(name): return False
        return any(veg_word.lower() in name.lower() for veg_word in veg_keywords)

    def is_nonveg(name):
        return any(nonveg_word.lower() in name.lower() for nonveg_word in nonveg_keywords)

    # Helper function to check if entry is a real item (original logic)
    def is_valid_item(entry):
        price = entry.get("price", "")
        # Improved check for validity
        return price and "Image from Swiggy" not in price and len(price) < 20

    # Loop through original data (from loaded JSON)
    for category, items in data_to_clean.items():
        if isinstance(items, dict):
            for item_name, item_info in items.items():
                if not isinstance(item_info, dict): continue
                if not is_valid_item(item_info): continue

                # Create structured item info for cleaned output
                cleaned_item_info = {

                    "price": item_info.get("price", ""),
                    "original_category": category # Keep track of original category
                }

                if is_veg(item_name):
                    final_cleaned_data_structure["menu"]["Veg"][item_name] = cleaned_item_info
                elif is_nonveg(item_name):
                    final_cleaned_data_structure["menu"]["Non-Veg"][item_name] = cleaned_item_info
                # Items not classified as Veg/Non-Veg by keywords are currently skipped
                # Could add an "Other" category if needed

    # Save cleaned data to a new file
    cleaned_json_output_path = data_dir / 'subway_menu_unofficial_cleaned.json'
    with open(cleaned_json_output_path, "w", encoding="utf-8") as f:
        json.dump(final_cleaned_data_structure, f, indent=4, ensure_ascii=False)

    print(f"Cleaned file saved as {cleaned_json_output_path}!")
    # os.remove(json_output_path) # Keep intermediate file for now, don't remove automatically
    # print(f'Intermediate file {json_output_path} kept.')

except FileNotFoundError:
     print(f"Error: Could not find intermediate file {json_output_path} for cleaning.")
except Exception as e:
     print(f"Error during cleaning process: {e}")