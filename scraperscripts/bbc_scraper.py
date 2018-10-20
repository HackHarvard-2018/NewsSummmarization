# For directory management
import sys
sys.path.insert(0, '../')

# Imports firebase
import pyrebase
from config import config

# Importing required libraries for scraping
import ssl
import re
import requests
from multiprocessing import Pool
from multiprocessing import Process
from bs4 import BeautifulSoup as BS

# Importing required libraries for wordprocessing
from datetime import datetime as dt
from pytz import timezone
import pytz
import time
from time import mktime
import pandas as pd
import numpy as np
import json

# Forming JSON objects
import uuid

class Article:
    def __init__ (self, header, articleurl):
        self.header = header
        self.articleurl = articleurl
        self.articlecontent = ""

    def get_header(self):
        return self.header

    def get_articleurl(self):
        return self.articleurl

    def get_articlecontent(self):
        return self.articlecontent

    def store_articlecontent(self, articlecontent):
        self.articlecontent = articlecontent

def fetch_latest_articles(homepage):
    try:
        r = requests.get(homepage, timeout=10)
        homepage_html = BS(r.content, "lxml")
        main_article_header = homepage_html.find_all("span", {"class": "title-link__title-text"})[0].text
        main_article_link = (homepage_html.find("div", {"class": "buzzard__links-list"})).find("a")["href"]

        secondary_article_headers = [tag.find("span", {"class": "title-link__title-text"}).text for tag in homepage_html.find_all("div", {"class": "pigeon-item__body"})]
        secondary_article_links = [tag.find("a")["href"] for tag in homepage_html.find_all("div", {"class": "pigeon-item__body"})]
        all_article_headers = [main_article_header] + secondary_article_headers
        all_article_links = [main_article_link] + secondary_article_links
        return all_article_headers, all_article_links
    except:
        print("Found an error while getting latest articles' URL!")

def fetch_article_content(articleobj):
    try:
        r = requests.get(articleobj.get_articleurl(), timeout=10)
        article_html = BS(r.content, "lxml")
        # Remove embedded content eg. tweets, videos
        caveats = ['Share this with', 'Email', 'Facebook', 'Messenger', 'Twitter', 'Pinterest', 'WhatsApp', 'LinkedIn', 'Copy this link',
        'End of Twitter post', 'These are external links and will open in a new window']
        for div in article_html.find_all("div", {'class':'embed-twitter'}) or article_html.find_all("div", {'class':'off-screen'}):
            div.decompose()
        article_content = [tag.text for tag in article_html.find_all("p") if tag.text not in caveats]
        article_prose = ' '.join(article_content)
        articleobj.store_articlecontent(article_prose)
        # print(article_prose)
        return articleobj
    except:
        print("Found an error while getting article's content!")

if __name__ == '__main__':
    # Instantiates a firebase client
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()
    utc = pytz.utc
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    curr_time = dt.utcnow()

    # News Website
    homepage = "https://www.bbc.com/news/world"
    start_url = "https://www.bbc.com"

    with Pool(6) as pool:
        print("Started Pooling Process...")

        article_objs = []
        article_details = fetch_latest_articles(homepage)
        for article in range(len(article_details[0])):
            article_objs.append(Article(article_details[0][article], start_url + article_details[1][article]))

        test_obj = article_objs[1]
        pool1 = pool.map(fetch_article_content, article_objs)

    all_articles = []
    headers = {'content-type': 'application/json'}
    for article in pool1[:2]:
        try:
            data = {
                'articles': [
                    {
                        'text': article.get_articlecontent()
                    }
                ],
                'summary_length_words': 60
            }
            response = requests.post(
                url = "https://coherent-summarization-service.staging.agolo.com/summarization",
                data = json.dumps(data),
                headers=headers
            )
            # response = json.response.sentences
            # print(response.content)
            content = json.loads(response.content)
            print(content)
            summary = ' '.join(content['sentences'])
            print(summary)

            # Build Article Json Object
            article_data = {
                'mainText': article.get_header() + "... " + summary,
                'redirectionUrl': article.get_articleurl(),
                'titleText': article.get_header(),
                'uid': uuid.uuid1().__str__(),
                'updateDate': dt(dt.utcnow().year, dt.utcnow().month, dt.utcnow().day, dt.utcnow().hour, dt.utcnow().minute, dt.utcnow().second, tzinfo=pytz.utc).strftime(fmt)
            }
            print(type(article_data))
            print(article_data)
            all_articles.append(article_data)
        except:
            print("Error in calling API!")
    db.child("world").set(all_articles)

    print("Done with scraping and pushing to Firebase!")
