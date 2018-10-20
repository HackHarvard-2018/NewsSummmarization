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
import time
from time import mktime
import pandas as pd
import numpy as np
import json

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
        article_headers = [tag.text for tag in homepage_html.find_all("a", {"class": "gs-c-promo-heading"})]
        article_href = [tag['href'] for tag in homepage_html.find_all("a", {"class": "gs-c-promo-heading"})]
        return article_headers, article_href
    except:
        print("Found an error while getting latest articles' URL!")

if __name__ == '__main__':
    # Instantiates a firebase client
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()

    # News Website
    homepage = "https://www.bbc.com/news"

    with Pool(6) as pool:
        print("Started Pooling Process...")

        article_objs = []
        # article_details = fetch_latest_articles(homepage)
        fetch_latest_articles(homepage)
