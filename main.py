import json
import time
import pendulum
import pprint
import sys
import os
import splinter
import csv
import selenium
from langdetect import detect
from PIL import Image
from loguru import logger as log
from splinter import Browser as Sbrowser
from selenium import webdriver as wd
from selenium.webdriver.support.color import Color
from pymongo import MongoClient, ReturnDocument
from datetime import datetime
from itertools import islice
from detectors import find_cookie_notice

mainPath = os.path.abspath(os.getcwd())
runId = 0


def genPathForScreen(url, name: str):
    # Make sure we do not have https/http with the url.
    url = url.replace("https://", "")
    url = url.replace("http://", "")
    url = url.replace("/", "")
    # Dots to -.
    url = url.replace(".", "-")
    # Get time.
    timestamp = (
        time.strftime("%a")
        + "_"
        + time.strftime("%d")
        + "_"
        + time.strftime("%b")
        + "_"
        + time.strftime("%H")
        + "_"
        + time.strftime("%M")
    )
    full_path = (
        os.getcwd() + "/result/screens/" + url + "_" + timestamp + "_" + name + ".png"
    )
    # Make sure path exists...
    dir = os.path.dirname(full_path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    return full_path


class Logger:
    """A class for logging."""

    def __init__(self, log):
        # This function sets up a default logger for the crawler.
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


class DatabaseManager:
    """This class provides connection to the MongoDB database."""

    def __init__(self, db_url=None):
        """Init class for DatabaseManager

        Args:
            db_url (string, optional): Database connection string. Defaults to localhost:27017.
        """
        try:
            log.debug("Connecting to database...")
            self.client = MongoClient(db_url)
            self.db = self.client["ccrawler"]
            self.runs = self.db["runs"]
            status = self.status()
            log.debug(
                "Ready! Running MongoDB {} on host {}.",
                status["version"],
                status["host"],
                status["uptime"],
            )
        except Exception as e:
            log.exception(e)

    def status(self):
        try:
            status = self.db.command("serverStatus")
            return status
        except Exception as e:
            log.exception(e)

    def create_run(self, url):
        """This function generates a Object for a new run, and saves it in the database.

        Returns:
            string: The objectId for the generated object.
        """
        try:
            new_run = {
                "url": url,
                "status": "startingRun",
                "runStartTime": datetime.now(),
            }
            obj_id = self.runs.insert_one(new_run).inserted_id
            return obj_id
        except Exception as e:
            log.exception(e)

    def modify_run(self, run_id, data):
        """This function modifies a run.

        Args:
            runId (string): the run to edit (objectId).

        Returns:
            documentId: The id of the doc modified.
        """
        try:
            run = self.runs.find_one_and_update(
                {"_id": run_id}, {"$set": data}, return_document=ReturnDocument.AFTER
            )
            return run
        except Exception as e:
            log.exception(e)

    def get_run(self, run_id):
        try:
            run = self.runs.find_one({"_id": run_id})
            return run
        except Exception as e:
            log.exception(e)

    def get_last_run_for_url(self, url):
        try:
            run = self.runs.find({"url": url}).sort("runStartTime", -1).limit(1)
            return run
        except Exception as e:
            log.exception(e)

    def get_runs_for_url(self, url, limit=None):
        try:
            if limit:
                runs = (
                    self.runs.find({"url": url}).sort("runStartTime", -1).limit(limit)
                )
            else:
                runs = self.runs.find({"url": url}).sort("runStartTime", -1)
            return runs
        except Exception as e:
            log.exception(e)


class Consent:
    """A class for consents."""

    def __init__(
        self, url, consent_elem: selenium.webdriver.remote.webelement.WebElement
    ):
        self.url = url  # Needed for screenshot cap.
        self.elem = consent_elem  # The content of the button text.
        self.size = (
            self.elem.size
        )  # The size of the consent notice, as webdriver rect dirct.
        self.links = []
        self.html = self.elem.get_attribute("outerHTML")
        self.apprBtn = None
        self.apprBtnMeta = None
        self.moreBtn = None
        self.moreBtnMeta = None
        self.scrn = None
        # Look for links
        for elem in self.elem.find_elements_by_partial_link_text(""):
            self.links.append(elem.get_attribute("href"))
        # Lets screenshot ourselves.
        self.screenshot()
        # Lets find our buttons.
        self.find_buttons()

    def screenshot(self):
        # Takes a screenshot of the current notice/element, saves in results
        # Returns path to screenshot.
        full_path = genPathForScreen(self.url, "notice")
        log.debug(full_path)
        scrn = self.elem.screenshot(full_path)
        log.debug(scrn)
        if scrn:
            self.scrn = full_path
            return True
        else:
            log.debug("Could not screenshot element!")
            return False

    def find_buttons(self):
        apprTrigs = [
            "approve",
            "okay",
            "accept",
            "agree",
            "allow",
            "continue",
            "godkänn",
            "förstår",
            "stäng",
        ]
        apprBtn = self._findBtnElem(apprTrigs)
        if apprBtn:
            log.debug("FOUND APPROVE BUTTON!")
            apprBtn = Button(self.url, apprBtn)
            apprBtn.screenshot("approve")
            self.apprBtn = apprBtn
            self.apprBtnMeta = apprBtn.getMeta()
        moreTrigs = [
            "configure",
            "manage",
            "settings",
            "customize",
            "customise",
            "inställningar",
            "more",
            "mer",
        ]
        moreBtn = self._findBtnElem(moreTrigs)
        if moreBtn:
            log.debug("FOUND MORE BUTTON!")
            moreBtn = Button(self.url, moreBtn)
            moreBtn.screenshot("more")
            self.moreBtn = moreBtn
            self.moreBtnMeta = moreBtn.getMeta()

    @log.catch
    def _findBtnElem(self, triggers):
        """Tries to find a button on page containg any string in input list.

        Args:
            triggers (list): A list of strings to look for.

        Returns:
            WebDriverElement: The found element, if any.
        """
        elemTypes = ["button", "input", "a"]
        for t in elemTypes:
            log.debug("Looking for element by type {}.", t)
            elems = self.elem.find_elements_by_tag_name(t)
            for elem in elems:
                elemText = elem.text or elem.get_attribute("value")
                if not elemText:
                    continue
                # Make lowercase, remove spaces,tabs,newlines,non alphab chars.
                elemText = "".join(char for char in elemText if char.isalpha())
                elemText = "".join(elemText.lower().split())
                # Compare against list
                for trig in triggers:
                    if trig in elemText:
                        return elem
        # Did not find any element.
        log.debug("Did not find any element.")
        return None

    def getMeta(self):
        return {
            "size": self.size,
            "links": self.links,
            "html": self.html,
            "apprBtn": self.apprBtnMeta,
            "moreBtn": self.moreBtnMeta,
            "scrn": self.scrn,
        }


class Button:
    """A class for buttons."""

    def __init__(self, url, btnElem: selenium.webdriver.remote.webelement.WebElement):
        self.url = url  # Url for screenshot cap.
        self.text = None  # The content of the button text.
        self.color = None  # The color of the button.
        self.textColor = None  # The color of the text.
        self.type = None  # The type of button.
        self.redirect = None  # Is the button a redirect to another page?
        self.html = None  # Raw HTML of button.
        self.size = None  # Size.
        self.scrn = None  # A screenshot of the button.
        # If we got a button, add it!
        if btnElem:
            # Lets not forget the element.
            self.elem = btnElem
            # Now lets fill out the apprBtn extras from button.
            if self.elem:
                self.text = self.elem.text or self.elem.get_attribute("value")
                self.type = self.elem.tag_name
                self.html = self.elem.get_attribute("outerHTML")
            if self.elem.size:
                self.size = self.elem.size
            if self.elem.get_attribute("href"):
                self.redirect = self.elem.get_attribute("href")
            if self.elem.value_of_css_property("background-color"):
                self.color = Color.from_string(
                    self.elem.value_of_css_property("background-color")
                ).hex
            if self.elem.value_of_css_property("color"):
                self.textColor = Color.from_string(
                    self.elem.value_of_css_property("color")
                ).hex

    def screenshot(self, name: str):
        # Takes a screenshot of the current notice/element, saves in results
        # Returns path to screenshot.
        full_path = genPathForScreen(self.url, name)
        scrn = self.elem.screenshot(full_path)
        if scrn:
            self.scrn = full_path
            return True
        else:
            log.debug("Could not screenshot element!")
            return False

    def getMeta(self):
        return {
            "text": self.text,
            "color": self.color,
            "textColor": self.textColor,
            "type": self.type,
            "redirect": self.redirect,
            "html": self.html,
            "scrn": self.scrn,
            "size": self.size,
        }


class Iframe:
    """A class for iframes."""

    def __init__(self, iframeElem: splinter.driver.ElementAPI = None):
        self.html = None
        self.url = None
        # self.cookies = list[dict]

        # If we got a button, add it!
        if iframeElem:
            # Lets not forget the element.
            # self.elem = iframeElem
            # Now lets fill out the apprBtn extras from button.
            self.text = iframeElem.html or None
            self.html = iframeElem._element.get_attribute("outerHTML")


class PageResult:
    """This class/object contains the result of a page scan."""

    def __init__(self, url):
        # Setup basic vars.
        self.url = url
        self.failed = False
        self.failedMsg = None
        self.failedExp = None
        # Cookies and HTML of page.
        self.cookies = []  # dict of all cookies.
        self.rawHtml = None
        # More information
        self.lang = None
        self.iframe = None
        # Found buttons
        self.apprBtn = None
        self.moreBtn = None
        # List of all screenshot paths.
        self.screens = []

    def setApprBtn(self, btn: Button):
        """Sets the pages approve button.

        Args:
            btn (Button): A button object.
        """
        self.apprBtn = btn

    def setMoreBtn(self, btn: Button):
        """Sets the pages more button.

        Args:
            btn (Button): A button object.
        """
        self.moreBtn = btn

    def setHtml(self, html: str):
        """Sets the raw html of page

        Args:
            html (str): The raw, unparsed html of page.
        """
        self.rawHtml = html

    def setLang(self, lang: str):
        """Sets the language of the page.

        Args:
            lang (str): Language tag.
        """
        self.lang = lang

    def setIframe(self, iframe: splinter.driver.ElementAPI):
        """Sets the iframe for consent.

        Args:
            iframe (WebDriverElement): The iframe element.
        """
        self.iframe = iframe

    def setCookies(self, cookies):
        self.cookies = cookies

    def addScreen(self, name: str, screenPath: str):
        """Adds a screenshot to this pages list of screens.

        Args:
            screen (str): The path to the screenshot.
        """
        self.screens.append({"name": name, "path": screenPath})

    def toJson(self):
        """Function to return this object as a json object.

        Returns:
            str: A json representation of this object.
        """
        return None


@log.catch
class PageScanner:
    """This class setups a page scanner, which can crawl a page for
    cookie consent notices.
    """

    def __init__(
        self, browser: splinter.driver.DriverAPI, db: DatabaseManager, url: str
    ):
        self.browser = browser
        self.url = url
        self.db = db
        # Window size.
        self.windowSize = self.browser.driver.get_window_size()
        # Timings.
        self.startedAt = None
        self.endedAt = None
        # Metadata.
        self.url = url  # The url we start at.
        self.lang = None  # The website language.
        self.scrn = None  # Screenshot of first load.
        self.consent = None  # Consent element.
        # Cookies.
        self.startCookies = None  # The cookies that gets set at start.
        self.endCookies = None  # The cookies after the run has been done.

    @log.catch
    def doScan(self, followLinks=True, screenshot=True):
        """Do a scan of the current url we are at.

        Args:
            followLinks (bool, optional): If we should follow links/hrefs to settings. Defaults to True.
            screenshot (bool, optional): If we should screenshot all found elements. Defaults to True.
        """
        try:
            self.startedAt = datetime.now()
            self.runId = self.db.create_run(self.url)
            # Clear cookies and local storage before run.
            log.debug("Clearing cookies, preparing for run...")
            self.browser.cookies.delete()
            # Navigate to page.
            self.browser.visit(self.url)
            log.debug("Navigated to url.")
            # Lets figure out the language
            self._resolveLang()
            # Screenshot
            self.browser.driver.save_screenshot(genPathForScreen(self.url, "full"))
            self.scrn = genPathForScreen(self.url, "full")
            # Lets check for iframes.
            iframe = self._iframeHandler()
            self.iframe = iframe
            # Lets grab the cookies, mmm.
            self.startCookies = self.browser.cookies.all(True)
            # Lets find our consent notice.
            log.info("Looking for cookie notice!")
            consent = find_cookie_notice(self.browser)
            if consent:
                self.consent = Consent(self.url, consent)
                # We have buttons, we are done for now :)
                self.endedAt = datetime.now()
                self.db.modify_run(
                    self.runId,
                    {
                        "status": "runDone",
                        "browserSize": self.windowSize,
                        "startedAt": self.startedAt,
                        "endedAt": self.endedAt,
                        "lang": self.lang,
                        "scrn": self.scrn,
                        "notice": self.consent.getMeta(),
                        "startCookies": self.startCookies,
                        "endCookies": self.endCookies,
                    },
                )
            else:
                # We have no notice, lets skip this page and return error to db.
                self.endedAt = datetime.now()
                self.db.modify_run(
                    self.runId,
                    {
                        "status": "noNoticeFound",
                        "browserSize": self.windowSize,
                        "startedAt": self.startedAt,
                        "endedAt": self.endedAt,
                        "lang": self.lang,
                        "scrn": self.scrn,
                        "startCookies": self.startCookies,
                        "endCookies": self.endCookies,
                    },
                )
                return None

            log.info("DONE WITH RUN!")
            # Done with first crawl, now if we had settings lets check them out.
            # TODO: Start looking for settings, check flowchart #3.
        except:
            # Log stuff here.
            e = sys.exc_info()[0]
            log.exception(e)

    @log.catch
    def _findMoreLink(self):
        """A last way to find link to more settings page/info.
        uses xpath to look for links containg cookie or policy.
        """
        xpaths = ["//a[contains(@href,'cookie')]", "//a[contains(@href,'policy')]"]
        for xpath in xpaths:
            elems = self.browser.find_by_xpath(xpath)
            if elems:
                log.debug("Found cookie/policy link element.")
                return elems.first
        log.debug("Did not find any cookie/policy link.")
        return None  # None found

    @log.catch
    def _iframeHandler(self):  # TODO: Cleamup handler, make iframe agnostic.
        """This function handles if there is a popup iframe of a consent,
        as some pages uses CMSes that are loded via iframe. If iframe is found,
        we just jump in.

        Returns:
            boolean: If we jumped in a frame or not.
        """
        try:
            frames = self.browser.find_by_tag("iframe").find_by_xpath(
                "//*[contains(@title, 'onsent')]"
            )
            if frames:
                log.debug("Found an iframe, jumping in.")
                self.browser.driver.switch_to.frame(frames.first["id"])
                return True
            return None
        except:
            log.debug("Didnt find iframe.")
        return None

    @log.catch
    def _resolveLang(self):
        """Tries to resolve language of current page."""
        try:
            log.debug("Determining language.")
            textBody = self.browser.evaluate_script(
                "window.document.body.innerText.valueOf();"
            )
            self.lang = detect(textBody)
        except:
            log.debug("Could not determine language.")

    @log.catch
    def toJson(self):
        """Function to return this object as a json object.

        Returns:
            str: A json representation of this object.
        """
        res = {
            key: value
            for key, value in self.__dict__.items()
            if key not in ["browser", "elem"]
        }
        return json.dumps(
            res, indent=2, default=lambda o: "<not serializable>", ensure_ascii=False
        )


def setupDriver(hless=False):
    """Returns a setup browser from splinter, ready for scaping.

    Args:
        hless (bool, optional): Should the browser run headless. Defaults to False.

    Returns:
        WebDriver: A splinter browser driver.
    """
    browserOptions = wd.ChromeOptions()
    browserOptions.add_argument("--lang=en-GB")
    browserOptions.add_argument("--window-size=1920,1080")
    browserOptions.add_experimental_option(
        "prefs", {"intl.accept_languages": "en,en_GB"}
    )
    browserOptions.add_experimental_option("w3c", False)
    browserOptions.headless = hless
    if hless:
        log.info("Starting a headless chrome drier...")
    else:
        log.info("Starting a visible chrome driver...")
    return Sbrowser("chrome", options=browserOptions)


if __name__ == "__main__":
    Logger(log)
    db = DatabaseManager()
    url_list = []
    with open("url_list.csv", "r") as link_csv_file:
        csv_reader = csv.DictReader(link_csv_file)

        header = next(csv_reader)
        if header != None:
            for link in islice(csv_reader, 10):
                http_string = "https://" + link["Domain"]
                url_list.append(http_string)

    for url in url_list:
        runId += 1
        print("Creating test obj..")
        browser = setupDriver(True)
        with log.contextualize(url=url):
            res = PageScanner(browser, db, url)
            res.doScan()
            browser.quit()
