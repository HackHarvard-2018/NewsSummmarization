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
        article_headers = [re.sub('\t', '', re.sub('\n', '', tag.text)) for tag in homepage_html.find_all("a", {"class": "post-block__title__link"})]
        article_href = [tag['href'] for tag in homepage_html.find_all("a", {"class": "post-block__title__link"})]
        return article_headers, article_href
    except:
        print("Found an error while getting latest articles' URL!")

def fetch_article_content(articleobj):
    try:
        r = requests.get(articleobj.get_articleurl(), timeout=10)
        article_html = BS(r.content, "lxml")
        # Remove embedded content eg. tweets, videos
        for div in article_html.find_all("div", {'class':'embed'}):
            div.decompose()
        article_content = [para.text for para in (article_html.find_all("div", {"class": "article-content"})[0]).find_all("p")]
        article_prose = ''.join(article_content)
        articleobj.store_articlecontent(article_prose)
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

    # News website
    homepage = "https://techcrunch.com/"

    with Pool(6) as pool:
        print("Started Pooling Process...")

        article_objs = []
        article_details = fetch_latest_articles(homepage)
        for article in range(len(article_details[0])):
            article_objs.append(Article(article_details[0][article], article_details[1][article]))

        # test_obj = article_objs[]
        pool1 = pool.map(fetch_article_content, article_objs)
        # print(pool1[1].get_articlecontent())

    all_articles = []
    headers = {'content-type': 'application/json'}
    for article in pool1[:2]:
        # try:
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
                'updateDate': dt(curr_time.year, curr_time.month, curr_time.day, curr_time.hour, curr_time.minute, curr_time.second, tzinfo=pytz.utc).strftime(fmt)
            }
            print(type(article_data))
            print(article_data)
            all_articles.append(article_data)
        # except:
        #     print("Error in calling API!")
    db.child("techcrunch").set(all_articles)

    print("Done with scraping and pushing to Firebase!")
