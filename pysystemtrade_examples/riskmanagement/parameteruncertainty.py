## make a gaussian distribution, size N
from scipy.stats import norm
from random import gauss
import numpy as np
from matplotlib.pyplot import show, hist, gca

stdev=3.0
Nlength=500
monte_length=10000
var_point=5
std_correction = norm.ppf(1-var_point/100.0)

assert (var_point*monte_length/100.0)>=2.0

all_std = []
all_var = []
all_es = []
all_sigma=[]

for unused in range(monte_length):

    data=[gauss(0.0, stdev) for Unused in range(Nlength)]
    sigma_est = np.std(data)
    stdev_est = np.mean(data) - std_correction*np.std(data)
    var_est = np.percentile(data, var_point)
    small_data = [x for x in data if x <= var_est]
    es_est = np.mean(small_data)

    all_std.append(stdev_est)
    all_var.append(var_est)
    all_es.append(es_est)
    all_sigma.append(sigma_est)

hist(all_std, bins=50, range=[-6.1, -3.8])
#np.std(all_std)

hist(all_var, bins=50, range=[-6.1, -3.8])
np.std(all_var)

hist(all_es, bins=50)