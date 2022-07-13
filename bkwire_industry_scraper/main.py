import re
import urllib
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from fresh_useragent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from random import choice
from getproxies import get_proxies

proxies = get_proxies()


def get_industry_type_from_linkedin_search(search_query):
    industry = None

    # Prepare a search query for linkedin
    search_query = f"site:linkedin.com {search_query} industry type"

    query = urllib.parse.quote_plus(search_query)
    # session = HTMLSession()

    # Add user agent
    userAgent = UserAgent()
    print("+" * 100)
    print("User Agent:- ", userAgent)
    headers = {"user-agent": userAgent}

    # Add proxies
    while True:
        try:
            proxy = choice(proxies)
            print("Proxy currently being used: {}".format(proxy))
            response = requests.get(
                "https://www.google.com/search?q=" + query,
                proxies={str(proxy).split(":")[0]: proxy},
                headers=headers,
                timeout=7,
            )
            break
            # if the request is successful, no exception is raised
        except Exception as e:
            print(e)
            print("Connection error, looking for another proxy")
            pass
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.findAll("div")

    for row in table:
        if "Industries:" in row.text:
            try:
                result = re.search("Industries: (.*) Company size:", row.text)
                if (
                    ";" in result.group(1)
                    and "."
                    not in result.group(1)[: result.group(1).find("Company size:")]
                ):
                    industry = result.group(1).split(";")[0].strip()
                    break
                else:
                    industry = result.group(1).split(".")[0]
                    break
            except:
                continue
    return industry


def get_industry_type_from_google(search_query):
    # Selenium Driver Headless Chrome
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    industry = None

    # Selenium get the google URL
    query = urllib.parse.quote_plus(search_query)
    url = "http://www.google.com/maps/search/" + query
    driver.get(url)

    # Find for the company/industry type element and get the value.
    try:
        industry = driver.find_element(
            By.CSS_SELECTOR, "button[jsaction='pane.rating.category']"
        ).text

    except NoSuchElementException:
        try:
            industry = driver.find_element(
                By.CSS_SELECTOR,
                "#QA0Szd > div > div > div.w6VYqd > div.bJzME.tTVLSc > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.ecceSd > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.ecceSd > div:nth-child(3) > div > div.bfdHYd.Ppzolf.OFBs3e > div.lI9IFe > div.y7PRA > div > div > div > div:nth-child(4) > div:nth-child(2) > span > jsl > span:nth-child(2)",
            ).text
        except:
            print("Industry type doesn't found on google business!")

    return industry


def get_industry_news_links_from_google_search(industry_type):
    search_query = f"latest {industry_type} industry news"
    news_links = []
    # Add user agent
    userAgent = UserAgent()
    headers = {"user-agent": userAgent}
    params = {
        "q": search_query,
        "tbm": "nws",
        "hl": "en",
    }

    response = requests.get(
        "https://www.google.com/search", headers=headers, params=params
    )
    print("+" * 100)
    print(response.url)
    print("+" * 100)

    soup = BeautifulSoup(response.content, "html.parser")
    count = 0
    for a in soup.find_all("a", class_="WlydOe", href=True):
        date_published = a.find("div", class_="OSrXXb ZE0LJd").contents[0].text
        hours_check = re.findall("hours ago", date_published)
        days_check = re.search("[1-2] (day|days) ago", date_published)
        if hours_check or days_check:
            print("+" * 100)
            print(date_published)
            news_links.append(a["href"])
            count = count + 1
        if count == 5:
            break
    return news_links


app = Flask(__name__)


@app.route("/")
def index():
    return "Industry Scraper API"


@app.route("/industry/")
def industry():
    company_name = request.form["company_name"]
    street = request.form.get("street", "")
    city = request.form.get("city", "")
    state = request.form.get("state", "")
    country = request.form.get("country", "")

    # Prepare a Search Query for Linkedin and Google.
    search_query = company_name + " ".join([street, city, state, country])

    # First check in the linkedin for Industry
    industry = get_industry_type_from_linkedin_search(search_query)

    # If industry not found in linkedin and then search in the Google
    if industry is None:
        industry = get_industry_type_from_google(search_query)

    return jsonify({"industry": industry})


@app.route("/news/")
def news():
    industry_type = request.form["industry_name"]
    news_links = get_industry_news_links_from_google_search(industry_type)
    return jsonify({"News_Links": news_links})
