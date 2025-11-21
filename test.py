print("Hello, world!")

import matplotlib.pyplot as plt
import numpy as np


def generate_sin(time: np.ndarray):
    return np.sin(time)


time = np.linspace(0, 100, 10**5)
value = generate_sin(time)
plt.plot(time, value)
plt.show()
