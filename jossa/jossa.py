import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
from bs4 import BeautifulSoup
import csv
from openpyxl import Workbook

# === Function to select value from a 'chosen.js' enhanced dropdown ===
def select_chosen_dropdown_option(driver, wait, dropdown_base_id, option_text):
    """
    Simulates interaction with a JavaScript-enhanced <select> using Chosen.js.
    This is needed because the dropdown is hidden and replaced by a custom UI.
    
    Args:
    - driver: Selenium WebDriver instance
    - wait: WebDriverWait instance for waiting on elements
    - dropdown_base_id: ID of the <select> element (not the rendered div)
    - option_text: visible text to be selected
    """

    # Chosen.js creates a separate container with "_chosen" suffix
    chosen_id = dropdown_base_id + "_chosen"
    
    # Wait for the dropdown container to appear
    container = wait.until(EC.presence_of_element_located((By.ID, chosen_id)))
    
    # Find the clickable area of the dropdown
    dropdown_button = container.find_element(By.CLASS_NAME, "chosen-single")
    
    # Use ActionChains to simulate user click
    actions = ActionChains(driver)
    actions.move_to_element(dropdown_button).click().perform()
    
    # After dropdown expands, locate the specific option <li> to click
    option_xpath = f"//ul[@class='chosen-results']/li[text()='{option_text}']"
    option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
    
    # Click on the selected option
    actions.move_to_element(option).click().perform()

    # Allow UI to update
    time.sleep(0.5)


# === Main workflow function ===
def main(params):
    """
    Orchestrates the full automation process: open URL, select dropdowns, submit, scrape table, save to CSV.

    Args:
    - params: dictionary of all dropdown values (year, round_no, instype, etc.)
    """
    driver = webdriver.Chrome()  # ChromeDriver should be in PATH
    wait = WebDriverWait(driver, 10)

    # Load the JoSAA page
    url = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
    driver.get(url)

    # Ensure the page has fully loaded by checking the main dropdown
    wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlYear")))

    # Select all dropdown parameters passed in
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlYear",     params["year"])
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlroundno",  params["round_no"])
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlInstype",  params["instype"])
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlInstitute",params["institute"])
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlBranch",   params["branch"])
    select_chosen_dropdown_option(driver, wait, "ctl00_ContentPlaceHolder1_ddlSeatType", params["seat_type"])

    # Click the Submit button
    submit_button = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btnSubmit")))
    submit_button.click()
    print("Submit clicked")

    # Wait for the results table to render
    results_table = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1")))
    print("Results table loaded")

    # Parse HTML with BeautifulSoup after results load
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # Locate the table in parsed HTML
    table = soup.find("table", {"id": "ctl00_ContentPlaceHolder1_GridView1"})

    # === Extract header row ===
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    # === Extract all data rows ===
    data = []
    for row in table.find_all("tr")[1:]:  # Skip header row
        cells = row.find_all("td")
        if cells:
            data.append([cell.get_text(strip=True) for cell in cells])

    # === Construct output filename based on params ===
    filename = params["year"] + "_" + params["seat_type"] + "_" + params["round_no"] + "_" + params["instype"] + "_" + params["institute"] + ".xlsx"

    # # === Write data to CSV ===
    # with open(filename, "w", newline='', encoding='utf-8') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(headers)
    #     writer.writerows(data)
    #     print(f"Data saved to {filename} in same directory as script")

    
    # Create a new workbook and get the active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = str(params["year"])
    ws.append(headers)
    # Write data rows
    for row in data:
        ws.append(row)
    # Save the file
    wb.save(filename)  # Make sure filename ends with '.xlsx'
    print(f"Data saved to {filename} in same directory as script")




    # Optional wait before quitting (for visual confirmation if debugging)
    time.sleep(5)
    driver.quit()


# === Entry Point ===
if __name__ == "__main__":
    # Define your dropdown selections here
    params = {
        "year":      "2023", ## 2024 ------------- 2016
        "round_no":  "6",    ## 1 --------------------5
        "instype":   "ALL",  ## ALL, National Institute of Technology, Government Funded Technical Institutions,  Indian Institute of Information Technology, National Institute of Technology
        "institute": "ALL",  ## ALL
        "branch":    "ALL",  ## ALL
        "seat_type": "OBC-NCL",  # You can change this to SC/ST/GEN/EWS as needed
    }

    # Start automation
    main(params)
