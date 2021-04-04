import json
import time
import pendulum
import pprint
import sys
import os
from langdetect import detect
from loguru import logger as log
from splinter import Browser as Sbrowser
from selenium.webdriver.support.color import Color

mainPath = os.path.abspath(os.getcwd())


class Logger:
    """A class for buttons."""

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

    def __init__(self):
        self.text = None
        self.color = None
        self.textColor = None
        self.type = None
        self.redirect = None
        self.html = None

    @log.catch
    def importBtn(self, btnElem=None):
        """Function that converts WebDriverElement "button" into class Button.

        Args:
            btnElem (WebDriverElement): The "button" element.
        """
        # If no button, return.
        if not btnElem:
            return
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
        self.elem = None


class PageResult:
    """This class/object contains the result of a page scan."""

    def __init__(self, url):
        # Setup basic vars.
        self.url = url
        self.failed = False
        self.failedMsg = None
        self.failedExp = None
        # Cookies and HTML of page.
        self.cookies = {}  # dict of all cookies.
        self.rawHtml = None
        # More information
        self.lang = None
        self.iframe = None
        # Found buttons
        self.apprBtn = None
        self.moreBtn = None
        # List of all screenshot paths.
        self.screens = []

    def setApprBtn(self, btn):
        """Sets the pages approve button.

        Args:
            btn (Button): A button object.
        """
        self.apprBtn = btn

    def setMoreBtn(self, btn):
        """Sets the pages more button.

        Args:
            btn (Button): A button object.
        """
        self.moreBtn = btn

    def setHtml(self, html):
        """Sets the raw html of page

        Args:
            html (str): The raw, unparsed html of page.
        """
        self.rawHtml = html

    def setLang(self, lang):
        """Sets the language of the page.

        Args:
            lang (str): Language tag.
        """
        self.lang = lang

    def setCookies(self, cookies):
        self.cookies = cookies

    def addScreen(self, screen):
        """Adds a screenshot to this pages list of screens.

        Args:
            screen (str): The path to the screenshot.
        """
        self.screens.append(screen)

    def toJson(self):
        """Function to return this object as a json object.

        Returns:
            str: A json representation of this object.
        """
        res = {
            key: value for key, value in self.__dict__.items() if key not in ["browser"]
        }
        return json.dumps(
            res, indent=2, default=lambda x: x.__dict__, ensure_ascii=False
        )


@log.catch
class PageScanner:
    """This class setups a page scanner, which can crawl a page for
    cookie consent notices.
    """

    def __init__(self, browser, url):
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
            # self.browser.visit(self.url)
            # Clear cookies and local storage before run.
            log.debug("Clearing cookies, preparing for run.")
            self.browser.cookies.delete()
            # Navigate to page.
            self.browser.visit(self.url)
            log.debug("Navigated to url.")
            # Lets figure out the language
            self._resolveLang()
            # Lets grab the cookies, mmm.
            cookies = self.browser.cookies.all(True)
            pprint.pprint(cookies)
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
                apprBtn = Button()
                apprBtn.importBtn(aBtn)
                self.res.setApprBtn(apprBtn)
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
                moreBtn = Button()
                moreBtn.importBtn(mBtn)
                self.res.setMoreBtn(moreBtn)
            # Lets screenshot our elements
            aBtnS = aBtn.screenshot(f"{mainPath}/screens/screen.png")
            mBtnS = mBtn.screenshot(f"{mainPath}/screens/screen.png")
            self.res.addScreen(aBtnS)
            self.res.addScreen(mBtnS)
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
                return True
        except:
            log.debug("Didnt find iframe.")
        return False

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
            res, indent=2, default=lambda x: x.__dict__, ensure_ascii=False
        )


if __name__ == "__main__":
    Logger(log)
    print("Creating test obj..")
    browser = Sbrowser("chrome", headless=True)
    res = PageScanner(browser, "https://cnn.com")
    res.doScan()
    print(res.toJson())
    browser.quit()