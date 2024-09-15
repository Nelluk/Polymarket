import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import os
from webdriver_manager.core.utils import ChromeType

class Polymarket(callbacks.Plugin):
    """Fetches and displays odds from Polymarket"""

    def polymarket(self, irc, msg, args, url):
        """<url>
        
        Fetches and displays the current odds from a Polymarket URL.
        """
        try:
            result = self._parse_polymarket_event(url)
            if result['data']:
                irc.reply(f"Market: {result['title']}")
                for outcome, probability in result['data']:
                    irc.reply(f"{outcome}: {probability:.2%}")
            else:
                irc.reply("Unable to fetch odds or no valid data found.")
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")

    polymarket = wrap(polymarket, ['url'])

    def _parse_polymarket_event(self, url, max_responses=4):
        # Use a writable directory for ChromeDriver
        driver_path = ChromeDriverManager(path="/tmp").install()
        service = Service(driver_path)
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "*:not(script):not(style)"))
            )

            title = driver.title

            script = """
            return Array.from(document.querySelectorAll('*')).filter(el => el.textContent.includes('%'))
                .map(el => el.textContent.trim())
                .filter(text => text.match(/^[\\w\\s,+\\-%]+\\$[\\d,]+\\s+Bet\\d+(?:\\.\\d+)?%/))
                .map(text => {
                    let [outcome, rest] = text.split(/\\$(?=\\d)/);
                    let percentage = rest.match(/Bet(\\d+(?:\\.\\d+)?)%/)[1];
                    return [outcome.trim(), parseFloat(percentage) / 100];
                });
            """
            
            data = driver.execute_script(script)

            cleaned_data = sorted(
                {k: v for k, v in dict(data).items() if v > 0.01}.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_responses]

            return {
                'title': title,
                'data': cleaned_data
            }

        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                'title': title if 'title' in locals() else "Title not found",
                'data': []
            }

        finally:
            driver.quit()

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
