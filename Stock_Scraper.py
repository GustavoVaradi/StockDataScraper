import os
import csv
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# Configurations
OUTPUT_FILE = "stock_data.csv"
LOG_FILE = "url_status_log.csv"
TICKER_FILE = "acoes-listadas-b3.csv"
BASE_URL = "https://analitica.auvp.com.br/acoes/"
XPATHS = {
    "price": '//*[@id="asset-header"]/div/div[1]/div[2]/div[1]/span',
    "LPA": '//*[@id="PAGE_CONTAINER"]/main/div[3]/div/div[2]/div[2]/div/div[2]/div[1]/div/div[4]/div[2]/span',
    "VPA": '//*[@id="PAGE_CONTAINER"]/main/div[3]/div/div[2]/div[2]/div/div[2]/div[1]/div/div[5]/div[2]/span'
}

def initialize_csv(file_path, header):
    """Creates a new CSV file with a header."""
    if os.path.exists(file_path):
        os.remove(file_path)
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)

def log_status(url, status_code, status):
    """Logs the URL status in a CSV file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, url, status_code, status])

def check_url_status(url):
    """Checks if a URL is accessible."""
    try:
        response = requests.get(url, timeout=5)
        status_code = response.status_code
        return status_code, "UP" if status_code == 200 else "DOWN"
    except requests.exceptions.RequestException as e:
        return "ERROR", str(e)

def extract_data(driver, ticker, url):
    """Extracts financial data using Selenium."""
    try:
        driver.get(url)
        
        def get_float(xpath):
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            raw_text = element.text.replace(',', '.')
            return float(raw_text.replace('R$ ', '')) if "-" not in raw_text else 0
        
        price = get_float(XPATHS["price"])
        lpa = get_float(XPATHS["LPA"])
        vpa = get_float(XPATHS["VPA"])
        real_price = (22.5 * lpa * vpa) ** (1/2)
        
        with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([ticker, price, lpa, vpa, f"{real_price:.2f}"])
        
    except Exception as e:
        print(f"❌ Error extracting data for {ticker}: {e}")

def main():
    """Main function to run the data extraction process."""
    initialize_csv(OUTPUT_FILE, ["Ticker", "Price", "LPA", "VPA", "Real Price"])
    initialize_csv(LOG_FILE, ["Timestamp", "URL", "Status Code", "Status"])
    
    df_tickers = pd.read_csv(TICKER_FILE)
    tickers = df_tickers["Ticker"].tolist()
    urls = [BASE_URL + ticker for ticker in tickers]
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    for url in tqdm(urls, desc="Processing URLs", unit="url"):
        ticker = url.split("/")[-1].upper()
        status_code, status = check_url_status(url)
        log_status(url, status_code, status)
        if status == "UP":
            extract_data(driver, ticker, url)
    
    driver.quit()
    print("\n📂 Extraction completed! Data saved in 'stock_data.csv'")

    # Read the CSV file and calculate the 'real price'
    df = pd.read_csv(OUTPUT_FILE)
    df.to_csv(OUTPUT_FILE, decimal=',', sep=';', index=False)
    print("📈 'Real price' calculated and saved in 'stock_data.csv'")

if __name__ == "__main__":
    main()