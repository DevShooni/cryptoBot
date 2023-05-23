import asyncio
import json
import logging
import time

import numpy as np
import websocket
import websockets

import apca_client
from dqn import DQN
from trading_environment import TradingEnvironment

# ENABLE LOGGING - options, DEBUG,INFO, WARNING?
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize TradingEnvironment
env = TradingEnvironment()


# Preprocess historical and live data
def preprocess_data(data, is_live_data=False):
    if is_live_data:
        kline_data = data['k']
        data = [
            float(kline_data['o']), float(kline_data['h']), float(kline_data['l']),
            float(kline_data['c']), float(kline_data['v']), float(kline_data['q'])
        ]
    else:
        data = [[x[1], x[2], x[3], x[4], x[5], x[6]] for x in data]

    processed_data = np.array(data)
    return processed_data
"""
# Load historical data
historical_data = requests.get('https://api.binance.us/api/v3/'
                               'klines?symbol=BTCUSDT&interval=1m&limit=1000').json()
processed_historical_data = preprocess_data(historical_data, is_live_data=False)
print(historical_data)
print(processed_historical_data)
"""

action_size = 2  # Buy, Do Nothing
state_size = 6  # Open, High, Low, Close, Volume, Symbol


# Initialize DQN agent
agent = DQN(state_size, action_size)
agent.load_model()
print("Agent initialized.")



def calculate_reward(cash, last_cash):
    reward = float(cash) - float(last_cash)
    return float(reward)


# Calculate reward based on trading strategy
def send_action(state, action, done, paper=True):
    if paper:
        if action == 0:  # Buy
            order = asyncio.run(apca_client.post_alpaca_order('hold'))
        elif action == 1:  # Sell
            pass#order = asyncio.run(apca_client.post_alpaca_order('sell'))
        elif action == 2:  # Hold / Limit Sell
            order = asyncio.run(apca_client.post_alpaca_order('hold'))
        else:
            logger.info('Big Error. Big Fail. Should not print this ever...')

    # Historical Data
    else:
        if action == 0:  # Buy
            env.buy(state[0, 0])  # Buy one unit
        else:  # Sell
            env.sell(state[0, 0])  # Sell one unit
        reward = env.get_portfolio_value()

"""
# Historical Data Training
for i in range(len(processed_historical_data) - 1):
    state = processed_historical_data[i].reshape(1, state_size)
    next_state = processed_historical_data[i + 1].reshape(1, state_size)
    # Choose an action (buy, hold, or sell)
    action = agent.act(state)
    send_action(state, action, done=False, paper=False)
    reward = env.get_portfolio_value()
    agent.replay(49)

    print("Training step: " + str(i) + " / " + str(len(processed_historical_data) - 1) + " complete.")
    print("Reward: " + str(reward) + ", Action: " + str(action))

agent.save_model()
print("Training complete.")
"""

# Live Paper Data and Training
def on_open(ws):
    agent.load_model()
    logger.info('opened connection. agent loaded.')


def on_close(ws, close_status_code, close_msg):
    agent.save_model()
    logger.info('closed connection. agent saved.')


message_count = 0

"""
def on_message(ws, message):
    global message_count
    data = json.loads(message)
    # Preprocess live data
    processed_data = preprocess_data(data, is_live_data=True)
    print(message)
    print(processed_data)
    current_states = np.array(processed_data)
    next_states = np.array(processed_data)
    message_count += 1

    if message_count >= 5:
        message_count = 0
        current_states = next_states.copy
        # Update DQN agent with live data
        state = current_states
        # Choose an action (buy, hold, or sell)
        action = agent.act(current_states)
        # Calculate reward and done based on the action
        reward = send_action(current_states, action, done=False, paper=True)
        agent.remember(current_states, action, reward, next_states, done=False)
        agent.replay(49)
        next_states = np.empty_like(next_states)
        print("REWARD: ", reward)

    else:
        # Append the processed_data to the current_states list
        next_states = np.concatenate((next_states, processed_data), axis=0)
"""


def on_message(ws, message):
    last_cash = apca_client.trading_client.get_account().cash
    print(message)
    data = json.loads(message)
    training_data = []
    # Preprocess live data
    processed_data = preprocess_data(data, is_live_data=True)
    training_data.append(processed_data)
    # Update DQN agent with live data
    if len(training_data) > 2:
        training_data.pop(0)
    state = (training_data[-1]).reshape(1, state_size)
    next_state = (training_data[0]).reshape(1, state_size)

    # Choose an action (buy, hold, or sell)
    action = agent.act(state)
    # Calculate reward and done based on the action
    send_action(state, action, done=False, paper=True)
    cash = apca_client.trading_client.get_account().cash
    reward = calculate_reward(cash, last_cash)
    agent.remember(state, action, reward, next_state, done=False)

    agent.replay(49)
    agent.save_model()
    print("REWARD: ", reward)


def on_error(ws, error):
    logger.error(f"WebSocket Error: {error}")
    logger.info("Reconnecting...")
    time.sleep(3)
    start_websocket()


def start_websocket():
    wsApp = websocket.WebSocketApp(
        "wss://stream.binance.us:9443/ws/btcusdt@kline_5m",
        on_open=on_open,
        on_close=on_close,
        on_message=on_message,
        on_error=on_error,
        keep_running=True
    )
    wsApp.run_forever()


start_websocket()
