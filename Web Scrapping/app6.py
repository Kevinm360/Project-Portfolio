from flask import Flask, render_template, request, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Set up Selenium with a headless option and rotating user agents
def create_driver():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")

    chrome_service = Service(executable_path="C:/mysql/chromedriver.exe")
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    return driver

# Helper functions for cleaning and handling the data (from webMD.py)
def clean_age(age_str):
    if age_str and not re.match(r'\d{1,2}/\d{1,2}/\d{4}', age_str):  # Ignore if it's a date
        return age_str.replace("Age:", "").strip()  # Remove 'Age:' prefix and any surrounding spaces
    return None  # Return None for dates or invalid entries

def clean_supplement_time(supp_time_str):
    if supp_time_str and not re.match(r'\d{1,2}/\d{1,2}/\d{4}', supp_time_str):  # Ignore if it's a date
        return supp_time_str.strip()  # Just trim spaces
    return 'Unknown'  # Return 'Unknown' for missing or invalid entries

def clean_condition(condition_str):
    if condition_str:
        return condition_str.replace("Condition:", "").strip()  # Remove 'Condition:' prefix
    return 'Unknown'  # Return 'Unknown' if no condition is found

def clean_rating(rating_str):
    if rating_str:
        return rating_str.replace("Overall rating", "").strip()  # Remove 'Overall rating' prefix
    return rating_str

def handle_name(name_str):
    if name_str is None or name_str == '' or re.match(r'\d{1,2}/\d{1,2}/\d{4}', name_str):  # If name is missing or it's a date
        return 'anonymous'
    return name_str

# WebMD scraping function remains unchanged
def scrape_webmd(url):
    driver = create_driver()
    all_reviews = []  # List to store all the reviews

    # Loop through multiple pages (adjust the range for more pages as needed)
    page = 1
    while True:
        page_url = f"{url}?page={page}&next_page=true"
        driver.get(page_url)
        time.sleep(5)  # Allow time for the page to load
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all review sections
        reviews = soup.find_all('div', class_='review-details-holder')
        
        if not reviews:
            # Break the loop if no more reviews are found
            break
        
        for review in reviews:
            try:
                # Extract user info (name, age, supplement time)
                user_info = review.find('div', class_='card-header')
                if user_info:
                    user_info_text = user_info.get_text(strip=True)
                    # Initialize variables
                    name = None
                    age = None
                    supplement_time = None

                    # Split on '|' to separate name/age from supplement time
                    parts = user_info_text.split('|')
                    if len(parts) > 0:
                        name_age_part = parts[0].strip()
                        age_match = re.search(r'Age:\s*(\d{2}-\d{2}|75 or over)', name_age_part)
                        if age_match:
                            name = name_age_part.split('Age:')[0].strip()  # Name is before "Age:"
                            age = age_match.group(1).strip()  # Extract age
                        else:
                            name = name_age_part

                    if len(parts) > 1:
                        supp_part = parts[1].strip()
                        if supp_part.startswith('On supplement for'):
                            supplement_time = supp_part
                        else:
                            if re.search(r'\d{2}-\d{2}|75 or over', supp_part):
                                age = supp_part  # Assign as age if format matches age
                            else:
                                supplement_time = supp_part

                    # Clean up the age and supplement time format, and filter out dates
                    age = clean_age(age)
                    supplement_time = clean_supplement_time(supplement_time)
                    name = handle_name(name)  # Handle missing or invalid names

                    name_text = name
                    supplement_time_text = supplement_time
                else:
                    name_text = 'anonymous'
                    supplement_time_text = 'Unknown'

                # Extract condition
                condition = review.find('strong', class_='condition')
                condition_text = clean_condition(condition.get_text(strip=True)) if condition else 'Unknown'

                # Extract overall rating
                overall_rating = review.find('div', class_='overall-rating')
                rating_text = clean_rating(overall_rating.get_text(strip=True)) if overall_rating else 'No Rating'

                # Extract review text
                review_text = review.find('div', class_='description')
                review_text_text = review_text.get_text(strip=True) if review_text else 'No Review Text'

                all_reviews.append([name_text, supplement_time_text, condition_text, rating_text, review_text_text])
            except Exception as e:
                print(f"Error extracting data from a review: {e}")

        # Increment the page number to scrape the next page
        page += 1

    driver.quit()

    # Save all the reviews into a DataFrame and export it to a CSV
    df = pd.DataFrame(all_reviews, columns=['Name', 'Supplement Time', 'Condition', 'Rating', 'Review Text'])
    output_file = 'webmd_all_reviews.csv'
    df.to_csv(output_file, index=False)
    return output_file

# Scrape a single page of reviews
def scrape_amazon_page(url, page):
    driver = create_driver()
    driver.get(f"{url}&pageNumber={page}")
    time.sleep(random.uniform(2, 4))  # Dynamic waiting time
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    reviews = soup.find_all('div', {'data-hook': 'review'})
    page_reviews = []

    for review in reviews:
        name = review.find('span', class_='a-profile-name')
        rating = review.find('i', {'data-hook': 'review-star-rating'})
        review_text = review.find('span', {'data-hook': 'review-body'})

        page_reviews.append([
            name.get_text(strip=True) if name else 'No Name Found',
            rating.get_text(strip=True) if rating else 'No Rating Found',
            review_text.get_text(strip=True) if review_text else 'No Review Text Found'
        ])

    return page_reviews

# Optimized Amazon scraping function for 1,000 reviews using multithreading
def scrape_amazon(url):
    all_reviews = []  # List to store all the reviews
    max_reviews = 1000 # Stop at 1,000 reviews
    max_pages = (max_reviews // 10) + 1  # Assuming 10 reviews per page

    # Use ThreadPoolExecutor to fetch multiple pages in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_amazon_page, url, page) for page in range(1, max_pages + 1)]

        for future in futures:
            result = future.result()
            all_reviews.extend(result)

            if len(all_reviews) >= max_reviews:
                break

    # Save all the reviews into a DataFrame and export it to a CSV
    df = pd.DataFrame(all_reviews[:max_reviews], columns=['Name', 'Rating', 'Review Text'])
    output_file = 'amazon_reviews_1000.csv'
    df.to_csv(output_file, index=False)
    return output_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    
    if 'amazon.com' in url:
        csv_file = scrape_amazon(url)
    elif 'webmd.com' in url:
           csv_file = scrape_webmd(url)
    else:
        return "Website not supported yet."

    return send_file(csv_file, as_attachment=True, mimetype='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
