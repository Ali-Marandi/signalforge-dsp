from signalforge_finance.indicators import sma, ema, rsi, macd


def test_sma_ema_rsi_macd():
    values = [1.0, 2.0, 3.0, 2.5, 2.0, 3.5, 4.0]
    s = sma(values, 3)
    assert len(s) == len(values)
    e = ema(values, 3)
    assert len(e) == len(values)
    r = rsi(values, 3)
    assert len(r) == len(values)
    ml, sl, h = macd(values)
    assert len(ml) == len(values)
    assert len(sl) == len(values)
    assert len(h) == len(values)
