import json
import time
import pendulum
import pprint
import sys
import os
import splinter
from langdetect import detect
from loguru import logger as log
from splinter import Browser as Sbrowser
from selenium import webdriver as wd
from selenium.webdriver.support.color import Color

mainPath = os.path.abspath(os.getcwd())
runId = None


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


class Button:
    """A class for buttons."""

    def __init__(self, btnElem: splinter.driver.ElementAPI):
        self.text = None
        self.color = None
        self.textColor = None
        self.type = None
        self.redirect = None
        self.html = None
        self.scrn = None
        # If we got a button, add it!
        if btnElem:
            # Lets not forget the element.
            self.elem = btnElem
            # Now lets fill out the apprBtn extras from button.
            if self.elem:
                self.text = self.elem.text or self.elem.value
                self.type = self.elem.tag_name
                self.html = self.elem._element.get_attribute("outerHTML")
            if self.elem._element.get_attribute("href"):
                self.redirect = self.elem._element.get_attribute("href")
            if self.elem._element.value_of_css_property("background-color"):
                self.color = Color.from_string(
                    self.elem._element.value_of_css_property("background-color")
                ).hex
            if self.elem._element.value_of_css_property("color"):
                self.textColor = Color.from_string(
                    self.elem._element.value_of_css_property("color")
                ).hex

    def screenshot(self, name: str):
        path = os.getcwd() + f"/result/{runId}/screens/"
        try:
            # Make path if not found, we save
            if not os.path.exists(path):  # Make path if not exists
                os.makedirs(path)
            tmpImg = self.elem.screenshot(path + f"/{name}")  # Take a screenshot
            os.rename(tmpImg, path + f"/{name}")  # Move to correct filename.
            log.debug("Took screenshot of element!")
            return path + f"/{name}"
        except:
            e = sys.exc_info()[0]
            log.error("Could not screenshot element, error: {}", e)


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

    def __init__(self, browser: splinter.driver.DriverAPI, url):
        self.startedAt = None
        self.endedAt = None
        self.browser = browser
        self.url = url
        self.res = PageResult(self.url)

    @log.catch
    def doScan(self, followLinks=True, screenshot=True):
        """Do a scan of the current url we are at.

        Args:
            followLinks (bool, optional): If we should follow links/hrefs to settings. Defaults to True.
            screenshot (bool, optional): If we should screenshot all found elements. Defaults to True.
        """
        try:
            self.startedAt = pendulum.now().to_iso8601_string()
            self.runId = self._genRunId()
            runId = self.runId
            # Clear cookies and local storage before run.
            log.debug("Clearing cookies, preparing for run.")
            self.browser.cookies.delete()
            # Navigate to page.
            self.browser.visit(self.url)
            log.debug("Navigated to url.")
            # Lets figure out the language
            self._resolveLang()
            # Lets check for iframes.
            iframe = self._iframeHandler()
            self.res.setIframe(iframe)
            # Lets grab the cookies, mmm.
            cookies = self.browser.cookies.all(True)
            self.res.setCookies(cookies)
            # Lets find our approve and more button.
            trigs = [
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
                "tilladalle",
            ]
            aBtn = self._findBtnElem(trigs)
            if aBtn:
                apprBtn = Button(aBtn)
                self.res.setApprBtn(apprBtn)
                scrn = apprBtn.screenshot("approve.png")
                self.res.addScreen("approve", scrn)
            trigs = [
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
                "tilladvalge",
            ]
            mBtn = self._findBtnElem(trigs)
            if not mBtn:
                mBtn = self._findMoreLink()
            if mBtn:
                moreBtn = Button(mBtn)
                self.res.setMoreBtn(moreBtn)
                scrn = moreBtn.screenshot("more.png")
                self.res.addScreen("more", scrn)
            self.endedAt = pendulum.now().to_iso8601_string()
        except:
            # Log stuff here.
            log.error("WOOPS, SOMETHING WENT WRONG...")

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
            elems = self.browser.find_by_tag(t)
            for elem in elems:
                elemText = elem.value or elem.text
                if not elemText:
                    continue
                # Make lowercase, remove spaces,tabs,newlines,non alphab chars.
                elemText = "".join(char for char in elemText if char.isalpha())
                elemText = "".join(elemText.lower().split())
                # Compare against list
                if elemText in triggers:
                    log.debug("Found element, on match {}.", elemText)
                    return elem
        # Did not find any element.
        log.debug("Did not find any element.")
        return None

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
    def _iframeHandler(self):
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
                return Iframe(frames.first)
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
            lang = detect(textBody)
            self.res.setLang(lang)
        except:
            log.debug("Could not determine language.")

    def _genRunId(self):
        """Function that generates a runID.

        Returns:
            str: A unique identifier for this run.
        """
        url = self.url.replace("https://", "").replace("http://", "").replace(".", "-")
        time = pendulum.now().format("YYYY_MM_DD_HH_mm_ss")
        return time + "-" + url

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
    browserOptions.headless = hless
    if hless:
        log.info("Starting a headless chrome drier...")
    else:
        log.info("Starting a visible chrome driver...")
    return Sbrowser("chrome", options=browserOptions)


if __name__ == "__main__":
    Logger(log)
    print("Creating test obj..")
    browser = setupDriver(True)
    url = "https://vice.com"
    with log.contextualize(url=url):
        res = PageScanner(browser, url)
        res.doScan()
        print(res.toJson())
        browser.quit()
