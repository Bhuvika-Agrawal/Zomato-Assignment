from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException # Added import
from selenium.webdriver.chrome.service import Service # Added import
import time
import json
from pathlib import Path # Added import

# Define Restaurant Constant
RESTAURANT_NAME = "Dominos Pizza"
LOCATION_INFO = "Store ID 6585R (from URL)"
NOTES = "Extracted using innerText parsing with category/filter clicks. Data fragility expected. Veg/Non-Veg based on filter only."
URL = 'https://pizzaonline.dominos.co.in/jfl-discovery-ui/en/web/menu-v1/6585R?&showSearchModal=false&scrollTo=2'


def safe_click(driver, by, value):
    """Safely scroll and click an element."""
    # Original safe_click code
    try:
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.element_to_be_clickable((by, value)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        element.click()
        return True
    except TimeoutException: # Explicitly catch TimeoutException
        return False
    except Exception: # Catch other exceptions
        return False


def get_items(category_name, mode='Veg Only', debug = False):
    # Original get_items code exactly as provided by user
    url = 'https://pizzaonline.dominos.co.in/jfl-discovery-ui/en/web/menu-v1/6585R?&showSearchModal=false&scrollTo=2'
    data = []
    # Use Service object
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = None # Initialize driver
    try:
        # Pass service object
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        wait = WebDriverWait(driver, 10)

        # Select mode (Veg/Non-Veg)
        safe_click(driver, By.XPATH, f"//*[contains(text(), '{mode}')]")
        time.sleep(3)

        # Select category
        success = safe_click(driver, By.XPATH, f"//*[contains(text(), '{category_name}')]")
        if not success:
            print(f"⚠️ Category button '{category_name}' not found in mode '{mode}'.") if debug == True else None
            if driver: driver.quit() # Quit driver if category click fails
            return []
        time.sleep(3)

        # Get page text
        page_text = driver.execute_script("return document.body.innerText;").split('\n')
        i = 0
        while i < len(page_text):
            # Original parsing logic
            if page_text[i].startswith("Rs."):
                if category_name == '5 Course Lunch Feast':
                    name = page_text[i-3] if (i-3) >= 0 else "Unknown"
                    description = page_text[i-2] if (i-2) >= 0 else "Unknown"
                    price = page_text[i]
                else:
                    name = page_text[i-2] if (i-2) >= 0 else "Unknown"
                    description = page_text[i-1] if (i-1) >= 0 else "Unknown"
                    price = page_text[i]

                temp_data = {"name": name, "description": description, "price": price}
                data.append(temp_data)

                # Original skip logic
                if (i + 3 < len(page_text)) and (page_text[i+2].startswith('Save Rs.') or page_text[i+2] == 'Add +'):
                    i += 3
                else:
                    i += 1
            else:
                i += 1

    # Added broad exception catch as in original
    except Exception as e:
        print(f"  Error during scraping for {category_name} ({mode}): {e}")
    finally:
        if driver: # Check if driver was initialized
            driver.quit()

    return data

# ===========================================================
# Main Script (Original structure and variable names kept)
# ===========================================================
dominos_data = {} # Dictionary to hold results, keyed by category
failed_categories = []

# Original category lists
all_cats = [
    'Garlic Breads & More', 'Recommended', 'New Launches', 'Meal for 1',
    'Party Combos', 'No Onion No Garlic', 'Cheese Burst Pizza',
    'Spicy Pizza', '5 Course Lunch Feast', 'Big Big Pizza'
]
special_cats = ['Desserts', 'Beverages']

# Original loops
for cat in all_cats:
    print(f'Processing {cat} in Veg...')
    try:
        veg_items = get_items(cat) # Default mode is 'Veg Only'
        if cat not in dominos_data:
            dominos_data[cat] = {}
        dominos_data[cat]['Veg Only'] = veg_items
    except Exception as e:
        print(f'Failed {cat} in Veg with error: {e}')
        failed_categories.append(f'VEG - {cat}')
    time.sleep(1)

    print(f'Processing {cat} in Non-Veg...')
    try:
        non_veg_items = get_items(cat, mode='Non Veg Only') # Explicitly pass mode
        if cat not in dominos_data:
            dominos_data[cat] = {}
        dominos_data[cat]['Non Veg Only'] = non_veg_items
    except Exception as e:
        print(f'Failed {cat} in Non-Veg with error: {e}')
        failed_categories.append(f'NON-VEG - {cat}')
    time.sleep(1)

for special_cat in special_cats:
    print(f'Processing {special_cat}...')
    try:
        items = get_items(special_cat) # Default mode 'Veg Only'
        # Original key used for special categories
        dominos_data[special_cat] = {'Veg Only': items}
    except Exception as e:
        print(f'Failed {special_cat} with error: {e}')
        failed_categories.append(f'VEG - {special_cat}')
    time.sleep(1)

print("\n--- Saving Data to JSON ---")
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
data_dir = project_root / 'data'

json_output_path = data_dir / 'dominos.json'
data_dir.mkdir(parents=True, exist_ok=True)

# --- Create the final output structure ---
final_output_data = {
    "restaurant_name": RESTAURANT_NAME,


    # Nest the original data structure here
    "menu_by_category_filter": dominos_data
}
# --- End final output structure ---

try:
    # Save the NEW final_output_data dictionary
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ All data has been saved to {json_output_path}!")

    print(f"Saved data for {len(dominos_data)} categories.")

except Exception as e:
    print(f"\n❌ Error saving data to {json_output_path}: {e}")




if failed_categories:
    print("\n⚠️ The following categories failed:")
    for fail in failed_categories:
        print(f"- {fail}")
else:
    print("\n🎉 No failures reported by script! All categories processed.")