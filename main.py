import requests
from bs4 import BeautifulSoup
import os
import re
import time
from apscheduler.schedulers.blocking import BlockingScheduler
import tweepy
from tqdm import tqdm
from keep_alive import keep_alive
keep_alive()

api_key = os.environ.get('api_key')
api_secret = os.environ.get('api_secret')
bearer_token = repr(os.environ.get('bearer_token'))
access_token = os.environ.get('access_token')
access_token_secret = os.environ.get('access_token_secret')

def read_titles_from_file(filename):
    titles_set = set()
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                titles_set.add(line.strip())
    except FileNotFoundError:
        pass  # If file not found, return an empty set
    return titles_set

def write_titles_to_file(titles_set, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        for title in titles_set:
            file.write(f"{title}\n")


def scrape(url):
    global sold_out_set
    global available_set
    i=1
    while True:

        cur_url = url + "?page=" + str(i)
        headers = {"User-Agent": "Content-Scraping"}
        response = requests.get(cur_url, headers=headers)

        if not response.ok:
            print('Status Code:', response.status_code)
            #raise Exception('Failed to fetch')
            continue
        soup = BeautifulSoup(response.text, 'html.parser')
        # Use regular expression to find all div elements with the desired id pattern
        products = soup.find_all('div', id=re.compile(r'^ProductInfo-\d+$'))
        if not products:
            break
        for product in products:
            title =""
            price =""
            a_tag = product.find('a')
            href = "https://shop.gracieabrams.com"
            if a_tag:
                href = href+ a_tag.get('href')
            price = product.find('span', class_= "price__current")
            if price:
                price = price.text.strip()
            title_div = product.find('div', class_="card__title card__text card__details--wrapper relative block placement-below text-left justify-start c-text-primary")
            if title_div:
                title = title_div.text.strip()
            if "Sold out" not in product.get_text():
                available_set.add((title, price, href))
            else:
                sold_out_set.add((title, price, href))
              
        i+=1
        time.sleep(2)


def main_function():
    global sold_out_set
    global available_set
    urls = ["https://shop.gracieabrams.com/collections/all", "https://shop.gracieabrams.com/collections/vinyl", "https://shop.gracieabrams.com/collections/cd", "https://shop.gracieabrams.com/collections/the-secret-of-us", "https://shop.gracieabrams.com/collections/good-riddance", "https://shop.gracieabrams.com/collections/this-is-what-it-feels-like"]
    sold_out_set = set()
    available_set = set()
    for url in tqdm(urls):
        scrape(url)
        time.sleep(10)
    
    # Load previous data
    previous_available_titles = read_titles_from_file('available_products.txt')
    previous_sold_out_titles = read_titles_from_file('sold_out_products.txt')
    
    # Extract titles from current sets
    current_available_titles = {title for title, price, href in available_set}
    current_sold_out_titles = {title for title, price, href in sold_out_set}
    
    # Find new products, restocked products, and newly sold-out products
    new_products = current_available_titles - previous_available_titles - previous_sold_out_titles
    restocked_products = current_available_titles & previous_sold_out_titles
    newly_sold_out_products = current_sold_out_titles - previous_sold_out_titles

    client = tweepy.Client(bearer_token, api_key, api_secret, access_token, access_token_secret)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api = tweepy.API(auth)


    # Print changes for potential Twitter updates
    print("New Products:")
    for title in new_products:
        product = next(item for item in available_set if item[0] == title)
        print(product)
        try:
            message = "New Product Added: " + title + "-" + product[1] + "\n" + product[2]
            #api.update_status(data_str)
            client.create_tweet(text = message)
            print("Tweeted successfully!")
        except Exception as e:
            print("Error during tweeting:", e)
        time.sleep(30)
    
    print("Restocked Products:")
    for title in restocked_products:
        product = next(item for item in available_set if item[0] == title)
        print(product)
        try:
            message = "Product Back In Stock: " + title + "-" + product[1] + "\n" + product[2]
            #api.update_status(data_str)
            client.create_tweet(text = message)
            print("Tweeted successfully!")
        except Exception as e:
            print("Error during tweeting:", e)
        time.sleep(30)
    
    print("Newly Sold Out Products:")
    for title in newly_sold_out_products:
        product = next(item for item in sold_out_set if item[0] == title)
        print(product)
        try:
            message = "Product Sold Out: " + title + "-" + product[1] + "\n" + product[2]
            #api.update_status(data_str)
            client.create_tweet(text = message)
            print("Tweeted successfully!")
        except Exception as e:
            print("Error during tweeting:", e)
        time.sleep(30)
    
    # Update files
    write_titles_to_file(current_available_titles, 'available_products.txt')
    write_titles_to_file(current_sold_out_titles, 'sold_out_products.txt')

if __name__ == '__main__':
    main_function()
    scheduler = BlockingScheduler()
    scheduler.add_job(main_function, 'interval', minutes=15)
    scheduler.start()
