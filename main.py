# Main file for CCrawler
import json
import sys
import time
from loguru import logger as log
from selenium import webdriver as wd
from splinter import Browser as Sbrowser


def setupLogging():
    """This function sets up a default logger for the crawler."""
    log.remove()
    log.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    log.add("logs/logs.log", rotation="1 day")
    log.info("Starting log...")


def setupDriver(hless=False):
    """Returns a setup browser from splinter, ready for scaping.

    Args:
        hless (bool, optional): Should the browser run headless. Defaults to False.

    Returns:
        WebDriver: A splinter browser driver.
    """
    browserOptions = wd.ChromeOptions()
    browserOptions.add_argument("--lang=en-GB")
    browserOptions.add_experimental_option(
        "prefs", {"intl.accept_languages": "en,en_GB"}
    )
    browserOptions.headless = hless
    if hless:
        log.info("Starting a headless chrome drier...")
    else:
        log.info("Starting a visible chrome driver...")
    return Sbrowser("chrome", options=browserOptions)


def findCookieNotice(browser):
    """A function that searched for a GDPR/Cookie consent notice.

    Args:
        browser ([type]): [description]
    """
    # Todo stuff here with browser.


@log.catch  # Lets be sure to catch all exceptions!
def startCrawl(url, browser):
    """Starts the crawler at url, with driver browser.

    Args:
        url ([type]): The url to start the crawl at.
        browser ([type]): the WebDriver browser to use.
    """
    log.info("Setting up crawler for {}...", url)
    # Clean the browser from previous run
    log.debug("Cleaning cookies before run.")
    browser.driver.delete_all_cookies()
    # Navigate to the page.
    browser.visit(url)
    time.sleep(2)  # A sleep is needed for selenium to finish load.
    # Save down the cookies.
    allCookies = browser.cookies.all()
    # Take a screenshot.
    # Save down dict
    # Find cookie notice.
    findCookieNotice(browser)


if __name__ == "__main__":
    # Setup logging and a basic browser driver.
    setupLogging()
    browser = setupDriver(False)
    # Fetch the urls to be crawled.
    urls = ["https://yahoo.com", "https://svt.se"]
    for url in urls:
        startCrawl(url, browser)
