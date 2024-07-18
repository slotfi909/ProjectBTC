from BTClib.bingX.spot.market import Market
from BTClib.bingX.spot.trade import Trade
from BTClib.bingX.spot.transfer import Transfer


class Spot:
    def __init__(self, api_key: str, secret_key: str) -> None:
        self.trade = Trade(api_key, secret_key)
        self.market = Market(api_key, secret_key)
        self.transfer = Transfer(api_key, secret_key)