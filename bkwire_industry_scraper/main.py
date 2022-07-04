import getpass
import os
import re
import time
import urllib
import requests
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from requests_html import HTMLSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

load_dotenv()

PREFIX = r"https?://(?:www\.)?"
SITES = ["(?:[a-z]{2}\.)?linkedin.com/(?:company/)"]
BETWEEN = ["user/", "add/", "pages/", "#!/", "photos/", "u/0/"]
ACCOUNT = r"[\w\+_@\.\-/%]+"
PATTERN = r"%s(?:%s)(?:%s)?%s" % (PREFIX, "|".join(SITES), "|".join(BETWEEN), ACCOUNT)
SOCIAL_REX = re.compile(PATTERN, flags=re.I)
VERIFY_LOGIN_ID = "global-nav-search"
REMEMBER_PROMPT = "remember-me-prompt__form-primary"

# Configuration
LINKEDIN_USER_ID = os.environ.get("LINKEDIN_USER_EMAIL_ID", None)
LINKEDIN_USER_PWD = os.environ.get("LINKEDIN_USER_PASSWORD", None)

# Get free proxies for rotating
def get_free_proxies(driver):
    driver.get("https://sslproxies.org")

    table = driver.find_element(By.TAG_NAME, "table")
    thead = table.find_element(By.TAG_NAME, "thead").find_elements(By.TAG_NAME, "th")
    tbody = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")

    headers = []
    for th in thead:
        headers.append(th.text.strip())

    proxies = []
    for tr in tbody:
        proxy_data = {}
        tds = tr.find_elements(By.TAG_NAME, "td")
        for i in range(len(headers)):
            proxy_data[headers[i]] = tds[i].text.strip()
        proxies.append(proxy_data)

    list_of_proxies = []
    for record in proxies:
        list_of_proxies.append(f"{record['IP Address']}:{record['Port']}")

    return list_of_proxies


def __prompt_email_password():
    u = input("Email: ")
    p = getpass.getpass(prompt="Password: ")
    return (u, p)


def login(driver, email, password, timeout=10):
    if not email or not password:
        email, password = __prompt_email_password()
    driver.get("https://www.linkedin.com/login")
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, "username"))
    )  # email_elem = driver.find_element(By.ID, "username")
    element.send_keys(email)
    password_elem = driver.find_element(By.ID, "password")
    password_elem.send_keys(password)
    password_elem.submit()

    try:
        if driver.url == "https://www.linkedin.com/checkpoint/lg/login-submit":
            remember = driver.find_element(By.ID, REMEMBER_PROMPT)
            if remember:
                remember.submit()

        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, VERIFY_LOGIN_ID))
        )
    except:
        pass


def login_to_linkedin(email, password):
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    try:
        status = login(driver, email, password)
    except Exception as e:
        return False
    return driver


def get_industry_type_from_linkedin_search(search_query):
    industry = None

    search_query = f"site:linkedin.com {search_query} industry type"

    query = urllib.parse.quote_plus(search_query)
    # session = HTMLSession()
    response = requests.get("https://www.google.com/search?q=" + query)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.findAll("div")
    for row in table:
        if "Industries:" in row.text:
            try:
                result = re.search("Industries: (.*) Company size:", row.text)
                industry = result.group(1).split(".")[0]
                break
            except:
                continue
    return industry


def get_industry_type_from_linkedin(search_query):
    industry = None

    search_query = f"site:linkedin.com {search_query}"

    query = urllib.parse.quote_plus(search_query)
    session = HTMLSession()
    response = session.get("https://www.google.com/search?q=" + query)

    links = list(response.html.absolute_links)
    linkedin_links_list = []
    for link in links:
        if re.search(PATTERN, link):
            linkedin_links_list.append(link)

    first_link = [link for link in linkedin_links_list if "/company/" in link]
    if len(first_link) > 0:
        first_link = first_link[0]
        if "translate.google.com" in first_link:
            first_link = first_link[
                first_link.find("https", 6) : first_link.find("&prev")
            ]
        while True:
            driver = login_to_linkedin(LINKEDIN_USER_ID, LINKEDIN_USER_PWD)
            if driver != False:
                break
        time.sleep(2)
        if (
            first_link.endswith("life")
            or first_link.endswith("jobs")
            or first_link.endswith("people")
            or first_link.endswith("videos")
        ):
            first_link = "/".join(first_link.split("/")[:-1])

        try:
            driver.get(first_link)
        except:
            pass

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "h1"
                    # "/html/body/div[6]/div[3]/div/div[2]/div/div[2]/main/div[1]/section/div/div[2]/div[1]/div[1]/div[2]/div/h1/span",
                )
            )
        )
        try:
            industry = driver.find_element(
                By.CSS_SELECTOR,
                ".org-top-card-summary-info-list__info-item",
            ).text
        except Exception as e:
            print(e)
            print("Industry element doesn't found on about page of the company")

    return industry


def get_industry_type_from_google(search_query):
    pass


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"


@app.route("/")
def index():
    return


@app.route("/industry/")
def industry():
    company_name = request.form["comapny_name"]
    street = request.form.get("street", "")
    city = request.form.get("city", "")
    state = request.form.get("state", "")
    country = request.form.get("country", "")
    search_query = company_name
    li = [street, city, state, country]
    for data in li:
        if data == "":
            continue
        search_query += " " + data
    industry = get_industry_type_from_linkedin_search(search_query)
    if not industry:
        industry = get_industry_type_from_google(search_query)
    return jsonify({"industry": industry})
