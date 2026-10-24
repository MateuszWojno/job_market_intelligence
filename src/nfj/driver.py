from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless=False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    return webdriver.Chrome(options=options)
