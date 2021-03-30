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

mainPath = os.path.abspath(os.getcwd())


def genRunId(url):
    """Takes in url, and turns it into a run ID for usage in the program."""
    url = url.replace("https://", "").replace("http://", "").replace(".", "-")
    id = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(4)
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


def openDropdowns(b):
    """A function to open all dropdowns on a page, used before taking screenshot.

    Args:
        b (WebDriver): The webdriver browser to use.
    """
    # Use js to open all dropdowns
    b.execute_script("document.querySelectorAll('.chevron').forEach(e => e.click())")


def checkCookieIframe(browser):  # Function to check if there is a iframe
    try:
        foundIframes = browser.find_by_tag("iframe").find_by_xpath(
            "//*[contains(@title, 'onsent')]"
        )  # onsent used for C/consent.
        if foundIframes:
            browser.driver.switch_to.frame(foundIframes.first["id"])
            return True
    except:
        return False


def screenshotElement(elem, dst):  # Function to screenshot current element to path
    try:
        if not os.path.exists(os.path.dirname(dst)):  # Make path if not exists
            os.makedirs(os.path.dirname(dst))
        tmpImg = elem.screenshot(dst)  # Take a screenshot
        os.rename(tmpImg, dst)  # Move to correct filename.
        log.debug("Took screenshot of element!")
        return dst
    except:
        e = sys.exc_info()[0]
        log.error("Could not screenshot element, error: {}", e)


def screenshotPage(b, dst):  # Function to screenshot current page to path
    try:
        if not os.path.exists(os.path.dirname(dst)):  # Make path if not exists
            os.makedirs(os.path.dirname(dst))
        tmpImg = b.screenshot(dst, full=True)  # Take a screenshot
        os.rename(tmpImg, dst)  # Move to correct filename.
        log.debug("Took screenshot of page!")
        return dst
    except:
        e = sys.exc_info()[0]
        log.error("Could not screenshot page, error: {}", e)


def findAppr(b):  # Return first element found
    m = [
        "iagree",
        "agree",
        "accept",
        "iaccept",
        "acceptcookies",
        "allow",
        "acceptall",
        "jagförstår",
        "ok,stäng",
        "stäng",
    ]
    # First check for buttons with any matchin text string.
    log.debug("Looking for buttons...")
    items = b.find_by_tag("button")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().replace("+", "").split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
    # Secondly check for inputs with any matching text string.
    log.debug("Lookings for inputs...")
    items = b.find_by_tag("input")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
        # Well then, we can also check for a hrefs...
    log.debug("Lookings for a´s...")
    items = b.find_by_tag("a")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
    return None  # None found


def findMore(b):  # Return first element found
    m = [
        "configure",
        "manage",
        "managecookies",
        "configurepreferences",
        "managetrackers",
        "managesettings",
        "settings",
        "läsmer",
        "inställningar",
        "hanterainställningar",
    ]
    # First check for buttons with any matchin text string.
    log.debug("Looking for buttons...")
    items = b.find_by_tag("button")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().replace("+", "").split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
    # Secondly check for inputs with any matching text string.
    log.debug("Lookings for inputs...")
    items = b.find_by_tag("input")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
    # Well then, we can also check for a hrefs...
    log.debug("Lookings for a´s...")
    items = b.find_by_tag("a")
    for item in items:
        text = item.value or item.text
        if not text:  # If we have no text, why keep checking this one?
            continue
        # Make lowercase, remove all types of spaces, tabs, newlines...
        text = "".join(text.lower().split())
        if text in m:
            log.debug("Found match on {}!", text)
            return item
    # Last way, not the best, but can find some links to cookie policys.
    lastCheck = b.find_by_xpath("//a[contains(@href,'cookie')]")
    if lastCheck:
        log.debug(
            "Found an settings link by checking for links containing string cookie."
        )
        return lastCheck.first
    lastCheck = b.find_by_xpath("//a[contains(@href,'policy')]")
    if lastCheck:
        log.debug(
            "Found an settings link by checking for links containing string policy."
        )
        return lastCheck.first
    return None  # None found


def cookieShot(b):  # Function that takes a "shot" of all cookies.
    return browser.cookies.all()


@log.catch  # Lets be sure to catch all exceptions!
def startCrawl(url, b):
    # Here we should
    # create id variable.
    runId = genRunId(url)
    # 1. visit the url.
    log.info("Starting crawl id '{}'.", runId)
    browser.visit(url)
    # 1.1 Save down cookies.
    cookiesPre = b.cookies.all()
    # 1.2 Look for Iframes and jump in if found.
    iframeW = checkCookieIframe(b)
    if iframeW:
        log.info("Cookie consent seems to be an iframe, jumped in.")
    # 2. Check for approve and more settings buttons.
    log.info("Trying to find buttons, please wait.")
    apprBtn = findAppr(b)
    moreBtn = findMore(b)
    if apprBtn:
        log.info("Found a approve button/link.")
    else:
        log.info("Warning, could not find approve button/link.")
    if moreBtn:
        log.info("Found a settings button/link.")
    else:
        log.info("Warning, could not find settings button/link.")
    # 3. Screenshot Whole page, each button by themselves.
    log.info("Taking screenshot of page, and buttons.")
    screenshotPage(b, f"{mainPath}/screens/{runId}/mainPage.png")
    screenshotElement(apprBtn, f"{mainPath}/screens/{runId}/approve.png")
    screenshotElement(moreBtn, f"{mainPath}/screens/{runId}/more.png")
    log.info("Done with screenshots.")
    # 4. Save down the colors of buttons:
    log.info(
        "BG color of apprBtn is {} with the text color {}.",
        apprBtn._element.value_of_css_property("background-color"),
        apprBtn._element.value_of_css_property("color"),
    )
    log.info(
        "BG color of moreBtn is {} with the text color {}.",
        moreBtn._element.value_of_css_property("background-color"),
        moreBtn._element.value_of_css_property("color"),
    )
    # 5. Navigate to the next page i.e settings page, open dropdowns, take screenshot
    # Decide what type of button/link moreBtn is, is it a redirect or a JS function/button??
    if moreBtn._element.get_attribute("href"):
        # The settings are on a different page, visit the page.
        log.info("More button seems to be a link, clicking.")
        b.visit(moreBtn._element.get_attribute("href"))
    else:
        # Click on the button, simulating user.
        log.info("More button is JS/same-page, clicking.")
        moreBtn.click()
    log.info("On new page, sleeping 3 seconds for load.")
    time.sleep(3)
    # Open all dropdowns on page.
    log.info("Opening dropdowns, if any.")
    openDropdowns(b)
    # Take screenshot of page.
    log.info("Taking screenshot of more page.")
    screenshotPage(b, f"{mainPath}/screens/{runId}/morePage.png")
    # 6. More stuff i guess....
    return None


if __name__ == "__main__":
    # Setup logging and a basic browser driver.
    setupLogging()
    browser = setupDriver(True)
    # Fetch the urls to be crawled.
    urls = ["https://svt.se"]
    for url in urls:
        with log.contextualize(url=url):
            startCrawl(url, browser)
    browser.quit()