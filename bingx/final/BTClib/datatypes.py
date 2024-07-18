from BTClib.constants import *
from BTClib.other import *

class order_detail:
    global ORDER_TIMEOUT
    def __init__(self,symbol,orderId, timeout_counter_initial = ORDER_TIMEOUT):
        self.orderId = orderId
        self.symbol = symbol
        self.timeout_counter = timeout_counter_initial

class Strategy(Enum):
    _settings_ = NoAlias
    THREESOLDIERS = 3 + 1
    ENGULFING = 2 + 1
    SHOOTINGSTAR = 1 + 1 
    HAMMER = 1 + 1

class Pair:
    '''
    # attributes
        # pairName: str
        # buy_percentage_current: float
        # sell_percentage_current: float
        # strategies: list (contains multiple Strategy)
    '''
    def __init__(self) -> None:
        self._price_updated = False
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS, Strategy.SHOOTINGSTAR, Strategy.HAMMER]

    def __init__(self, pairName: str) -> None:
        self._price_updated = False
        self.pairName = pairName
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS, Strategy.SHOOTINGSTAR, Strategy.HAMMER]

    def setPairName(self,pairName: str) -> None:
        self.pairName = pairName

    def setStrategies(self, strategies: list) -> None:
        self.strategies = strategies

    def appendStrategies(self, strategy: Strategy) -> None:
        self.strategies.append(strategy)

    def setBuyPercentage(self, new_buy_percentage: float) -> None:
        self.buy_percentage_current = new_buy_percentage

    def setSellPercentage(self, new_sell_percentage: float) -> None:
        self.sell_percentage_current = new_sell_percentage

    def clearStrategies(self) -> None:
        self.strategies = []

    def popStrategy(self) -> None:
        assert len(self.strategies > 0), 'strategies does not have any member!'
        self.strategies.pop()

    def extract_currency_name(self) -> str:
        for index in range(len(self.pairName)):
            if self.pairName[index] == '-':
                dash_index = index
                break

        currency = self.pairName[0:dash_index]
        return currency

    def update_latest_price(self,bingx_client: BingX):
        self._price_updated = True
        res = bingx_client.spot.market.get_k_line_data(self.pairName,Interval.MINUTELY_ONEMINUTE.value)
        self._latest_price = res[0][1]

        return

    def get_latest_price(self):
        assert self._price_updated , "latest price was never set, but there was an attempt to access it!"
        return self._latest_price
        
class StrategyChecker:
    class ENGLUFING:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:
            if cdf.loc[0]['isGreen'] == 0.0:
                if cdf.loc[1]['isGreen'] == 1.0 or engulfing_first_candle_color_dont_care_sell:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
                            self.suitableForSell = True
                
            if cdf.loc[0]['isGreen'] == 1.0:
                if cdf.loc[1]['isGreen'] == 0.0 or engulfing_first_candle_color_dont_care_buy:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
                            self.suitableForBuy = True 
            
            return self.suitableForBuy, self.suitableForSell

    class THREESOLDIERS:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False
        def checkData(self,cdf) -> bool | bool:
            if cdf.loc[0]['isGreen'] == 1.0:
                if cdf.loc[1]['isGreen'] == 1.0:
                    if cdf.loc[2]['isGreen'] == 1.0:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
                            if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
                                self.suitableForBuy = True
                    
            if cdf.loc[0]['isGreen'] == 0.0:
                if cdf.loc[1]['isGreen'] == 0.0:
                    if cdf.loc[2]['isGreen'] == 0.0:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
                            if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
                                self.suitableForSell = True

            return self.suitableForBuy, self.suitableForSell
            
    class HAMMER:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:               
            if cdf.loc[0]['isGreen'] == 1.0 or hammer_candle_color_dont_care:
                if cdf.loc[0]['tailLen'] / cdf.loc[0]['bodyLen'] >= hammer_tail_to_body_ratio:
                    if cdf.loc[0]['headLen'] / cdf.loc[0]['bodyLen'] <= hammer_head_to_body_ratio:
                       self.suitableForBuy = True 
            
            return self.suitableForBuy, self.suitableForSell
 
    class SHOOTINGSTAR:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:               
            if cdf.loc[0]['isGreen'] == 0.0 or shooting_star_candle_color_dont_care:
                if cdf.loc[0]['headLen'] / cdf.loc[0]['bodyLen'] >= shooting_star_head_to_body_ratio:
                    if cdf.loc[0]['tailLen'] / cdf.loc[0]['bodyLen'] <= shooting_star_tail_to_body_ratio:
                        self.suitableForSell = True 
            
            return self.suitableForBuy, self.suitableForSell

class Interval(Enum):

    MINUTELY_ONEMINUTE = '1m'
    MINUTELY_THREEMINUTE = '3m'
    MINUTELY_FIVEMINUTE = '5m'
    MINUTELY_FIFTEENMINUTE = '15m'
    MINUTELY_THIRTYMINUTE = '30m'

    HOURLY_ONEHOUR = '1h'
    HOURLY_TWOHOUR = '2h'
    HOURLY_FOURHOUR = '4h'
    HOURLY_SIXHOUR = '6h'
    HOURLY_EIGHTHOUR = '8h'
    HOURLY_TWELVEHOUR = '12h'

    DAILY_ONEDAY = '1d'

    WEEKLY_ONEWEEK = '1w'

    MONTHLY_ONEMONTH = '1M'

class Audit(Enum):
    WEEKLY = 1
    MONTHLY = 2
