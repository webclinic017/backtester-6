from Strategies import IkfStrategy
import backtrader as bt
import datetime
import os.path
import sys
from Strategies.DojiStrategyLong import DojiLongStrategy
from Analyzers.BasicSradeStats import BasicTradeStats
import backtrader.analyzers as btanalyzers
import matplotlib.pylab as pylab
from iknowfirst.iknowfirst import retrieve_forecasts_data, retrieve_stocks
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Blackly, Tradimo


cerebro = bt.Cerebro()


def main():
    add_strategies()
    # add_data(limit=0, stocks=retrieve_stocks(), dirpath='ikf_stocks')
    # add_data(limit=0, dirpath='data_feeds')
    IkfStrategy.add_data(limit=0, dirpath='ikf_stocks', cerebro=cerebro)
    # add_analyzer()
    global strategies
    strategies = backtest()
    # show_statistics(strategies)
    # plot(3, only_trades=False)


def add_strategies():
    cerebro.addstrategy(IkfStrategy.IkfStrategy, forecasts=retrieve_forecasts_data())
    cerebro.addstrategy(DojiLongStrategy)


def add_data(limit=0, dirpath='data_feeds'):
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    dirpath = os.path.join(modpath, dirpath)
    stocks = os.listdir(dirpath)
    stocks = stocks[:limit or len(stocks)]
    print('adding {} data feeds'.format(len(stocks)))
    for i, stock in enumerate(stocks):
        feed = bt.feeds.GenericCSVData(
            dataname=os.path.join(dirpath, stock), fromdate=datetime.datetime(2015, 4, 4),
            todate=datetime.datetime(2020, 3, 10), dtformat='%Y-%m-%d',
            high=1, low=2, open=3, close=4)
        feed.plotinfo.plotmaster = None
        feed.plotinfo.plot = False
        cerebro.adddata(feed, name=stock.strip('.csv'))
        
def add_analyzer():
    cerebro.addanalyzer(BasicTradeStats, _name='basic_trade_stats')


def backtest():
    cerebro.broker.setcash(10000.0)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    print('backtesting strategy')
    strategies = cerebro.run()
    return strategies


def set_plot_observers(plot):
    for observer in cerebro.runstrats[0][0].getobservers():
        observer.plotinfo.plot = plot

def plot_observers(plotter):
    set_plot_observers(True)
    cerebro.plot(plotter)

def set_plotting(feed, on):
    feed.plotinfo.plotmaster = feed
    feed.plotinfo.plot = on  # todo create a wrapper for the feed (csvData) object with attributes like indicators
    feed.indicator1.plotinfo.plot = on
    feed.indicator2.plotinfo.plot = on
    feed.indicator3.plotinfo.plot = on
    feed.indicator4.plotinfo.plot = on
    feed.indicator5.plotinfo.plot = on
    feed.indicator6.plotinfo.plot = on


def plot(max=1, only_trades=True, interactive_plots=True):
    pylab.rcParams['figure.figsize'] = 26, 13 # that's default image size for this interactive session
    feeds = list(dict(sorted(strategies[0]._trades.items(), key=lambda item: len(
        item[1][0]))))[:max] if only_trades else cerebro.datas[:max]
    plotter = Bokeh(style='bar', scheme=Blackly()) if interactive_plots else None
    print('ploting top %d feeds' % max)
    set_plot_observers(False)
    for i, feed in enumerate(feeds):
        set_plotting(feed, True)
        cerebro.plot(plotter=plotter, style='candlestick', barup='green', numfigs=1)
        set_plotting(feed, False)
    # plot_observers(plotter)


def show_statistics(strategies):
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    for each in strategies[0].analyzers:
        each.print()

if __name__ == '__main__':
    main()
