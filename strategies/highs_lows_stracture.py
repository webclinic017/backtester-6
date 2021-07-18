from globals import *
from backtrader import indicators, signal
from backtrader.indicator import LinePlotterIndicator
from money_mgmt.sizers import LongOnlyPortionSizer, PortionSizer
from strategies.base_strategy import BaseStrategy
from backtrader import talib
import backtrader as bt
from backtrader.order import Order
from enum import Enum
from custom_indicators import visualizers

class Direction(Enum):
    SHORT = -1
    LONG = 1

class HighsLowsStructure(BaseStrategy):
    '''
    This is a pullback strategy based on the stracture created by highest highs
    and lowest lows.
    Positive signal when price breaks the N-highest high (for long) - 
    buy order on price low-2*ATR of the breakout candle.
    The order is valid for L days - to filter out weak movements.
    Take profit - on the breakout level.
    Stop loss - buy price - 2*ATR
    Shut off strategy when volatility is too high (VIX at top 25% values of last 100 candles)

    Inspired by https://youtu.be/QKCDt2QnmeM
    AmyBrokers code: https://drive.google.com/file/d/1kou9AiNnq1MKUhfUIw71PADeKOliWka2/view

    Latest backtesting status: the trades are centerilzed around few months around the end of 2018 till
    the begining of 2019. win rate is about 50%.
    Improvements required:
    1. take profits 1 and 2
    2. decide Long/Short direction
    3. stop logic - trades go the right direction cannot loose money
    4. adjust the submitted orders during the entry period - update prices according to changes in the ATR
    5. adjust ask prices according to candle signals (for example possitive candle occurs around the asked price - support of opening position even for higher price)
    6. trade in the trend of the market only
    7. use VIX to filter trades
    '''

    params = (
        ('atr_period', 20),
        ('highs_period', 63),
        ('lows_period', 63),
        ('entry_period', 10),
        ('ma_period', 63)
    )
    
    allowed_directions = [Direction.SHORT, Direction.LONG]

    def prepare_stock(self, stock):
        stock.atr = talib.ATR(stock.high, stock.low, stock.close, timeperiod=self.p.atr_period)
        stock.highs= talib.MAX(stock, timeperiod=self.p.highs_period)
        stock.lows = talib.MIN(stock, timeperiod=self.p.lows_period)
        stock.highs_trend= talib.MAX(stock, timeperiod=self.p.atr_period)
        stock.lows_trend = talib.MIN(stock, timeperiod=self.p.atr_period)
        stock.long_ma = talib.SMA(stock, timeperiod=self.p.highs_period)
        stock.short_ma = talib.SMA(stock, timeperiod=self.p.entry_period)
        stock.entry = None
        stock.direction = None

    def check_signals(self, stock):
        if self.entry_pending(stock):
            stock.bars_since_order += 1
            if self.entry_period_passed(stock) or self.opposite_breakout(stock):
                stock.entry.cancel()
        else:
            self.update_direction(stock)
            if stock.direction not in self.allowed_directions:
                return
            if self.breakout(stock):
                self.send_orders(stock)
    
    def entry_pending(self, stock):
        return stock.entry and stock.entry.active()
    
    def entry_period_passed(self, stock):
        return stock.bars_since_order >= self.p.entry_period

    def send_orders(self, stock):
        if stock.direction is Direction.LONG:
            stock.entry = self.buy(stock, exectype=Order.Limit, price=stock.low[0] - 2*stock.atr[0], transmit=False)
            stock.stoploss = self.sell(stock, exectype=Order.Stop, price=stock.low[0] - 4*stock.atr[0], parent=stock.entry, transmit=False)
            stock.takeprofit = self.sell(stock, exectype=Order.Limit, price=stock.high[0], parent=stock.entry, transmit=True)
        if stock.direction is Direction.SHORT:
            stock.entry = self.sell(stock, exectype=Order.Limit, price=stock.high[0] + 2*stock.atr[0], transmit=False)
            stock.stoploss = self.buy(stock, exectype=Order.Stop, price=stock.high[0] + 4*stock.atr[0], parent=stock.entry, transmit=False)
            stock.takeprofit = self.buy(stock, exectype=Order.Limit, price=stock.low[0], parent=stock.entry, transmit=True)
        self.log(stock, "orders sent, %s trade. asked price: %.2f, take-profit: %.2f, stop-loss: %.2f"%(stock.direction, stock.entry.price, stock.takeprofit.price, stock.stoploss.price))
        stock.bars_since_order = 0

    def breakout(self, stock):
        # TODO try to use close price instead of high/low
        if stock.direction is Direction.LONG:
            return stock.high[0] > stock.highs[-1]
        if stock.direction is Direction.SHORT:
            return stock.low[0] < stock.lows[-1]

    def opposite_breakout(self, stock):
        if stock.direction is Direction.LONG:
            return stock.low[0] < stock.lows[-1]
        if stock.direction is Direction.SHORT:
            return stock.high[0] > stock.highs[-1]

    def update_direction(self, stock):
        # TODO improve this!
        if stock.long_ma[0] > stock.long_ma[-self.p.ma_period]:
            stock.direction = Direction.LONG
        elif stock.long_ma[0] < stock.long_ma[-self.p.ma_period]:
            stock.direction = Direction.SHORT
        else:
            stock.direction = None

    def manage_position(self, stock):
        pass
        
    def notify_order(self, order, verbose=0):
        super().notify_order(order, verbose)



class HighLowsStructureImproved(BaseStrategy):

    params = (
        ('atr_period', 20),
        ('highs_period', 63),
        ('entry_period', 10),
    )


    def prepare_stock(self, stock):
        stock.atr = talib.ATR(stock.high, stock.low, stock.close, timeperiod=self.p.atr_period)
        stock.highest = talib.MAX(stock.high, timeperiod=self.p.highs_period)
        stock.highs_breakout = HighestHighBreakoutSignal(high=stock.high, highest=stock.highest)
        # stock.highs_breakout = visualizers.SingleMarker(signals=stock.highest(-1) > stock.high, level=stock.high)
        # stock.highs_breakout2 = visualizers.SingleMarker(signals=stock.high[0]>stock.highest[-1], level=stock.high, marker='*', color='yellow')
        stock.buy_level = visualizers.PartialLevel(signal=stock.highs_breakout, level=stock.low-2*stock.atr, length=self.p.entry_period)
        stock.stop_level = visualizers.PartialLevel(signal=stock.highs_breakout, level=stock.low-3.5*stock.atr, color='salmon', length=self.p.entry_period)
        # stock.tp1 = visualizers.PartialLevel(signal=stock.low <= stock.buy_level, level=stock.high+2*stock.atr, color='seagreen')
        stock.entry, stock.stoploss, stock.takeprofit = None, None, None
        stock.bars_since_signal = None
        stock.open.forward()

    def next(self):
        for stock in self.stocks:
            self.next_stock(stock)
    
    def next_stock(self, stock):
        if self.getposition(stock):
            self.manage_position(stock)
            return
        if self.waiting_for_signal(stock):
            self.check_signals(stock)
        else:
            self.validate_conditions(stock)

    def waiting_for_signal(self,stock):
        return stock.entry is None

    def validate_conditions(self, stock):
        stock.bars_since_signal += 1
        if stock.bars_since_signal > self.p.entry_period:
            stock.entry.cancel()
        if stock.open[1] < stock.stop_level[0]:
            self.log(stock,'canceling')
            self.cancel(stock.entry)
            stock.entry = None

    def check_signals(self, stock):
        if stock.highs_breakout[0] > 0:
            size = self.getsizing(stock)
            tp1_size = size/2
            tp2_size = size - tp1_size
            # stock.entry, stock.stoploss, stock.takeprofit = self.buy_bracket(stock, price=stock.buy_level[0], stopprice=stock.stop_level[0], limitprice=stock.close[0])
            stock.entry, stock.stoploss, stock.takeprofit = self.buy_bracket(stock, price=stock.buy_level[0], stopprice=stock.stop_level[0], limitprice=stock.close[0], limitargs={'size':tp1_size})
            stock.bars_since_signal = 0
    
    def update_orders(self, stock):
        if stock.entry: 
            if stock.entry.alive():
                # stock.entry.cancel()
                # stock.entry = self.buy(stock, exectype=Order.Limit, price=stock.buy_level[0], transmit=False)
                stock.bars_since_signal += 1
            else:
                stock.entry, stock.stoploss, stock.takeprofit = None, None, None
                stock.bars_since_signal = None
        

    def buy_signal(self, stock):
        return stock.high[0] > stock.highest[-1]
        

    def manage_position(self, stock):
        stock.bars_since_signal = None
        stock.entry = None
        pass

    def notify_order(self, order, verbose=1):
        super().notify_order(order, verbose)


class BuyLevel(bt.Indicator):
    lines = ('buy_level',)
    plotlines = dict(buy_level=dict(color='deepskyblue', linewidth=9.0, linestyle='dotted'))
    plotinfo = dict(plot=True, subplot=False)

    def __init__(self, signal, level, length=10):
        self.signal = signal
        self.level = level
        self.length = length

    def once(self, start, end):
        for i in range(start,end):
            for j in range(i-self.length, i):
                if not math.isnan(self.signal[j]):
                    self.lines.buy_level[i] = self.level[j]
                    break

class HighestHighBreakoutSignal(bt.Indicator):
    lines = ('breakout',)
    plotinfo = dict(plot=True, subplot=False, plotlinelabels=True)
    plotlines = dict(breakout=dict(
        marker='d', markersize=8.0, color='springgreen')
        )
    
    def __init__(self, high, highest):
        self.high = high
        self.highest = highest
        # TODO Potential bug with the left most value on the chart
        # self.addminperiod(1)

    def once(self, start, end):
        for i in range(start, end):
            self.lines.breakout[i] = self.high[i] if self.high[i] > self.highest[i-1] else float('nan')  # If I'm getting out-of-index beacuase of the -1 add this to init: 'self.addminperiod(1)'

