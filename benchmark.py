import pandas as pd
import numpy as np
import timeit

# Generate some dummy data
np.random.seed(0)
n = 100000
df = pd.DataFrame({'Volume': np.random.randint(100, 1000, size=n)})
period = 5

def original_method(df, period):
    return df["Volume"].rolling(window=period).mean().iloc[-2]

def new_method(df, period):
    return df["Volume"].iloc[-(period + 1):-1].mean()

# Verify correctness
assert np.isclose(original_method(df, period), new_method(df, period))

# Benchmark
orig_time = timeit.timeit(lambda: original_method(df, period), number=1000)
new_time = timeit.timeit(lambda: new_method(df, period), number=1000)

print(f"Original method: {orig_time:.5f} seconds")
print(f"New method: {new_time:.5f} seconds")
print(f"Improvement: {orig_time / new_time:.2f}x faster")
