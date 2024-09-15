import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import requests
import json
from urllib.parse import urlparse
import warnings

# Suppress InsecureRequestWarning
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

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
        # Extract the slug from the URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        slug = ' '.join(path_parts[-1].split('-'))

        # Make API request
        api_url = f"https://polymarket.com/api/events/global?q={slug}"
        response = requests.get(api_url, verify=False)  # Disable SSL verification
        response.raise_for_status()
        data = response.json()

        if not data['events']:
            return {'title': "No matching event found", 'data': []}

        event = data['events'][0]
        title = event['title']
        markets = event['markets']

        # Sort markets by liquidity and get top max_responses
        sorted_markets = sorted(markets, key=lambda x: float(x['liquidity']), reverse=True)[:max_responses]

        cleaned_data = []
        for market in sorted_markets:
            outcome = market['groupItemTitle']
            # Parse the outcomePrices as a list and get the first element
            outcome_prices = json.loads(market['outcomePrices'])
            probability = float(outcome_prices[0]) if outcome_prices else 0.0
            cleaned_data.append((outcome, probability))

        return {
            'title': title,
            'data': cleaned_data
        }

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
