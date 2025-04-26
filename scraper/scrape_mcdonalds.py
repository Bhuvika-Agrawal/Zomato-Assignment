from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException # Added for potential safe_click errors
from selenium.webdriver.chrome.service import Service # Added for best practice with webdriver-manager
import time
import json
from pathlib import Path # Added for path handling

# Define Restaurant Constant
RESTAURANT_NAME = "McDonald's (McDelivery)" # Restaurant name added

def safe_click(driver, by, value):
    """Safely scroll and click an element."""
    # Original safe_click logic kept as provided
    try:
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.element_to_be_clickable((by, value)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)  # Small sleep to stabilize after scroll
        element.click()
        return True
    except TimeoutException: # Catch specific exception
        # Optional: Print warning only if debug is True if function signature supported it
        # print(f"  - Element not clickable: {value} (Timeout)")
        return False
    except Exception as e: # Catch broader exceptions
        # print(f"  - Error clicking {value}: {e}")
        return False


def get_items(category_name, mode='Veg', debug = False):
    # Original get_items logic kept exactly as provided
    url = 'https://mcdelivery.co.in/menu'
    data = []
    # Using Service object is recommended best practice
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = None # Initialize driver
    try:
        # Pass service object when creating driver
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        wait = WebDriverWait(driver, 10)

        # Select mode (Veg/Non-Veg)
        # Using original text-based XPath - relies on exact text matching
        safe_click(driver, By.XPATH, f"//*[contains(text(), '{mode}')]")
        time.sleep(3)

        # Select category
        # Using original text-based XPath
        success = safe_click(driver, By.XPATH, f"//*[contains(text(), '{category_name}')]")
        if not success:
            # Original debug print logic
            print(f"⚠️ Category button '{category_name}' not found in mode '{mode}'.") if debug == True else None
            if driver: driver.quit() # Quit driver if category fails
            return []
        time.sleep(3)

        # Get page text
        page_text = driver.execute_script("return document.body.innerText;").split('\n')
        i = 0
        while i < len(page_text):
            # Original parsing logic kept exactly
            if page_text[i] == 'Add':
                if (i-1 >= 0) and '%' in page_text[i-1]: # Check previous line first
                    name = page_text[i-5] if (i-5) >= 0 else "Unknown"
                    description = page_text[i-4] if (i-4) >= 0 else "Unknown"
                    price = page_text[i-3] if (i-3) >= 0 else "Unknown"
                    temp_data = {"name": name, "description": description, "price": price}
                    data.append(temp_data)
                elif (i-1 >= 0) and '₹' in page_text[i-1]: # Check previous line first
                    name = page_text[i-3] if (i-3) >= 0 else "Unknown"
                    description = page_text[i-2] if (i-2) >= 0 else "Unknown"
                    price = page_text[i-1] if (i-1) >= 0 else "Unknown"
                    temp_data = {"name": name, "description": description, "price": price}
                    data.append(temp_data)
                # else: # Original code didn't have an else here for the inner if
                #     i+=1 # If conditions not met, need to increment i? Added for safety.
                #     continue
            i += 1

    # Removed original 'else' block for the outer 'if', keeping original logic flow
    # The original loop structure implies incrementing 'i' regardless of 'Add' condition unless inner condition matched

    # Keep original broad exception handling
    except Exception as e:
         print(f"  Error during scraping for {category_name} ({mode}): {e}")
    finally:
        if driver: # Ensure driver was initialized before quitting
            driver.quit()

    return data

# ===========================================================
# Main Script (Keeping original structure and variables)
# ===========================================================
macd_data = {} # Dictionary to hold results, keyed by category
failed_categories = []

# Original category lists kept
all_cats = [
    'Korean Range & New Offerings',
    'Group Sharing Combos',
    'McSaver Combos (2 Pc Meals)',
    'Burger Combos ( 3 Pc Meals )',
    'Burgers & Wraps',
    'Burgers With Millet Bun'
]
special_cats = [
    'Fries & Sides',
    'Coffee & Beverages (Hot and Cold)',
    'Cakes Brownies and Cookies',
    'Desserts',
]

# Original loops kept
for cat in all_cats:
    print(f'Processing {cat} in Veg...')
    try:
        veg_items = get_items(cat) # Default mode is 'Veg'
        if cat not in macd_data:
            macd_data[cat] = {}
        # Store under 'Veg Only' key as in original script
        macd_data[cat]['Veg Only'] = veg_items
    except Exception as e:
        print(f'Failed {cat} in Veg with error: {e}')
        failed_categories.append(f'VEG - {cat}')
    time.sleep(1)

    print(f'Processing {cat} in Non-Veg...')
    try:
        # Explicitly pass mode='Non-Veg'
        non_veg_items = get_items(cat, mode='Non-Veg')
        if cat not in macd_data:
            macd_data[cat] = {}
         # Store under 'Non Veg Only' key as in original script
        macd_data[cat]['Non Veg Only'] = non_veg_items
    except Exception as e:
        print(f'Failed {cat} in Non-Veg with error: {e}')
        failed_categories.append(f'NON-VEG - {cat}')
    time.sleep(1)


for cat in special_cats:
    # Original logic for special categories kept
    print(f'Processing {cat} in special...')
    try:
        special_items = get_items(cat) # Default 'Veg' mode
        if cat not in macd_data:
            macd_data[cat] = {}
        # Store under original key 'desserts and bevrages'
        macd_data[cat]['desserts and bevrages'] = special_items
    except Exception as e:
        print(f'Failed {cat} in desserts and bevrages with error: {e}')
        failed_categories.append(f'special - {cat}')
    time.sleep(1)

# ===========================================================
# MODIFIED JSON SAVING LOGIC (Only change requested)
# ===========================================================
print("\n--- Saving Data to JSON ---")
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
data_dir = project_root / 'data'
# Use the original filename specified in the user's code
json_output_path = data_dir / 'macd.json'
data_dir.mkdir(parents=True, exist_ok=True) # Ensure data directory exists

# --- Create the final output structure with ONLY restaurant name + original data ---
final_output_data = {
    "restaurant_name": RESTAURANT_NAME, # Added restaurant name using constant
    # The original data structure generated by the script's loops
    "menu_details": macd_data # Use a key like 'menu_details' to nest the original data
}
# --- End final output structure ---


try:
    # Save the NEW final_output_data dictionary
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output_data, f, ensure_ascii=False, indent=4)
    # Use original success message structure
    print(f"\n✅ All data has been saved to {json_output_path}!")

except Exception as e:
    print(f"\n❌ Error saving data to {json_output_path}: {e}")

# ===========================================================
# Keep original final summary logic
# ===========================================================
if failed_categories:
    print("\n⚠️ The following categories failed:")
    for fail in failed_categories:
        print(f"- {fail}")
else:
    print("\n🎉 No failures reported by script! All categories processed.")