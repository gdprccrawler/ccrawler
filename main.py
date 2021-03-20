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
        splinterDriver: A splinter browser driver.
    """
    log
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


if __name__ == "__main__":
    setupLogging()
    browser = setupDriver(True)
    time.sleep(10)