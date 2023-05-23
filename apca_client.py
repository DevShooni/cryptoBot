from alpaca.trading import TimeInForce
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, \
    StopLimitOrderRequest, ClosePositionRequest
from alpaca.trading.stream import *
from alpaca.data.requests import *

import requests
import asyncio

import time
import logging
import config


# ENABLE LOGGING - options, DEBUG,INFO, WARNING?
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


URL = 'https://paper-api.alpaca.markets/v2/'
headers = {
        'APCA-API-KEY-ID': config.APCA_API_KEY_ID,
        'APCA-API-SECRET-KEY': config.APCA_API_SECRET_KEY
}

# Initialize Alpaca trading client
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)

# Trading variables
notional_size = 100  # $10 per trade
crypto_fee = 0.0040  # 0.4% fee per trade


def avg_price():
    request_avg_price = requests.get('https://api.binance.us/api/v3/avgPrice?symbol=BTCUSD', headers=headers).json()
    avg_price = request_avg_price['price']
    return avg_price


def stop_price(avg_price):
    stop_price = float(avg_price) * 0.998
    return stop_price


def limit_price(avg_price):
    limit_price = float(avg_price) * 1.003
    return limit_price


# Post an order to Alpaca
async def post_alpaca_order(side):
    try:
        if side == 'buy':
            buy_data = LimitOrderRequest(
                symbol="BTCUSD",
                notional=notional_size,
                side='buy',
                type='limit',
                limit_price=stop_price(avg_price()),
                time_in_force=TimeInForce.GTC,
            )
            buy_order = trading_client.submit_order(
                order_data=buy_data
            )

            logger.info(
                "Buy Limit Order placed for BTC/USD"
            )
            return trading_client.get_order_by_id(buy_order.id)

        elif side == 'sell':
            sell_data = StopLimitOrderRequest(
                symbol="BTCUSD",
                notional=notional_size,
                side='sell',
                type='stop_limit',
                time_in_force=TimeInForce.GTC,
                stop_price=stop_price(avg_price()),
                limit_price=limit_price(avg_price())
            )
            sell_order = trading_client.submit_order(
                order_data=sell_data
            )
            # sell_order = True
            logger.info(
                "Sell Stop Limit Order placed for BTC/USD"
            )

            # Wait for sell order to be completed or timeout
            start_time = time.time()
            timeout = 20

            while True:
                try:
                    check_order = trading_client.get_order_by_id(sell_order.id)
                except Exception as e:
                    continue
                if check_order.status == 'filled':
                    break
                elif time.time() - start_time > timeout:
                    # Cancel the buy order
                    trading_client.cancel_order_by_id(sell_order.id)
                    logger.info("Sell order timed out and was canceled")

                    # Place a new sell market order
                    sell_data = MarketOrderRequest(
                        symbol="BTCUSD",
                        notional=notional_size,
                        side='sell',
                        time_in_force=TimeInForce.GTC
                    )
                    sell_order = trading_client.submit_order(
                        order_data=sell_data
                    )

                    logger.info(
                        "Sell Market Order placed for BTC/USD due to timeout"
                    )
                    break
                else:
                    pass

            return trading_client.get_order_by_id(sell_order.id)

        elif side == 'hold':
            buy_data = LimitOrderRequest(
                symbol="BTCUSD",
                qty=1,
                side='buy',
                type='limit',
                limit_price=stop_price(avg_price()),
                time_in_force=TimeInForce.GTC,
            )
            buy_order = trading_client.submit_order(
                order_data=buy_data
            )

            logger.info(
                "Buy Limit Order placed for BTC/USD"
            )

            start_time = time.time()
            timeout = 30

            while trading_client.get_order_by_id(buy_order.id).status != ('filled' or 'partially_filled'):
                if time.time() - start_time > timeout:
                    # Cancel the buy order
                    trading_client.cancel_order_by_id(buy_order.id)
                    logger.info("Buy order timed out and was canceled")
                    break
            else:
                sell_data = StopLimitOrderRequest(
                    symbol="BTCUSD",
                    qty=1,
                    side='sell',
                    type='stop_limit',
                    time_in_force=TimeInForce.GTC,
                    stop_price=stop_price(avg_price()),
                    limit_price=limit_price(avg_price())
                )
                sell_order = trading_client.submit_order(
                    order_data=sell_data
                )
                # sell_order = True
                logger.info(
                    "Sell Stop Limit Order placed for BTC/USD"
                )

                # Wait for sell order to be completed or timeout
                start_time = time.time()
                timeout = 30

                while trading_client.get_order_by_id(sell_order.id).status != 'filled':
                    if time.time() - start_time > timeout:
                        # Cancel the buy order
                        trading_client.cancel_order_by_id(sell_order.id)
                        logger.info("Sell order timed out and was canceled")

                        # Place a new sell market order
                        sell_data = MarketOrderRequest(
                            symbol="BTCUSD",
                            qty=1,
                            side='sell',
                            time_in_force=TimeInForce.GTC
                        )
                        sell_order = trading_client.submit_order(
                            order_data=sell_data
                        )

                        logger.info(
                            "Sell Market Order placed for BTC/USD due to timeout"
                        )
                        break
                    else:
                        pass


    except Exception as e:
        logger.exception(
            "There was an issue placing an order: ".format(e))
        return False
