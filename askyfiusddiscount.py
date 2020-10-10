#!/usr/bin/env python3


# Strategy Outline:
#  1. Waiting for a rise in the price of YFI.
#  2. Submit an ask one tick above the best bid.
#  3. The ask size is limited by a USD (quote currency) budget.
#
# Execution:
#   - Copy this file from the strategies directory to the level above. Run with python3.

import json
import requests

from decimal import Decimal

from libraries.logger import logger
from libraries.rentseeker import bidrise
from libraries.spreadkiller import quotaask
from libraries.fillvalidator import confirmexecution


# Set quote currency (USD in this case) budget.
# This amount should exceed 20 cents ['0.00001' is the minimum for YFIUSD].
# Configure price rise desired in decimal terms.
# For example, 20 basis points is '0.002'. This covers Gemini API trading fees round trip!
pair = 'YFIUSD'
cash = '1.376'
rise = '0.005'

# Open websocket connection.
# Wait for bids to rise in price.
logger.info(f'waiting for {pair} to rise {Decimal(rise)*100}% in price to buy {cash} {pair[3:]} worth..')
deal = bidrise( pair, rise )
if deal:

    # Submit limit ask order.
    logger.debug(f'submitting {pair} aggressive limit ask order.')
    post = quotaask( pair, cash )
    post = post.json()
    dump = json.dumps( post, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( dump )

    # Define poststatus class.
    # Purpose: Stores the state of the orderid parameter upon exiting the websocket connection session.
    class Poststatus:
        def __init__(self, state): self.__state = state
        def getvalue(self): return self.__state
        def setvalue(self, state): self.__state = state

    poststatus = Poststatus(False)

    # Determine if the order was filled.
    confirmexecution( orderid = post['order_id'], poststatus = poststatus )