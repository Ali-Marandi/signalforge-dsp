import numpy as np
from signalforge_finance.timeseries_models import arima_forecast


def test_arima_forecast_length():
    data = [float(i) for i in range(50)]
    f, ci = arima_forecast(data, order=(1,0,0), steps=3)
    assert len(f) == 3
    assert ci.shape[0] == 3
