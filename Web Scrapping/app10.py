import asyncio
import aiohttp
from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

# Patch the asyncio loop to allow it to run inside Flask's threaded environment
import nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)

# Asynchronous function to fetch a single page of reviews
async def fetch_page(session, url, page):
    try:
        page_url = f"{url}&pageNumber={page}"
        async with session.get(page_url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            reviews = soup.find_all('div', {'data-hook': 'review'})
            
            # Parse the reviews
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
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []

# Asynchronous function to scrape multiple pages concurrently
async def scrape_amazon_async(url, max_reviews=1000):
    async with aiohttp.ClientSession() as session:
        max_pages = (max_reviews // 10) + 1  # Assuming 10 reviews per page
        tasks = []
        
        # Create a list of tasks to fetch multiple pages asynchronously
        for page in range(1, max_pages + 1):
            tasks.append(fetch_page(session, url, page))
        
        all_reviews = []
        for task in asyncio.as_completed(tasks):
            result = await task
            all_reviews.extend(result)
            
            # Stop if we've collected the target number of reviews
            if len(all_reviews) >= max_reviews:
                break

        return all_reviews[:max_reviews]

# Function to run asyncio in a synchronous environment
def scrape_amazon(url, max_reviews=1000):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(scrape_amazon_async(url, max_reviews))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    
    if 'amazon.com' in url:
        reviews = scrape_amazon(url)

        # Save the reviews into a DataFrame and export to a CSV
        df = pd.DataFrame(reviews, columns=['Name', 'Rating', 'Review Text'])
        output_file = 'amazon_reviews_1000_async.csv'
        df.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True, mimetype='text/csv')
    else:
        return "Website not supported yet."

if __name__ == '__main__':
    app.run(debug=True)
