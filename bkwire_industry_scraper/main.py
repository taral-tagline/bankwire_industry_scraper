import urllib
import re
import time
import getpass
import os
import random
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from requests_html import HTMLSession
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

PREFIX = r"https?://(?:www\.)?"
SITES = ["(?:[a-z]{2}\.)?linkedin.com/(?:company/|in/|pub/)"]
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

    time.sleep(2)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )  # email_elem = driver.find_element(By.ID, "username")
    element.send_keys(email)

    time.sleep(2)
    password_elem = driver.find_element(By.ID, "password")
    password_elem.send_keys(password)

    time.sleep(2)
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
    driver = webdriver.Chrome(ChromeDriverManager().install())
    options = Options()
    # options.headless = True
    free_proxies = get_free_proxies(driver)
    PROXY_STR = random.choice(free_proxies)
    options.add_argument("--proxy-server=%s" % PROXY_STR)
    try:
        status = login(driver, email, password)
    except Exception as e:
        return False
    return driver


def find_industry_from_about_page(driver, details_xpath):
    result = None
    try:
        time.sleep(2)
        if driver.find_element(By.XPATH, details_xpath + "dt[2]").text == "Industry":
            result = driver.find_element(By.XPATH, details_xpath + "dd[2]").text
    except NoSuchElementException:
        print("Element doesn't found! Moving to the next element...")

    try:
        time.sleep(2)
        if driver.find_element(By.XPATH, details_xpath + "dt[3]").text == "Industry":
            result = driver.find_element(By.XPATH, details_xpath + "dd[3]").text
    except NoSuchElementException:
        print("Element doesn't found! Moving to the next element...")

    try:
        time.sleep(2)
        if driver.find_element(By.XPATH, details_xpath + "dt[1]").text == "Industry":
            result = driver.find_element(By.XPATH, details_xpath + "dd[1]").text
    except NoSuchElementException:
        print("Industry element doesn't found on about page of the company")

    return result


def get_industry_type(search_query):
    data = {}
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
        is_clicked_about_page = False
        for _ in range(5):
            try:
                driver.get(first_link)
                time.sleep(2)
                driver.find_element(
                    By.XPATH,
                    "/html/body/div[6]/div[3]/div/div[2]/div/div[2]/main/div[1]/section/div/div[2]/div[2]/nav/ul/li[2]/a",
                ).click()
                is_clicked_about_page = True
            except:
                continue
            if is_clicked_about_page:
                break

        try:
            details_xpath = "/html/body/div[6]/div[3]/div/div[2]/div/div[2]/main/div[2]/div/div[2]/div[1]/section/dl/"
            data["Industry"] = find_industry_from_about_page(driver, details_xpath)
            if data["Industry"] == None:
                raise NoSuchElementException
        except NoSuchElementException:
            details_xpath = "/html/body/div[5]/div[3]/div/div[2]/div/div[2]/main/div[2]/div/div[2]/div[1]/section/dl/"
            data["Industry"] = find_industry_from_about_page(driver, details_xpath)
        except:
            try:
                time.sleep(2)
                driver.find_element(
                    By.XPATH,
                    "/html/body/main/section[1]/div/section[1]/div/dl/div[2]/dt",
                ).text == "Industries"
                result = driver.find_element(
                    By.XPATH,
                    "/html/body/main/section[1]/div/section[1]/div/dl/div[2]/dd",
                ).text
            except NoSuchElementException:
                print("Industry element doesn't found on about page of the company")
    else:
        return data
    return data


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
    search_query = "site:linkedin.com " + company_name
    li = [street, city, state, country]
    for data in li:
        if data == "":
            continue
        search_query += " " + data
    print(search_query)
    company_profile = get_industry_type(search_query)

    return jsonify(company_profile)
