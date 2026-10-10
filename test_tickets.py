import pandas as pd
import numpy as np
from tickets import analizar_volumen

def test_analizar_volumen():
    # Mock data to simulate DataFrame with "Volume"
    data = {
        "Volume": [100, 200, 300, 400, 500, 600, 700]
    }
    df = pd.DataFrame(data)

    # Test with period 3
    # last day volume is 700
    # previous 3 days: 400, 500, 600
    # avg = (400+500+600)/3 = 500
    # change_pct = (700-500)/500 * 100 = 40% (which is > 30% threshold, ALTO)
    result = analizar_volumen(df, period=3)
    assert "40.0%" in result
    assert "ALTO" in result

    # Test edge case: avg is 0
    data_zero = {
        "Volume": [0, 0, 0, 100]
    }
    df_zero = pd.DataFrame(data_zero)
    result_zero = analizar_volumen(df_zero, period=3)
    assert "N/A Avg" in result_zero

    # Test normal volume (change <= 30%)
    data_normal = {
        "Volume": [100, 100, 100, 100, 110]
    }
    df_normal = pd.DataFrame(data_normal)
    # prev 3: 100, 100, 100 -> avg = 100
    # today: 110
    # change = 10%
    result_normal = analizar_volumen(df_normal, period=3)
    assert "10.0%" in result_normal
    assert "ALTO" not in result_normal

    print("All tests passed!")
