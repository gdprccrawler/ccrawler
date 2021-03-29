# Main file for CCrawler
import json
import sys
import time
import os
import string
import random
import pprint
from loguru import logger as log
from selenium import webdriver as wd
from splinter import Browser as Sbrowser


def genRunId(url):
    """Takes in url, and turns it into a run ID for usage in the program."""
    url = url.replace("https://", "").replace("http://", "").split(".")[0]
    id = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )
    return url + "-" + id


def setupLogging():
    """This function sets up a default logger for the crawler."""
    log.remove()
    extra = {"url": "NURL"}
    log.configure(extra=extra)
    log.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | {extra[url]} |<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    log.add(
        "logs/logs.log",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | {extra[url]} |<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        rotation="1 day",
    )
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


def openDropdowns(browser):
    """A function to open all dropdowns on a page, used before taking screenshot.

    Args:
        browser (WebDriver): The webdriver browser to use.
    """
    # Use js to open all dropdowns
    browser.execute_script(
        "document.querySelectorAll('.chevron').forEach(e => e.click())"
    )


def findByButtonString(browser, text):  # Return first element found
    foundElements = browser.find_by_xpath(
        f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'{text}')]"
    )
    if foundElements:
        return foundElements.first
    else:
        return None


def findByInputString(browser, text):  # Return first element found
    foundElements = browser.find_by_xpath(f"//input[contains(@value,'{text}')]")
    if foundElements:
        return foundElements.first
    else:
        return None


def checkCookieIframe(browser):  # Function to check if there is a iframe
    try:
        foundIframes = browser.find_by_tag("iframe").find_by_xpath(
            "//*[contains(@title, 'onsent')]"
        )  # onsent used for C/consent.
        if foundIframes:
            log.debug("Jumping into a found iframe...")
            browser.driver.switch_to.frame(foundIframes.first["id"])
    except:
        log.debug("Could not find an iframe.")


def findApproveButton(browser):
    """Function that tries to find approve button on current page.

    Args:
        browser ([type]): The browser driver.

    Returns:
        [type]: Element found, else none.
    """
    log.debug("Looking for approve button.")
    strings = ["pprove", "ccept", "gree", "lose", "odkänner", "örstår", "äng"]
    for s in strings:
        # Look for buttons with that string.
        acceptButton = findByButtonString(browser, s)
        if acceptButton is None:  # Only check for input if no button is found.
            acceptButton = findByInputString(browser, s)
        if acceptButton:
            log.debug("Found an approve button on string {}, returning element.", s)
            return acceptButton
    log.debug("Did not find an approve button on page.")
    return None


def findPreferenceButton(browser):
    """Function that tries to find settings button on current page.

    Args:
        browser ([type]): The browser driver.

    Returns:
        [type]: Element found, else none.
    """
    log.debug("Looking for settings button.")
    strings = ["configure", "settings", "manage", "inställningar"]
    for s in strings:
        linksToManage = findByButtonString(browser, s)  # Look by button name.
        if linksToManage is None:
            linksToManage = browser.links.find_by_partial_text(s)  # Look by hefs.
        if linksToManage:
            log.debug("Found an settings button on string {}, returing element", s)
            return linksToManage
    # Check one last time for links containing string cookie.
    lastCheck = browser.find_by_xpath("//a[contains(@href,'cookie')]")
    if lastCheck:
        log.debug(
            "Found an settings link by checking for links containing string cookie"
        )
        return lastCheck.first
    log.debug("Did not find an settings button on page.")
    return None


def findCookieNotice(browser):
    """A function that searched for a GDPR/Cookie consent notice.

    Args:
        browser ([type]): [description]
    """
    path = os.path.abspath(os.getcwd())
    gid = genRunId(browser.url)
    checkCookieIframe(browser)
    apprBtn = findApproveButton(browser)
    prefsBtn = findPreferenceButton(browser)
    screenshot64 = browser.driver.get_screenshot_as_base64()
    cookies = browser.cookies.all()
    # Look for accept all button.
    # Make nicer looking finder.
    obj = {
        "url": browser.url,  # The current url
        "cookies": cookies,  # The cookies before any clicking on page.
        "apprBtn": apprBtn,  # The approve button, if any.
        "prefsBtn": prefsBtn,  # The prefs button, if any.
        "prefsNewPage": prefsBtn["href"]
        is not None,  # If the prefs are located on new page.
        # "screenshot64": screenshot64,
    }
    pprint.pprint(obj)
    return obj


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
    # Take a screenshot.
    # Save down dict
    # Find cookie notice.
    info = findCookieNotice(browser)
    pprint.pprint(info)
    log.info("Url to cookie settings is:{}", info["prefsBtn"].click())
    time.sleep(10)


if __name__ == "__main__":
    # Setup logging and a basic browser driver.
    setupLogging()
    browser = setupDriver(False)
    # Fetch the urls to be crawled.
    urls = ["https://cnn.com"]
    for url in urls:
        with log.contextualize(url=url):
            startCrawl(url, browser)
    browser.quit()