from pickle import load, dump
from syscore.pdutils import align_to_joint

ans = load(open("/home/rob/data.pck", "rb"))

[roll_acc, idm, acc_curve, mkt_counters] = ans

# plot IDM against market count, scattered

mkt_count_for_scatter = []
idm_for_scatter = []
roll_acc_for_scatter = []
risk_for_scatter = []

for (roll_acc_item, idm_item, mkt_count_item) in zip(roll_acc, idm,
                                                     mkt_counters):

    (roll_acc_item, mkt_count_item) = align_to_joint(
        roll_acc_item, mkt_count_item, ffill=(True, True))
    (idm_item, mkt_count_item) = align_to_joint(
        idm_item, mkt_count_item, ffill=(True, True))
    norm_risk = .2 / (roll_acc_item.resample("A").mean(
    ).iloc[:, 0] / idm_item.resample("A").mean().iloc[:, 0])

    roll_acc_item_rs = list(
        roll_acc_item.resample("A").mean().iloc[:, 0].values)
    idm_item_rs = list(idm_item.resample("A").mean().iloc[:, 0].values)
    mktcount_item_rs = list(mkt_count_item.resample("A").mean().values)

    mkt_count_for_scatter = mkt_count_for_scatter + mktcount_item_rs
    roll_acc_for_scatter = roll_acc_for_scatter + roll_acc_item_rs
    idm_for_scatter = idm_for_scatter + idm_item_rs
    risk_for_scatter = risk_for_scatter + list(norm_risk.values)

from matplotlib.pyplot import plot, show, scatter

scatter(mkt_count_for_scatter, idm_for_scatter)
show()

scatter(mkt_count_for_scatter, risk_for_scatter)
show()
