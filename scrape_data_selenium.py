from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

URL = "https://www.dsec.gov.mo/ts/#!/step2/en-US"

def main():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)
    driver.get(URL)

    # Wait for page and scripts to load
    time.sleep(5)
    try:
        # Iframes: switch if any present
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        if iframes:
            driver.switch_to.frame(iframes[0])

        # Wait for a cell containing 'Jan./1997' to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ag-cell') and contains(text(), 'Jan./1997')]") )
        )
        # Scroll to bottom to trigger lazy loading if needed
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, 'div.ag-row')
        data = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, 'div.ag-cell')
            if len(cells) >= 2:
                date = cells[0].text.strip()
                value = cells[1].text.strip()
                data.append({"date": date, "value": value})
        # Save to scraped.json
        with open("scraped.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(data)} rows to scraped.json")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
