#!/usr/bin/env python3


import requests
import ssl
import json
import websocket
import datetime
import time
import _thread as thread

from decimal import Decimal

from libraries.logger import logger as logger
from libraries.messenger import smsalert as smsalert

import libraries.authenticator as authenticator
import libraries.resourcelocator as resourcelocator

def askfall (
        pair: str,
        drop: str
        ) -> None:

    # Define high class.
    # Purpose: Stores the highest trading price reached during the websocket connection session.
    class High:
        def __init__(self, price): self.__price = price
        def getvalue(self): return self.__price
        def setvalue(self, price): self.__price = price

    # Define deal class.
    # Purpose: Stores the deal (last) price reached during the websocket connection session.
    class Deal:
        def __init__(self, price): self.__price = price
        def getvalue(self): return self.__price
        def setvalue(self, price): self.__price = price

    # Instantiate high/deal objects.
    high = High(0)
    deal = Deal(0)

    # Construct subscription request.
    subscriptionrequest = f'{{"type": "subscribe","subscriptions":[{{"name":"l2","symbols":["{pair}"]}}]}}'

    # Define websocet functions.
    def on_open( ws, subscriptionrequest = subscriptionrequest ):
        def run(*args):
            ws.send( subscriptionrequest )
        thread.start_new_thread(run, ())
        logger.debug(f'{ws} connection opened.')
    def on_close(ws): logger.debug(f'{ws} connection closed.')
    def on_error(ws, error): logger.debug(error)
    def on_message(ws, message, drop = drop, pair = pair, high = high, deal = deal):
        dictionary = json.loads( message )
        percentoff = Decimal( drop )
        sessionmax = Decimal( high.getvalue() )

        # Unncomment this statement to debug messages: logger.debug(dictionary)

        # Process "type": "update" messages with events only.
        if 'l2_updates' in dictionary['type']:
            if dictionary['changes'] != []:
                changes = dictionary['changes']

                # Rank bids and determine the highest bid in the orderbook from dYdX update response.
                askranking = [ Decimal(change[1]) for change in changes if change[0] == 'sell' ]
                minimumask = min(askranking)

                if minimumask.compare( Decimal(sessionmax) ) == 1 :
                        sessionmax = minimumask
                        high.setvalue(minimumask)

                # Calculate movement away from high [if any].
                move = 100 * ( sessionmax - minimumask ) / sessionmax

                # Display impact of event information received.
                logger.info( f'{move:.2f}% off highs [{sessionmax}] : {pair} is {minimumask} presently.' )

                # Define bargain (sale) price.
                sale = Decimal( sessionmax * ( 1 - percentoff ) )

                # Exit loop if there's a sale.
                if sale.compare( minimumask ) == 1 :
                    logger.info( f'{pair} [now {minimumask:.2f}] just went on sale [dropped below {sale:.2f}].' )
                    smsalert( f'There was a {percentoff*100}% drop in the price of the {pair} pair on Gemini.' )

                    # Update deal price.
                    deal.setvalue(minimumask)
                    ws.close()

    # Construct payload.
    request = resourcelocator.sockserver + '/v2/marketdata'
    nonce = int(time.time()*1000)
    payload = {
        'request': request,
        'nonce': nonce
    }
    authenticator.authenticate(payload)

    # Establish websocket connection.
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(request, on_open = on_open, on_message = on_message, on_error = on_error, on_close = on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    # Return value on discount only.
    last = Decimal( deal.getvalue() )
    if last.compare(0) == 1 :
        return last
    else: return False

def pricedrop(
        pair: str,
        drop: str
    ) -> None:

    # Define high class.
    # Purpose: Stores the highest trading price reached during the websocket connection session.
    class High:
        def __init__(self, price): self.__price = price
        def getvalue(self): return self.__price
        def setvalue(self, price): self.__price = price

    # Define deal class.
    # Purpose: Stores the deal (last) price reached during the websocket connection session.
    class Deal:
        def __init__(self, price): self.__price = price
        def getvalue(self): return self.__price
        def setvalue(self, price): self.__price = price

    # Instantiate high/deal objects.
    high = High(0)
    deal = Deal(0)

    # Define websocet functions.
    def on_close(ws): logger.debug(f'{ws} connection closed.')
    def on_open(ws): logger.debug(f'{ws} connection opened.')
    def on_error(ws, error): logger.debug(error)
    def on_message(ws, message, drop=drop, pair=pair, high=high, deal=deal):
        dictionary = json.loads( message )
        percentoff = Decimal( drop )
        sessionmax = Decimal( high.getvalue() )
        # Unncomment this statement to debug messages:
        logger.debug(dictionary)

        # Process "type": "update" messages with events only.
        if 'update' in dictionary['type']:
            if dictionary['events'] != []:
                events = dictionary['events']

                # Process "type": "trade" events for latest price.
                for event in events:
                    if event['type'] == 'trade' : last = Decimal( event["price"] )
                    if last.compare( Decimal(sessionmax) ) == 1 :
                        sessionmax = last
                        high.setvalue(last)

                    # Calculate movement away from high [if any].
                    move = 100 * ( sessionmax - last ) / sessionmax

                    # Display impact of event information received.
                    logger.info( f'{move:.2f}% off highs [{sessionmax}] : {pair} is {last} presently : [Message ID: {dictionary["socket_sequence"]}].' )

                    # Define bargain (sale) price.
                    sale = Decimal( sessionmax * ( 1 - percentoff ) )

                    # Exit loop if there's a sale.
                    if sale.compare(last) == 1 :
                        logger.info( f'{pair} [now {last:.2f}] just went on sale [dropped below {sale:.2f}].' )
                        smsalert( f'There was a {percentoff*100}% drop in the price of the {pair} pair on Gemini.' )

                        # Update deal price.
                        deal.setvalue(last)
                        ws.close()

    # Construct payload.
    request = resourcelocator.sockserver + '/v1/marketdata/' + pair
    nonce = int(time.time()*1000)
    payload = {
        'request': request,
        'nonce': nonce
    }
    authenticator.authenticate(payload)

    # Establish websocket connection.
    ws = websocket.WebSocketApp(request, on_open = on_open, on_message = on_message, on_error = on_error, on_close = on_close)
    ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    # Return value on discount only.
    last = Decimal( deal.getvalue() )
    if last.compare(0) == 1 :
        return last
    else: return False