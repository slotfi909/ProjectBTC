MAX_LOOP = 100 # controls the infinite loop inside _calculate_leverage function

def calculate_margin_and_leverage(total, specifiedMoney, risk, reward, fraction):
    recommendedLoss = total / fraction
    recommendedLeverage = _calculate_optimized_leverage(specifiedMoney, risk, recommendedLoss)
    final_margin = _calculate_margin(specifiedMoney, risk, recommendedLeverage)
    recommendedLeverage -= 1 # so we make sure we never ever hit liquidity

    return final_margin, recommendedLeverage

def _calculate_optimized_leverage(specifiedMoney, risk, loss):
    leverageArray = [1,2]
    while(leverageArray[-1] !=leverageArray[-2]):
        newMargin = _calculate_margin(specifiedMoney, risk, leverageArray[-1])
        newLeverage = _calulate_leverage(newMargin, risk, loss)
        leverageArray.append(newLeverage)
    
    return leverageArray[-1]

def _calulate_leverage(margin, risk, loss):
    i = 1
    cnt = 0
    while(1):
        cnt += 1
        if cnt > MAX_LOOP:
            raise Exception("counter exceeded maximum allowed iteration in leverage calculator.. terminating")
        
        if (margin * risk * i) / 100 > loss:
            break
        else: 
            i += 1
    return i

def _calculate_margin(specifiedMoney, risk, leverage):
    return specifiedMoney / (1 + (risk / 100) * leverage)