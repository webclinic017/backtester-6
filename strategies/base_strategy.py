from datetime import datetime
import itertools
import backtrader as bt
from backtrader.feeds.csvgeneric import GenericCSVData
from backtrader.trade import Trade
from backtrader.utils.autodict import AutoDictList
import matplotlib.pylab as pylab
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Blackly, Tradimo
import globals as gb


""" 
Base class for strategy of multiple feeds
"""

class BaseStrategy(bt.Strategy):

    def __init__(self):
        self.stocks = self.datas
        for stock in self.stocks:
            self.prepare(stock)
 
    def next(self):
        for stock in self.stocks:
            if not self.getposition(data=stock):
                self.check_signals(stock)
            else:
                self.manage_position(stock)



    def plot(self, limit=0, only_trades=True, interactive_plots=True, plot_observers=True):
        pylab.rcParams['figure.figsize'] = 26, 13 # that's default image size for this interactive session
        # limit = limit or len(self.stocks)
        # feeds = list(dict(sorted(self._trades.items(), key=lambda item: len(item[1][0]))))[:limit] if only_trades else self.stocks[:limit] # for sorted trades
        plotter = Bokeh(style='bar', scheme=Blackly()) if interactive_plots else None
        print('ploting top %d feeds' % (limit or (only_trades and len(self._trades) or len(self.stocks))))
        self.set_plot_for_observers(False)
        printed = 0
        for i, stock in enumerate(self.stocks):
            if only_trades and stock not in self._trades:
                continue
            if limit and printed >= limit:
                break
            self.set_plotting(stock, True)
            self.set_plot_for_buysell_observer(True, i, stock) # this hack won't work for sorted trades - because of assumption over
            gb.cerebro.plot(plotter=plotter, style='candlestick', barup='green', numfigs=1)
            printed += 1
            self.set_plot_for_buysell_observer(False, i, stock) # this hack won't work for sorted trades - because of assumption over
            self.set_plotting(stock, False)
        if plot_observers:
            self.plot_observers(plotter)


    def set_plotting(self, feed, on):
        feed.plotinfo.plotmaster = feed
        feed.plotinfo.plot = on  # todo create a wrapper for the feed (csvData) object with attributes like indicators
        self.set_plot_for_indicators(feed, on)
    
    def plot_observers(self, plotter):
        self.set_plot_for_observers(True)
        gb.cerebro.plot(plotter)

    def set_plot_for_observers(self, is_plot):
        for observer in self.getobservers():
            observer.plotinfo.plot = is_plot

    # hacky function to turn on the buy-sell observer of the stock that is about to plot
    def set_plot_for_buysell_observer(self, plot_on, index, stock):
        observer = self.getobservers()[index+1]
        if observer.data._name != stock._name:
            raise Exception("trying to plot buy-sell observer of wrong stock")
        observer.plotinfo.plot = plot_on
        

    @staticmethod
    def add_indicator(stock, indicator, attr_name, subplot=None):
        stock.indicators = stock.indicators if hasattr(stock, 'indicators') else []
        stock.indicators.append(indicator)
        setattr(stock, attr_name, indicator)
        if subplot is not None:
            getattr(stock, attr_name).plotinfo.subplot = subplot
    
    @staticmethod
    def set_plot_for_indicators(stock, is_plot):
        if hasattr(stock, 'indicators'):
            for ind in stock.indicators:
                ind.plotinfo.plot = is_plot


    def prepare(self, stock):
        raise NotImplementedError

    def check_signals(self, stock):
        raise NotImplementedError

    def manage_position(self, stock):
        raise NotImplementedError

    def notify_order(self, order: bt.Order):
        if order.status is bt.Order.Completed or order.status is bt.Order.Partial:
            self.log(order.data, "order %s: %s %s, price: %.2f, size: %s" % (
                order.getstatusname(), order.ordtypename(), order.getordername(), order.price or order.created.price, order.size))
        else: # the same message for now
            self.log(order.data, "order %s: %s %s, price: %.2f, size: %s" % (
                order.getstatusname(), order.ordtypename(), order.getordername(), order.price or order.created.price, order.size))

    def notify_trade(self, trade: bt.Trade):
        if (trade.status <= 1): # created or open
            self.log(trade.data, 'trade %s, execution price (MAYBE): %s, size: %s, date: %s' % ( #TODO remove MAYBE after validating the the price is the execution price
                trade.status_names[trade.status], trade.price, trade.size, trade.open_datetime().date()))
        else: 
            self.log(trade.data, 'trade %s, pnl %s, size: %s, date: %s' % (
                trade.status_names[trade.status], trade.pnl, trade.size, trade.close_datetime().date()))

    def log(self, stock, txt):
        ''' logging function for this strategy'''
        date = stock.datetime.date()
        print('%s @ %s: %s' % (stock._name, date.isoformat(), txt))


    def get_open_trade(self, stock): #TODO handle trade management by my strategy
        trades : AutoDictList = self._trades[stock]  # self._trades[stock] is {data: {order_id: [trades]}}
        open_trades = [t for t in itertools.chain(*self._trades[stock].values()) if t.isopen]
        if len(open_trades) > 1:
            raise Exception('Warning - more than one open position for %s, trades: %s'%(stock, open_trades))
        return open_trades[0]