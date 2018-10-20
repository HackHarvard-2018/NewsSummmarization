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
        self.thumbnail = ""

    def get_header(self):
        return self.header

    def get_articleurl(self):
        return self.articleurl

    def get_articlecontent(self):
        return self.articlecontent

    def get_thumbnail(self):
        return self.thumbnail

    def store_articlecontent(self, articlecontent):
        self.articlecontent = articlecontent

    def store_articlethumbnail(self, articlethumbnail):
        self.articlethumbnail = articlethumbnail

def get_info(article_chunk):
    uri_start = article_chunk.find("uri") + 6
    uri_end = article_chunk.find("headline") - 3

    headline_start = article_chunk.find("headline") + 11
    headline_end = article_chunk.find("thumbnail") - 3

    thumbnail_start = article_chunk.find("thumbnail") + 12
    thumbnail_end = article_chunk.find("duration") - 3

    return uri_start, uri_end, headline_start, headline_end, thumbnail_start, thumbnail_end

def fetch_latest_articles(extension, homepage): #https://www.cnn.com/
    try:
        headers = {'user-agent': 'my-app/0.0.1'}
        r = requests.get(homepage, headers=headers, timeout=10)
        pattern = re.compile(r'\.val\("([^@]+@[^@]+\.[^@]+)"\);', re.MULTILINE | re.DOTALL)
        homepage_html = BS(r.content, "lxml")
        article_scripts = homepage_html.find_all("script")[9].text
        start = article_scripts.find("articleList") + 13
        end = article_scripts.find("registryURL")
        articles = re.split("\",\"layout\":\"\"},{\"", article_scripts[start:end])
        # articles = articles[:5]
        all_uri = []
        all_headline = []
        all_thumbnail = []
        for article in articles:
            uri_start, uri_end, headline_start, headline_end, thumbnail_start, thumbnail_end = get_info(article)
            uri = extension + article[uri_start:uri_end]
            headline = article[headline_start:headline_end]
            # thumbnail = article[thumbnail_start:thumbnail_end]
            all_uri.append(uri)
            all_headline.append(headline)
            # all_thumbnail.append(thumbnail)

        return all_headline, all_uri, all_thumbnail
    except:
        print("Found an error while getting latest articles' URL!")

def fetch_article_content(articleobj):
    try:
        r = requests.get(articleobj.get_articleurl(), timeout=10)
        article_html = BS(r.content, "lxml")
        article_content = [tag.text for tag in article_html.find_all("div", {"class": "zn-body__paragraph"})]
        article_prose = ' '.join(article_content)
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

    # News Website
    homepage = "https://www.cnn.com/politics"
    news_extension = "https://www.cnn.com"

    with Pool(6) as pool:
        print("Started Pooling Process...")

        article_objs = []
        article_details = fetch_latest_articles(news_extension, homepage)
        for article in range(len(article_details[0])):
            article_objs.append(Article(article_details[0][article], article_details[1][article]))

        # test_obj = article_objs[0]
        # fetch_article_content(test_obj)
        pool1 = pool.map(fetch_article_content, article_objs)

    all_articles = []
    headers = {'content-type': 'application/json'}
    for article in pool1[:3]:
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
                'updateDate': dt(dt.utcnow().year, dt.utcnow().month, dt.utcnow().day, dt.utcnow().hour, dt.utcnow().minute, dt.utcnow().second, tzinfo=pytz.utc).strftime(fmt)
            }
            print(type(article_data))
            print(article_data)
            all_articles.append(article_data)
        # except:
        #     print("Error in calling API!")
    db.child("politics").set(all_articles)

    print("Done with scraping and pushing to Firebase!")
