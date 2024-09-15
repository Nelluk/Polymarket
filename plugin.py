import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.log as log
import requests
import json
from urllib.parse import urlparse, quote
import warnings

# Suppress InsecureRequestWarning
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class Polymarket(callbacks.Plugin):
    """Fetches and displays odds from Polymarket"""

    def _parse_polymarket_event(self, query, is_url=True, max_responses=12):
        """
        Parse Polymarket event data from API response.
        
        Args:
            query (str): URL or search string
            is_url (bool): True if query is a URL, False if it's a search string
            max_responses (int): Maximum number of outcomes to return

        Returns:
            dict: Parsed event data with title and outcomes
        """
        # Prepare API query
        if is_url:
            parsed_url = urlparse(query)
            path_parts = parsed_url.path.split('/')
            slug = ' '.join(path_parts[-1].split('-'))
        else:
            slug = query

        encoded_slug = quote(slug)
        api_url = f"https://polymarket.com/api/events/global?q={encoded_slug}"
        
        log.debug(f"Polymarket: Fetching data from API URL: {api_url}")
        
        # Fetch data from API
        response = requests.get(api_url, verify=False)
        response.raise_for_status()
        data = response.json()

        if not data['events']:
            return {'title': "No matching event found", 'data': []}

        # Find matching event
        if is_url:
            matching_event = next((event for event in data['events'] if event['slug'] == slug.replace(' ', '-')), None)
        else:
            matching_event = data['events'][0] if data['events'] else None

        if not matching_event:
            return {'title': "No matching event found", 'data': []}

        title = matching_event['title']
        markets = matching_event['markets']

        # Parse market data
        cleaned_data = []
        for market in markets:
            outcome = market['groupItemTitle']
            try:
                outcomes = json.loads(market['outcomes'])
                outcome_prices = json.loads(market['outcomePrices'])
                
                if len(outcomes) == 2 and 'Yes' in outcomes and 'No' in outcomes:
                    yes_index = outcomes.index('Yes')
                    no_index = outcomes.index('No')
                    yes_probability = float(outcome_prices[yes_index])
                    no_probability = float(outcome_prices[no_index])
                    
                    # Handle the edge case for Yes/No markets only if it's the only market
                    if len(markets) == 1 and yes_probability <= 0.01 and no_probability > 0.99:
                        cleaned_data.append((outcome, yes_probability, 'Yes'))
                    else:
                        probability = yes_probability
                        display_outcome = 'Yes'
                        cleaned_data.append((outcome, probability, display_outcome))
                else:
                    # For multi-outcome markets, always use the highest probability
                    max_price_index = outcome_prices.index(max(outcome_prices, key=float))
                    probability = float(outcome_prices[max_price_index])
                    display_outcome = outcomes[max_price_index]
                    cleaned_data.append((outcome, probability, display_outcome))
            except (KeyError, ValueError, json.JSONDecodeError):
                # If there's any error in parsing, skip this market
                continue

        # Sort outcomes by probability and limit to max_responses
        cleaned_data.sort(key=lambda x: x[1], reverse=True)
        
        result = {
            'title': title,
            'data': [item for item in cleaned_data if item[1] >= 0.01 or len(cleaned_data) == 1][:max_responses]
        }
        
        log.debug(f"Polymarket: Parsed event data: {result}")
        
        return result

    def polymarket(self, irc, msg, args, query):
        """<query>
        
        Fetches and displays the current odds from Polymarket. 
        If <query> is a URL, it fetches odds for that specific market.
        If <query> is a search string, it searches for matching markets and displays the top result.
        """
        try:
            is_url = query.startswith('http://') or query.startswith('https://')
            result = self._parse_polymarket_event(query, is_url=is_url)
            if result['data']:
                filtered_data = result['data'][:20]
                
                # Format output
                output = f"\x02{result['title']}\x02: "
                output += " | ".join([f"{outcome}: \x02{probability:.1%}{' (' + display_outcome + ')' if display_outcome != 'Yes' else ''}\x02" for outcome, probability, display_outcome in filtered_data])
                
                log.debug(f"Polymarket: Sending IRC reply: {output}")
                
                # Use private=True to trigger Limnoria's message splitting
                irc.reply(output, prefixNick=False, private=True)
            else:
                irc.reply("Unable to fetch odds or no valid data found.")
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")

    polymarket = wrap(polymarket, ['text'])

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
