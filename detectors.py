# This file contains multiple different detection algorithms #

import splinter
import selenium
import json
from abp.filters import parse_filterlist
from abp.filters.parser import Filter
from loguru import logger as log


def get_rules_for_url(url):
    """This function gets all the adblock rules appliciable to a specific domain.

    Args:
        url (str): The url to check. In format https://url or url.

    Returns:
        [list]: The list of appliciable rules.
    """
    # Make sure we do not have https/http with the url.
    url = url.replace("https://", "")
    url = url.replace("http://", "")
    url = url.replace("/", "")
    css_rules = []
    with open("list.txt") as filterlist:
        rules = parse_filterlist(filterlist)
        rules = [rule for rule in rules if isinstance(rule, Filter)]
        for rule in rules:
            if rule.selector.get("type") == "css":
                # Check if there is a specific domain for the specific rule.
                options = [
                    (key, value) for key, value in rule.options if key == "domain"
                ]
                # If not, its appliciable everywhere, add it to list.
                if len(options) == 0:
                    css_rules.append(rule.selector.get("value"))
                    continue
                # there is only one domain option, if applicable then add rule.
                _, domains = options[0]
                domains = [
                    (domain, applicable)
                    for domain, applicable in domains
                    if applicable == True
                ]
                if len(domains) == 0:
                    css_rules.append(rule.selector.get("value"))
                    continue
                # Loop through the domains, if domain is matched, add rule.
                for domain_opts, _ in domains:
                    if domain_opts in url:
                        css_rules.append(rule.selector.get("value"))

    return css_rules


def find_by_cookie_string(browser: splinter.driver.DriverAPI):
    found_elems = []
    elems = browser.find_by_xpath(
        "//body//*/text()[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cookie')]/parent::*"
    )
    for elem in elems:
        if (
            elem._element.tag_name != "script"
            and elem._element.tag_name != "style"
            and elem.visible
        ):
            found_elems.append(elem)
    return found_elems


### FIXED WIDTH ###
def find_by_fixed_parent(browser, elems):
    found = []
    for elem in elems:
        f_elem = find_by_fixed_helper(browser, elem)
        if f_elem and f_elem._element.is_displayed():
            found.append(f_elem)
    if len(found) > 0:
        return found[0]._element
    return None


def get_parent(browser, elem):
    parent = elem.find_by_xpath("./..").first
    if parent:
        return parent
    return None


def find_by_fixed_helper(browser, elem):
    s_elem = elem
    # While we have a element and parent is not whole html document.
    while s_elem and get_parent(browser, s_elem).tag_name != "html":
        if s_elem._element.value_of_css_property("position") == "fixed":
            return s_elem
        s_elem = get_parent(browser, s_elem)
    return None


### FIND BY RULES ###
def find_by_list(browser):
    found = find_by_ruleset(browser)
    if len(found) > 0 and found[0]._element.is_displayed():
        log.debug(found[0])
        return found[0]._element
    return None


def find_by_ruleset(browser: splinter.driver.DriverAPI):
    # Get applicable rules for the current url.
    found_elems = []
    log.warning(browser.url)
    rules = get_rules_for_url(browser.url)
    # Check if we have any css match, if so save down the match string.
    found_rules = browser.execute_script(
        """
        function getElems(rules){
            return found=[],
            rules.forEach(e=>{
                elems=document.querySelectorAll(e)
                if(elems.length > 0){
                    found.push(e)
                }
                }),
                found}
        return getElems(arguments[0])
     """,
        rules,
    )
    log.debug(found_rules)
    # Now lets find elements containing something...
    for rule in found_rules:
        log.debug("Checking for {}", rule)
        found_matchs = browser.find_by_css(rule)
        for elem in found_matchs:
            if elem.text:
                found_elems.append(elem)
    # Lets find all element on page containing these matches.
    # Turn them into local webdriver elements :)
    # local_elems = []
    # for elem in elements:
    #    local_elems.append(
    #        selenium.webdriver.remote.webdriver.WebElement(
    #            elem._parent, elem._id, elem._w3c
    #        )
    #    )
    return found_elems


### FULL WIDTH ###
# The JavaScript code is from a github project, LINK HERE!!!
def find_by_full_helper(browser, elem):
    script = """
            function findFullWidthParent(elem) {
                function parseValue(value) {
                    var parsedValue = parseInt(value);
                    if (isNaN(parsedValue)) {
                        return 0;
                    } else {
                        return parsedValue;
                    }
                }

                function getWidth(elem) {
                    const style = getComputedStyle(elem);
                    return elem.clientWidth +
                        parseValue(style.borderLeftWidth) + parseValue(style.borderRightWidth) +
                        parseValue(style.marginLeft) + parseValue(style.marginRight);
                }

                function getHeight(elem) {
                    const style = getComputedStyle(elem);
                    return elem.clientHeight +
                        parseValue(style.borderTopWidth) + parseValue(style.borderBottomWidth) +
                        parseValue(style.marginTop) + parseValue(style.marginBottom);
                }

                function getVerticalSpacing(elem) {
                    const style = getComputedStyle(elem);
                    return parseValue(style.paddingTop) + parseValue(style.paddingBottom) +
                        parseValue(style.borderTopWidth) + parseValue(style.borderBottomWidth) +
                        parseValue(style.marginTop) + parseValue(style.marginBottom);
                }

                function getHeightDiff(outerElem, innerElem) {
                    return getHeight(outerElem) - getHeight(innerElem);
                }

                function isParentHigherThanItsSpacing(outerElem, innerElem) {
                    let allowedIncrease = Math.max(0.25*getHeight(innerElem), 20);
                    return getHeightDiff(outerElem, innerElem) > (getVerticalSpacing(outerElem) + allowedIncrease);
                }

                function getPosition(elem) {
                    return elem.getBoundingClientRect().top;
                }

                function getPositionDiff(outerElem, innerElem) {
                    return Math.abs(getPosition(outerElem) - getPosition(innerElem));
                }

                function getPositionSpacing(outerElem, innerElem) {
                    const outerStyle = getComputedStyle(outerElem);
                    const innerStyle = getComputedStyle(innerElem);
                    return parseValue(innerStyle.marginTop) +
                        parseValue(outerStyle.paddingTop) + parseValue(outerStyle.borderTopWidth)
                }

                function isParentMovedMoreThanItsSpacing(outerElem, innerElem) {
                    let allowedIncrease = Math.max(0.25*getHeight(innerElem), 20);
                    return getPositionDiff(outerElem, innerElem) > (getPositionSpacing(outerElem, innerElem) + allowedIncrease);
                }
                if (!elem) elem = this;
                while(elem && elem !== document.body) {
                    parent = elem.parentNode;
                    if (isParentHigherThanItsSpacing(parent, elem) || isParentMovedMoreThanItsSpacing(parent, elem)) {
                        break;
                    }
                    elem = parent;
                }

                let allowedIncrease = 18; // for scrollbar issues
                if (document.documentElement.clientWidth <= (getWidth(elem) + allowedIncrease)) {
                    return elem;
                } else {
                    return false;
                }
            }
            return findFullWidthParent(arguments[0]);"""
    elem = browser.driver.execute_script(script, elem._element)
    if elem:
        elem = selenium.webdriver.remote.webelement.WebElement(elem._parent, elem._id)
        return elem
    return None


def find_by_full_parent(browser, elems):
    found = []
    for elem in elems:
        f_elem = find_by_full_helper(browser, elem)
        if f_elem and f_elem.is_displayed():
            found.append(f_elem)
    if len(found) > 0:
        return found[0]
    return None


## FIND BY BUTTON PARENT ###
trigsAppr = [
    "iagree",
    "agree",
    "accept",
    "iaccept",
    "acceptcookies",
    "allow",
    "enableall"
    "continue",
    "acceptall",
    "godkännalla",
    "jagförstår",
    "ok,stäng",
    "stäng",
    "close",
    "tilladalle",
]
trigsMore = [
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


def _findBtnElem(browser, triggers):
    """Tries to find a button on page containg any string in input list.
    Args:
        triggers (list): A list of strings to look for.
    Returns:
        WebDriverElement: The found element, if any.
    """
    elemTypes = ["button", "input", "a"]
    for t in elemTypes:
        log.debug("Looking for element by type {}.", t)
        elems = browser.find_by_tag(t)
        for elem in elems:
            elemText = elem.value or elem.text
            if not elemText:
                continue
            # Make lowercase, remove spaces,tabs,newlines,non alphab chars.
            elemText = "".join(char for char in elemText if char.isalpha())
            elemText = "".join(elemText.lower().split())
            # Compare against list
            if elemText in triggers:
                return elem
    # Did not find any element.
    log.debug("Did not find any element.")
    return None


def _get_parent_of_btn(browser, elem):
    s_elem = elem
    # While we have a element and parent is not whole html document.
    while s_elem and get_parent(browser, s_elem).tag_name != "html":
        props = browser.execute_script('return window.getComputedStyle(arguments[0], null);', s_elem._element)
        props = "".join(props)
        if (
            s_elem.tag_name == "div"
            and s_elem._element.rect["height"] > 10
            and s_elem._element.rect["width"] > (elem._element.rect["width"] * 2)+50
            and "flex" in props
        ):
            return get_parent(browser, s_elem)
        s_elem = get_parent(browser, s_elem)
    return None


def find_by_btn_parent(browser):
    accept_btn = _findBtnElem(browser, trigsAppr)
    if accept_btn:
        parent = _get_parent_of_btn(browser, accept_btn)
        if parent:
            return parent._element
        return None

def find_cookie_notice(browser):
    log.info("Trying too find a cookie notice on page...")
    #Get all items containg string cookie.
    log.debug("Grabbing all cookie strings.")
    base_elems = find_by_cookie_string(browser)
    #Move onto BTN PARENT FINDER.
    log.debug("Looking for parents of consent buttons.")
    elem = find_by_btn_parent(browser)
    if elem:
        return elem
    #Checking for FIXED PRNT.
    log.debug("Looking for fixed parents.")
    elem = find_by_fixed_parent(browser,base_elems)
    if elem:
        return elem
    #Next FULL WIDTH.
    log.debug("Looking for full width elems.")
    elem = find_by_full_parent(browser, base_elems)
    if elem:
        return elem
    #Next ADBLOCK LIST.
    log.debug("Looking by ADP blocklist.")
    elem = find_by_list(browser)
    if elem:
        return elem
    log.debug("Could not find any notice.")
    return None