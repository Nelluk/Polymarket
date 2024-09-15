import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import requests
import json
from urllib.parse import urlparse, quote
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
                # Filter outcomes with at least 1% probability
                filtered_data = [item for item in result['data'] if item[1] >= 0.01]
                
                output = f"\x02Market:\x02 {result['title']}\n"
                output += "\n".join([f"  \x0303{outcome}:\x03 {probability:.1%}" for outcome, probability in filtered_data])
                irc.reply(output, prefixNick=False)
            else:
                irc.reply("Unable to fetch odds or no valid data found.")
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")

    polymarket = wrap(polymarket, ['url'])

    def _parse_polymarket_event(self, url, max_responses=8):
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        slug = ' '.join(path_parts[-1].split('-'))
        encoded_slug = quote(slug)
        api_url = f"https://polymarket.com/api/events/global?q={encoded_slug}"
        
        response = requests.get(api_url, verify=False)
        response.raise_for_status()
        data = response.json()

        if not data['events']:
            return {'title': "No matching event found", 'data': []}

        matching_event = next((event for event in data['events'] if event['slug'] == slug.replace(' ', '-')), None)

        if not matching_event:
            return {'title': "No matching event found", 'data': []}

        title = matching_event['title']
        markets = matching_event['markets']

        cleaned_data = []
        for market in markets:
            outcome = market['groupItemTitle']
            try:
                probability = float(market['lastTradePrice'])
            except (KeyError, ValueError):
                probability = 0.0
        
            cleaned_data.append((outcome, probability))

        cleaned_data.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'title': title,
            'data': cleaned_data[:max_responses]
        }

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
