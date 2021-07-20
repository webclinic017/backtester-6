from strategies.trade_phase_strategy import TradePhase, TradePhaseStrategy


class TradePhaseStrategyTest(TradePhaseStrategy):
    def __init__(self):
        super().__init__(TradePhaseTest)


class TradePhaseTest(TradePhase):

    def next(self):
        # TODO what are you testing here?
        print('next() Trade Phase Test for feed %s'%self.feed._name)