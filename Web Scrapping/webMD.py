import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import pandas as pd

# Configure the WebDriver
chrome_service = Service(executable_path="C:/mysql/chromedriver.exe")
driver = webdriver.Chrome(service=chrome_service)

# Function to clean the 'Age' column by removing the "Age:" prefix
def clean_age(age_str):
    if age_str and not re.match(r'\d{1,2}/\d{1,2}/\d{4}', age_str):  # Ignore if it's a date
        return age_str.replace("Age:", "").strip()  # Remove 'Age:' prefix and any surrounding spaces
    return None  # Return None for dates or invalid entries

# Function to clean 'Supplement Time' and remove any dates
def clean_supplement_time(supp_time_str):
    if supp_time_str and not re.match(r'\d{1,2}/\d{1,2}/\d{4}', supp_time_str):  # Ignore if it's a date
        return supp_time_str.strip()  # Just trim spaces
    return None  # Return None for dates or invalid entries

# Function to clean 'Condition' by removing "Condition:" prefix
def clean_condition(condition_str):
    if condition_str:
        return condition_str.replace("Condition:", "").strip()  # Remove 'Condition:' prefix
    return condition_str

# Function to clean 'Overall Rating' by removing "Overall rating" prefix
def clean_rating(rating_str):
    if rating_str:
        return rating_str.replace("Overall rating", "").strip()  # Remove 'Overall rating' prefix
    return rating_str

# Function to handle missing names by replacing them with 'anonymous'
def handle_name(name_str):
    if name_str is None or name_str == '' or re.match(r'\d{1,2}/\d{1,2}/\d{4}', name_str):  # If name is missing or it's a date
        return 'anonymous'
    return name_str

# Function to parse individual review sections
def parse_reviews(soup):
    # Lists to store extracted data
    names = []
    ages = []
    supplement_times = []
    conditions = []
    overall_ratings = []
    review_texts = []

    # Find all review sections
    reviews = soup.find_all('div', class_='review-details-holder')

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
                    # Detect age using regex for age ranges
                    age_match = re.search(r'Age:\s*(\d{2}-\d{2}|75 or over)', name_age_part)
                    if age_match:
                        name = name_age_part.split('Age:')[0].strip()  # Name is before "Age:"
                        age = age_match.group(1).strip()  # Extract age
                    else:
                        # No age detected, treat the entire first part as name
                        name = name_age_part

                # Check if there’s a supplement time present in the second part
                if len(parts) > 1:
                    supp_part = parts[1].strip()
                    # Check if supplement time starts with "On supplement for"
                    if supp_part.startswith('On supplement for'):
                        supplement_time = supp_part
                    else:
                        # If it doesn't match, it's probably age swapped with supplement time
                        if re.search(r'\d{2}-\d{2}|75 or over', supp_part):
                            age = supp_part  # Assign as age if format matches age
                        else:
                            supplement_time = supp_part

                # Clean up the age and supplement time format, and filter out dates
                age = clean_age(age)
                supplement_time = clean_supplement_time(supplement_time)
                name = handle_name(name)  # Handle missing or invalid names

                names.append(name)
                ages.append(age)
                supplement_times.append(supplement_time)
            else:
                names.append('anonymous')
                ages.append(None)
                supplement_times.append(None)

            # Extract condition
            condition = review.find('strong', class_='condition')
            if condition:
                cleaned_condition = clean_condition(condition.get_text(strip=True))  # Clean the condition
                conditions.append(cleaned_condition)
            else:
                conditions.append(None)

            # Extract overall rating
            overall_rating = review.find('div', class_='overall-rating')
            if overall_rating:
                cleaned_rating = clean_rating(overall_rating.get_text(strip=True))  # Clean the rating
                overall_ratings.append(cleaned_rating)
            else:
                overall_ratings.append(None)

            # Extract review text
            review_text = review.find('div', class_='description')
            if review_text:
                review_texts.append(review_text.get_text(strip=True))
            else:
                review_texts.append(None)

        except Exception as e:
            print(f"Error extracting data from a review: {e}")

    return names, ages, supplement_times, conditions, overall_ratings, review_texts

# Lists to store data for all pages
all_names = []
all_ages = []
all_supplement_times = []
all_conditions = []
all_overall_ratings = []
all_review_texts = []

# Loop through multiple pages (adjust the range for more pages)
for page in range(1, 6):  # Example: scraping the first 5 pages
    url = f"https://reviews.webmd.com/vitamins-supplements/ingredientreview-437-lemon-balm?conditionid=&sortval=1&page={page}&next_page=true"
    driver.get(url)
    time.sleep(5)  # Wait for the page to fully load

    # Parse the page content
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    names, ages, supplement_times, conditions, overall_ratings, review_texts = parse_reviews(soup)

    # Append data from this page to the main lists
    all_names.extend(names)
    all_ages.extend(ages)
    all_supplement_times.extend(supplement_times)
    all_conditions.extend(conditions)
    all_overall_ratings.extend(overall_ratings)
    all_review_texts.extend(review_texts)

# Close the browser
driver.quit()

# Create a DataFrame
data = {
    'Name': all_names,
    'Age': all_ages,
    'Supplement Time': all_supplement_times,
    'Condition': all_conditions,
    'Overall Rating': all_overall_ratings,
    'Review Text': all_review_texts
}

df = pd.DataFrame(data)

# Save the DataFrame to a CSV file
df.to_csv('webmd_reviews_cleaned.csv', index=False)

print("Scraping complete. Data saved to 'webmd_reviews_cleaned.csv'.")
