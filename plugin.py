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
                # Filter outcomes with at least 1% probability and take top 4
                filtered_data = [item for item in result['data'] if item[1] >= 0.01][:4]
                
                # Format the output
                outcomes = ' | '.join([f"{outcome}: {probability:.1%}" for outcome, probability in filtered_data])
                output = f"Market: {result['title']} | {outcomes}"
                
                irc.reply(output)
            else:
                irc.reply("Unable to fetch odds or no valid data found.")
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")

    polymarket = wrap(polymarket, ['url'])

    def _parse_polymarket_event(self, url, max_responses=4):
        self.log.debug(f"Parsing Polymarket event for URL: {url}")
        
        # Extract the slug from the URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        slug = '-'.join(path_parts[-1].split('-'))  # Keep hyphens
        self.log.debug(f"Extracted slug: {slug}")

        # Make API request
        api_url = f"https://polymarket.com/api/events/global?q={slug}"
        self.log.debug(f"Making API request to: {api_url}")
        
        # New debug line to show the exact API endpoint
        self.log.debug(f"Full API endpoint: {requests.utils.quote(api_url)}")
        
        response = requests.get(api_url, verify=False)  # Disable SSL verification
        response.raise_for_status()
        data = response.json()
        self.log.debug(f"API response received. Number of events: {len(data['events'])}")

        if not data['events']:
            self.log.debug("No events found in API response")
            return {'title': "No matching event found", 'data': []}

        # Find the event that matches our slug
        matching_event = None
        for event in data['events']:
            self.log.debug(f"Checking event: {event['slug']}")
            if event['slug'] == slug:
                matching_event = event
                break

        if not matching_event:
            self.log.debug("No matching event found for the given slug")
            return {'title': "No matching event found", 'data': []}

        title = matching_event['title']
        markets = matching_event['markets']
        self.log.debug(f"Matching event found. Title: {title}, Number of markets: {len(markets)}")

        # Sort markets by liquidity and get top max_responses
        sorted_markets = sorted(markets, key=lambda x: float(x['liquidity']), reverse=True)[:max_responses]
        self.log.debug(f"Sorted markets. Number of markets after sorting: {len(sorted_markets)}")

        cleaned_data = []
        for market in sorted_markets:
            outcome = market['groupItemTitle']
            self.log.debug(f"Processing market: {outcome}")
            try:
                # Try to parse outcomePrices as JSON
                outcome_prices = json.loads(market['outcomePrices'])
                probability = float(outcome_prices[0]) if outcome_prices else 0.0
                self.log.debug(f"Parsed outcomePrices as JSON. Probability: {probability}")
            except json.JSONDecodeError:
                # If JSON parsing fails, try to evaluate it as a Python list
                try:
                    outcome_prices = eval(market['outcomePrices'])
                    probability = float(outcome_prices[0]) if outcome_prices else 0.0
                    self.log.debug(f"Parsed outcomePrices as Python list. Probability: {probability}")
                except:
                    # If all else fails, set probability to 0
                    probability = 0.0
                    self.log.debug(f"Failed to parse outcomePrices. Setting probability to 0")
            
            cleaned_data.append((outcome, probability))

        self.log.debug(f"Finished processing. Number of cleaned data entries: {len(cleaned_data)}")
        return {
            'title': title,
            'data': cleaned_data
        }

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
