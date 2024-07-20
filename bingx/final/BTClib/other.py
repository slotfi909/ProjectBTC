###
###############################
# todo
# add sensitive info to .env file
# check pair_min_trade for both market trade and limit trade
# price is queried two times, once in get_total_balance and then in 
# do all the selling first the do the buy
# add option to buy all market or half market half limit
# add option to do buy and sell in different intervals
# add option of using indicators -> MAs
# add special sell/ buy/ learning rate for each strategy
# prevent buy/sell when candles bodyLens are too small
# add stop price for market trades
# add buy% and sell % in constractor of pair
# add futures!
# add max tries function for communication
# add audit
# create code way more modular
# prevent division by zero
###############################


DEBUG_MODE = True

old_date = ''
logFile = ''