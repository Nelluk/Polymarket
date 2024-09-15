import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class Polymarket(callbacks.Plugin):
    """Fetches and displays odds from Polymarket"""

    def polymarket(self, irc, msg, args):
        """Takes no arguments
        
        A simple test command for the Polymarket plugin.
        """
        irc.reply("Polymarket plugin is working!")

Class = Polymarket

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
