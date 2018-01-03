# assumes get raw data has been run

from pickle import load
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

f = open('/home/rob/results.pck', "rb")
results = load(f)
f.close()

irange = [xkey[0] for xkey in results.keys()]
jrange = [xkey[1] for xkey in results.keys()]
instruments = [xkey[2] for xkey in results.keys()]

irange = list(set(irange))
jrange = list(set(jrange))
irange.sort()
jrange.sort()

instruments = list(set(instruments))


instrument="V2X"

def get_results(results, i, j, instrument):
    if i==j:
        return np.nan
    return results[(i, j, instrument)].mean() * 250

plot_results = np.array([[get_results(results,i,j, instrument) for i in irange] for j in jrange])

plt.imshow(plot_results)
plt.colorbar()

ax = plt.gca() # grab the current axis
ax.set_xticks(range(len(irange))[1::2][:-1])
ax.set_xticklabels(irange[1::2][:-1])
ax.set_yticks(range(len(irange))[1::2][:-1])
ax.set_yticklabels(jrange[1::2][:-1])

ax.set_xlabel("A")
ax.set_ylabel("B")

plt.show()

plot_results[np.isnan(plot_results)]=-1000000
max_values=np.unravel_index(plot_results.argmax(), plot_results.shape)

print("A max %d; B max %d"  % (irange[max_values[1]], jrange[max_values[0]]))

## Run a series of t-tests versus the maximum
def t_test(acc1, acc2):
    ## acc2 needs to be higher, or will get negative numbesr
    jacc = pd.concat([acc1, acc2], axis=1)
    corr = jacc.corr()[0][1]
    adj_factor = acc1.std() / acc2.std()

    diff = acc1.mean() - (acc2.mean()*adj_factor)

    omega_1 = acc1.std() / (len(acc1.index)**.5)

    var_diff = 2 * (omega_1**2) * (1-corr)
    t_stat = diff / (var_diff**.5)

    return t_stat


def get_ttest_results(results, i, j, instrument, max_acc):
    if i==j:
        return np.nan
    return t_test(max_acc, results[(i, j, instrument)])


def get_corr_results(results, i, j, instrument, max_acc):
    if i==j:
        return np.nan

    jacc = pd.concat([max_acc, results[(i, j, instrument)]],axis=1)
    corr = jacc.corr()[0][1]

    return corr


#max_acc = results[(irange[max_values[1]], jrange[max_values[0]], instrument)]
max_acc = results[(7, 70, instrument)]

plot_results = np.array([[get_ttest_results(results,i,j, instrument, max_acc) for i in irange] for j in jrange])
#plot_results = np.array([[get_corr_results(results,i,j, instrument, max_acc) for i in irange] for j in jrange])


# delete if want to show all
#plot_results[plot_results<2]=np.nan
#plot_results[plot_results>0.99]=np.nan

plt.imshow(plot_results)
plt.colorbar()

ax = plt.gca() # grab the current axis
ax.set_xticks(range(len(irange))[1::2][:-1])
ax.set_xticklabels(irange[1::2][:-1])
ax.set_yticks(range(len(irange))[1::2][:-1])
ax.set_yticklabels(jrange[1::2][:-1])

ax.set_xlabel("A")
ax.set_ylabel("B")

ax.set_title(instrument)
plt.show()

# and now replot
# correlations

## pool the lot of em


def pooled_results(results, i,j):
    all_results = pd.concat([results[(i, j, instrument)] for instrument in instruments], axis=0)
    return all_results

def get_results_all_instruments(results, i, j):
    if i==j:
        return np.nan

    return pooled_results(results, i, j).mean() * 250

plot_results = np.array([[get_results_all_instruments(results,i,j) for i in irange] for j in jrange])

plt.imshow(plot_results)
plt.colorbar()

ax = plt.gca() # grab the current axis
ax.set_xticks(range(len(irange))[1::2][:-1])
ax.set_xticklabels(irange[1::2][:-1])
ax.set_yticks(range(len(irange))[1::2][:-1])
ax.set_yticklabels(jrange[1::2][:-1])

ax.set_xlabel("A")
ax.set_ylabel("B")

plt.show()

def get_ttest_results_pooled(results, i, j,  max_acc):
    if i==j:
        return np.nan
    return t_test(max_acc, pooled_results(results, i, j))

plot_results[np.isnan(plot_results)]=-1000000
max_values=np.unravel_index(plot_results.argmax(), plot_results.shape)

print("A max %d; B max %d"  % (irange[max_values[1]], jrange[max_values[0]]))

max_acc = pooled_results(results,irange[max_values[1]], jrange[max_values[0]])

plot_results = np.array([[get_ttest_results_pooled(results,i,j, max_acc) for i in irange] for j in jrange])

plot_results[plot_results<2]=np.nan

plt.imshow(plot_results)
plt.colorbar()

ax = plt.gca() # grab the current axis
ax.set_xticks(range(len(irange))[1::2][:-1])
ax.set_xticklabels(irange[1::2][:-1])
ax.set_yticks(range(len(irange))[1::2][:-1])
ax.set_yticklabels(jrange[1::2][:-1])

ax.set_xlabel("A")
ax.set_ylabel("B")

plt.show()
