# Before running, install dependencies with:
# pip install -r requirements.txt
#
# This script requires Chrome, ChromeDriver, and a Codespace or similar environment.
#

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urljoin
from selenium.webdriver.common.keys import Keys

def accept_cookie_consent(driver):
    """Handles cookie consent popups with multiple selectors"""
    print("Checking for cookie consent pop-up...")
    try:
        time.sleep(3)
        consent_button_selectors = [
            (By.CSS_SELECTOR, '#sliding-popup #popup-buttons button.agree-button'),
            (By.CSS_SELECTOR, 'button.agree-button'),
            (By.XPATH, "//button[contains(., 'Acepto')]"),
            (By.CSS_SELECTOR, 'button.cky-btn.cky-btn-accept'),
            (By.ID, 'hs-eu-confirmation-button'),
            (By.XPATH, "//button[contains(., 'Aceptar todas')]"),
            (By.XPATH, "//button[contains(., 'Aceptar todo')]"),
            (By.XPATH, "//a[contains(., 'Aceptar todas')]"),
            (By.XPATH, "//a[contains(., 'Aceptar todo')]"),
            (By.XPATH, "//button[contains(., 'Accept All')]"),
            (By.XPATH, "//button[contains(., 'Accept cookies')]"),
            (By.XPATH, "//a[contains(., 'Accept All')]"),
            (By.XPATH, "//a[contains(., 'Accept cookies')]"),
            (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar')]"),
            (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cookies')]"),
            (By.CSS_SELECTOR, 'button[aria-label*="accept"]'),
            (By.CSS_SELECTOR, 'button[name*="accept"]'),
            (By.CSS_SELECTOR, 'button[title*="accept"]'),
            (By.XPATH, "//button[contains(@class, 'cookie') and (contains(text(), 'Accept') or contains(text(), 'Aceptar'))]"),
            (By.CSS_SELECTOR, '[id*="cookie"][id*="accept"]'),
            (By.CSS_SELECTOR, '[class*="cookie"][class*="accept"]'),
        ]

        clicked = False
        for by_type, selector in consent_button_selectors:
            try:
                consent_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                if consent_button.is_displayed(): 
                    print(f"Attempting to click cookie button with selector: {selector}")
                    driver.execute_script("arguments[0].click();", consent_button)
                    print("Cookie consent accepted.")
                    time.sleep(1)
                    clicked = True
                    break
            except (NoSuchElementException, TimeoutException):
                continue
            except ElementClickInterceptedException:
                print(f"Click intercepted for {selector}. Trying to dismiss overlay with ESC.")
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
                try:
                    consent_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by_type, selector)))
                    driver.execute_script("arguments[0].click();", consent_button)
                    print("Cookie consent accepted after ESC.")
                    time.sleep(1)
                    clicked = True
                    break
                except Exception:
                    continue

        if not clicked:
            print("No obvious cookie consent button found.")
            try:
                print("Attempting to close with ESC key...")
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
            except Exception:
                pass

    except Exception as e:
        print(f"Error handling cookie consent: {e}")

def scrape_coworking_spaces_selenium(driver, url):
    """Scrapes main listing page for coworking space names and links"""
    all_coworking_data = []
    try:
        print("Navigating to main page...")
        driver.get(url)
        print("Page loaded.")
        accept_cookie_consent(driver)

        print("Waiting for listings container...")
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.view-content'))
        )
        print("Main container found.")
        time.sleep(2)

        scroll_attempts = 0
        max_scroll_attempts = 150

        while scroll_attempts < max_scroll_attempts:
            scroll_attempts += 1
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            current_count = len(driver.find_elements(By.CSS_SELECTOR, 'div.view-content > div.views-row'))
            print(f"Current listings: {current_count}")

            try:
                mostrar_mas_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Mostrar más')]"))
                )
                driver.execute_script("arguments[0].click();", mostrar_mas_button)
                
                WebDriverWait(driver, 20).until( 
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, 'div.view-content > div.views-row')) > current_count
                )
                time.sleep(1.5)
            except (TimeoutException, NoSuchElementException):
                print("No more 'Mostrar más' buttons. Proceeding.")
                break
            except Exception as e:
                print(f"Error: {e}. Continuing.")
                continue

        print(f"Finished loading. Total attempts: {scroll_attempts}")
        print(f"Final listings count: {len(driver.find_elements(By.CSS_SELECTOR, 'div.view-content > div.views-row'))}")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        coworking_listings = soup.select('div.view-content > div.views-row')

        if not coworking_listings:
            print("No listings found.")
            return []
        
        print(f"Found {len(coworking_listings)} listings for processing.")

        for listing in coworking_listings:
            name = 'N/A'
            link = 'N/A'
            
            try:
                name_link_tag = listing.select_one('div.spaces-list-title > a') or listing.select_one('div.spaces-list-title h2 a')
                
                if name_link_tag:
                    h2_tag = name_link_tag.select_one('h2')
                    name = h2_tag.text.strip() if h2_tag else name_link_tag.text.strip()
                    
                    if 'href' in name_link_tag.attrs:
                        link = urljoin(url, name_link_tag['href'])
            
                all_coworking_data.append({'Name': name, 'Link': link})

            except Exception as e:
                print(f"Error processing listing: {e}")
                continue

        return all_coworking_data

    except Exception as e:
        print(f"Stage 1 error: {e}")
        return []

def scrape_coworking_details(driver, url):
    """Scrapes detailed information with scrolling to load all content"""
    details = {
        'Description': 'N/A',
        'Website': 'N/A',
        'Phone': 'N/A',
        'Address': 'N/A',
        'Services_List': 'N/A',
        'Detailed_Prices': 'N/A',
        'Surface_Area': 'N/A',
        'Private_Offices': 'N/A',
        'Meeting_Rooms_Count': 'N/A',
        'Capacity': 'N/A',
        'Image_URL': 'N/A'
    }
    print(f"  Scraping details from: {url}")
    try:
        driver.get(url)
        
        # Wait for any content to load
        print("  Waiting for page to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
        )
        
        # Scroll to load all content
        print("  Scrolling to load content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 3:  # Scroll 3 times to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
        
        time.sleep(2)  # Final pause after scrolling
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # --- Extract Description ---
        try:
            description_tag = soup.select_one('div.field-name-body div.field-item.even[property="content:encoded"]') or \
                              soup.select_one('div.field-name-body div.field-item.even')
            details['Description'] = description_tag.get_text(separator='\n', strip=True) if description_tag else 'N/A'
            print(f"    Description: {'Found' if details['Description'] != 'N/A' else 'N/A'}")
        except Exception as e:
            print(f"    Error with Description: {e}")

        # --- Extract Address ---
        try:
            address_tag = soup.select_one('div.space-info div.field-name-field-coworking-address div.field-item.even')
            details['Address'] = address_tag.get_text(strip=True) if address_tag else 'N/A'
            print(f"    Address: {details['Address']}")
        except Exception as e:
            print(f"    Error with Address: {e}")

        # --- Extract Phone ---
        try:
            phone_tag = soup.select_one('div.space-info div.field-name-field-coworking-telefono div.field-item.even')
            details['Phone'] = phone_tag.get_text(strip=True) if phone_tag else 'N/A'
            print(f"    Phone: {details['Phone']}")
        except Exception as e:
            print(f"    Error with Phone: {e}")

        # --- Extract Website ---
        try:
            website_link_tag = soup.select_one('div.space-info div.field-name-field-coworking-web div.field-item.even a')
            details['Website'] = website_link_tag['href'] if website_link_tag and 'href' in website_link_tag.attrs else 'N/A'
            print(f"    Website: {details['Website']}")
        except Exception as e:
            print(f"    Error with Website: {e}")

        # --- Extract Services ---
        try:
            services_found_list = []
            services_heading = soup.find('h2', class_='field-label', string='Servicios')
            if services_heading:
                services_items_container = services_heading.find_next_sibling('div', class_='field-items')
                if services_items_container:
                    for service_item in services_items_container.select('span.term-name'):
                        service_name = service_item.get_text(strip=True)
                        if service_name:
                            services_found_list.append(service_name)
            details['Services_List'] = "; ".join(services_found_list) if services_found_list else 'N/A'
            print(f"    Services: {len(services_found_list)} found")
        except Exception as e:
            print(f"    Error with Services: {e}")

        # --- Extract Basic Info ---
        try:
            basic_info_container = soup.select_one('div.space-info div.basic-info.clearfix')
            if basic_info_container:
                for info_item in basic_info_container.select('div.info-item'):
                    label_tag = info_item.select_one('.info-item-label')
                    value_tag = info_item.select_one('.info-item-value')
                    
                    if label_tag and value_tag:
                        label = label_tag.get_text(strip=True).lower()
                        value = value_tag.get_text(strip=True)
                        
                        if 'superficie' in label:
                            details['Surface_Area'] = value
                        elif 'despachos' in label:
                            details['Private_Offices'] = value
                        elif 'salas' in label:
                            details['Meeting_Rooms_Count'] = value
                        elif 'capacidad' in label:
                            details['Capacity'] = value
                print(f"    Metrics: Surface={details['Surface_Area']}, Offices={details['Private_Offices']}")
        except Exception as e:
            print(f"    Error with Metrics: {e}")

        # --- Extract Detailed Prices ---
        try:
            all_prices_data = []
            detailed_rate_blocks = soup.select('section.space-rates div.block.block-views.clearfix')
            
            if detailed_rate_blocks:
                for block in detailed_rate_blocks:
                    block_title_tag = block.select_one('h2.block-title')
                    block_category = block_title_tag.get_text(strip=True).replace('Tarifas de ', '') if block_title_tag else "Unknown"
                    
                    for row in block.select('div.views-row'):
                        price_details = {'Category': block_category}
                        price_details['Plan_Name'] = row.select_one('.views-field-title .field-content a').get_text(strip=True) if row.select_one('.views-field-title .field-content a') else 'N/A'
                        price_details['Type'] = row.select_one('.col-field-tarifa-pase-tipo .field-content, .col-field-tarifa-tipo .field-content').get_text(strip=True) if row.select_one('.col-field-tarifa-pase-tipo .field-content, .col-field-tarifa-tipo .field-content') else 'N/A'
                        price_details['Price'] = row.select_one('.col-field-tarifa-precio-billing-price .field-content').get_text(strip=True) if row.select_one('.col-field-tarifa-precio-billing-price .field-content') else 'N/A'
                        all_prices_data.append(price_details)
            
            if all_prices_data:
                formatted_prices = []
                for price_item in all_prices_data:
                    parts = [f"Category: {price_item['Category']}", f"Plan: {price_item['Plan_Name']}", f"Price: {price_item['Price']}"]
                    formatted_prices.append(", ".join(parts))
                details['Detailed_Prices'] = " || ".join(formatted_prices)
                print(f"    Prices: {len(all_prices_data)} plans found")
            else:
                details['Detailed_Prices'] = 'N/A'
                print("    No pricing info found")
        except Exception as e:
            print(f"    Error with Prices: {e}")
            details['Detailed_Prices'] = 'Error'

        # --- Extract Image URL ---
        try:
            image_link_tag = soup.select_one('div.photoswipe-gallery a.photoswipe[href]')
            details['Image_URL'] = image_link_tag['href'] if image_link_tag else 'N/A'
            print(f"    Image: {'Found' if details['Image_URL'] != 'N/A' else 'N/A'}")
        except Exception as e:
            print(f"    Error with Image: {e}")

    except TimeoutException:
        print(f"  Timeout loading {url}")
    except Exception as e:
        print(f"  Error with {url}: {e}")
    return details

def save_to_excel(data, filename="coworking_barcelona.xlsx"):
    """Saves data to Excel file"""
    if data:
        try:
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False)
            print(f"Data saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving Excel: {e}")
            return False
    print("No data to save")
    return False

if __name__ == "__main__":
    url = "https://coworkingspain.es/espacios/coworking/barcelona"

    print("\n" + "="*50)
    print("LAUNCHING BROWSER")
    print("="*50)
    
    # Configure for Codespace environment
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # Essential for Codespace
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Use webdriver-manager for automatic driver setup
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # STAGE 1: Scrape names and links
        print("\n" + "="*50)
        print("STAGE 1: GETTING NAMES AND LINKS")
        print("="*50)
        
        summary_data = scrape_coworking_spaces_selenium(driver, url)
        
        if not summary_data:
            print("No data from Stage 1. Exiting.")
            exit()
            
        print(f"\nStage 1 complete! Found {len(summary_data)} spaces")
        
        # Automate scraping all spaces
        spaces_to_scrape = summary_data
        print(f"\nScraping details for all {len(spaces_to_scrape)} spaces...")
        
        # STAGE 2: Scrape details
        print("\n" + "="*50)
        print("STAGE 2: SCRAPING DETAILS")
        print("="*50)
        
        final_data = []
        
        for i, space in enumerate(spaces_to_scrape):
            print(f"\nProcessing {i+1}/{len(spaces_to_scrape)}: {space['Name']}")
            
            if space['Link'] and space['Link'] != 'N/A':
                details = scrape_coworking_details(driver, space['Link'])
                combined = {
                    'Name': space['Name'],
                    'Link': space['Link'],
                    'Description': details['Description'],
                    'Website': details['Website'],
                    'Phone': details['Phone'],
                    'Address': details['Address'],
                    'Services_List': details['Services_List'],
                    'Detailed_Prices': details['Detailed_Prices'],
                    'Surface_Area': details['Surface_Area'],
                    'Private_Offices': details['Private_Offices'],
                    'Meeting_Rooms_Count': details['Meeting_Rooms_Count'],
                    'Capacity': details['Capacity'],
                    'Image_URL': details['Image_URL']
                }
                final_data.append(combined)
                print(f"✓ Details scraped")
            else:
                print("⚠️ No link - skipping details")
                final_data.append(space)
            
            # Save progress every 10 spaces
            if (i+1) % 10 == 0:
                print(f"\nSaving checkpoint after {i+1} spaces...")
                save_to_excel(final_data, f"checkpoint_{i+1}.xlsx")
            
            time.sleep(2)
        
        # Save final results
        print("\n" + "="*50)
        if save_to_excel(final_data):
            print("SUCCESS: Final data saved to coworking_barcelona.xlsx")
        else:
            print("WARNING: Possible save issue")
            
        print("\nSCRAPING COMPLETE!")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        driver.quit()
        print("Browser closed.")
