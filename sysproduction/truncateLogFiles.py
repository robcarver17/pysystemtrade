from syslogdiag.log import accessLogFromMongodb


def truncate_log_files():
    mlog = accessLogFromMongodb()
    mlog.delete_log_items_from_before_n_days(days=365)

