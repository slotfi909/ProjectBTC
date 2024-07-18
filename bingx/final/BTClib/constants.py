import pandas as pd
import numpy as np
import math
from BTClib.bingX import BingX
import time
from BTClib.bingX.spot import types
from aenum import Enum, NoAlias
from datetime import date
import sys
import os
###

MARKET_BUY_PERCENTAGE = 50
LIMIT_BUY_PERCENTAGE = 100 - MARKET_BUY_PERCENTAGE
MARKET_SELL_PERCENTAGE = 50
LIMIT_SELL_PERCENTAGE = 100 - MARKET_SELL_PERCENTAGE
ORDER_TIMEOUT = 4

engulfing_body_condition = 2
engulfing_first_candle_color_dont_care_buy = True
engulfing_first_candle_color_dont_care_sell = True
hammer_candle_color_dont_care = False
shooting_star_candle_color_dont_care = True
threesoldiers_body_condition = [1.01,1.02]
hammer_tail_to_body_ratio = 6
hammer_head_to_body_ratio = 0.1
shooting_star_head_to_body_ratio = 6
shooting_star_tail_to_body_ratio = 0.1


communication_max_tries = 5
buy_percentage_init = 10
sell_percentage_init = 13
learning_rate_buy = 0.9
learning_rate_sell = 1.1
buyPositionsNumber = 0
sellPositionsNumber = 0
PAIR_MIN_TRADE_USDT = 5
_limit_orders = []