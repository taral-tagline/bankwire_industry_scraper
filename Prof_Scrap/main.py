from flask import Flask, render_template, request, jsonify
import urllib
from requests_html import HTMLSession
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from selenium.webdriver.chrome.options import Options
import getpass
import json

PREFIX = r"https?://(?:www\.)?"
SITES = ["(?:[a-z]{2}\.)?linkedin.com/(?:company/|in/|pub/)"]
BETWEEN = ["user/", "add/", "pages/", "#!/", "photos/", "u/0/"]
ACCOUNT = r"[\w\+_@\.\-/%]+"
PATTERN = r"%s(?:%s)(?:%s)?%s" % (PREFIX, "|".join(SITES), "|".join(BETWEEN), ACCOUNT)
SOCIAL_REX = re.compile(PATTERN, flags=re.I)
VERIFY_LOGIN_ID = "global-nav-search"
REMEMBER_PROMPT = "remember-me-prompt__form-primary"

options = Options()
options.headless = True


def __prompt_email_password():
    u = input("Email: ")
    p = getpass.getpass(prompt="Password: ")
    return (u, p)


def login(driver, email, password, timeout=10):
    if not email or not password:
        email, password = __prompt_email_password()

    driver.get("https://www.linkedin.com/login")
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )

    email_elem = driver.find_element(By.ID, "username")
    email_elem.send_keys(email)

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
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    try:
        status = login(driver, email, password)
    except Exception as e:
        return False
    return driver


def get_industry_type(search_query):
    company_profile = {"company_url": None, "company_industry_type": None}
    query = urllib.parse.quote_plus(search_query)
    session = HTMLSession()
    response = session.get("https://www.google.co.uk/search?q=" + query)

    links = list(response.html.absolute_links)
    for link in links:
        if re.search(PATTERN, link):
            first_link = link
            if "company" in first_link:
                while True:
                    driver = login_to_linkedin("taral.tagline@gmail.com", "Tagline@123")
                    if driver != False:
                        break
                if (
                    first_link.endswith("life")
                    or first_link.endswith("jobs")
                    or first_link.endswith("people")
                    or first_link.endswith("videos")
                ):
                    first_link = "/".join(first_link.split("/")[:-1])
                company_profile["company_url"] = first_link
                driver.get(first_link)
                time.sleep(1)
                driver.find_element(
                    By.XPATH,
                    "/html/body/div[6]/div[3]/div/div[2]/div/div[2]/main/div[1]/section/div/div[2]/div[2]/nav/ul/li[2]/a",
                ).click()
                details_xpath = "/html/body/div[6]/div[3]/div/div[2]/div/div[2]/main/div[2]/div/div[2]/div[1]/section/dl/"
                time.sleep(1)
                if (
                    driver.find_element(By.XPATH, details_xpath + "dt[2]").text
                    == "Industry"
                ):
                    result = driver.find_element(By.XPATH, details_xpath + "dd[2]").text
                    company_profile["company_industry_type"] = result
                elif (
                    driver.find_element(By.XPATH, details_xpath + "dt[3]").text
                    == "Industry"
                ):
                    result = driver.find_element(By.XPATH, details_xpath + "dd[3]").text
                    company_profile["company_industry_type"] = result
                break
    return company_profile


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        company_name = request.form["comapny_name"]
        city = request.form["city"]
        state = request.form["state"]
        street = request.form["street"]

        search_query = (
            "linkedin.com company "
            + company_name
            + ", "
            + city
            + ", "
            + state
            + ", "
            + street
        )
        company_profile = get_industry_type(search_query)
        json_object = json.dumps(company_profile, indent=4)

        return jsonify(json_object)
    return render_template("index.html")
