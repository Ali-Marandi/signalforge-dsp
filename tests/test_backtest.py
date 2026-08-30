from signalforge_finance.backtest import sma_crossover_backtest


def test_sma_backtest_simple():
    prices = [i + (1 if i%20<10 else -1) for i in range(200)]
    result = sma_crossover_backtest(prices, short_window=5, long_window=20)
    assert "trades" in result
    assert isinstance(result["trades"], list)
