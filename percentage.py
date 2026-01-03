import pandas as pd
import numpy as np


def percentage (AElo, HElo):
  ex = 1 / (1+ 10 ** ((HElo - AElo)/400))
  return ex
