from systems.accounts.account_forecast import accountForecast
from systems.accounts.account_subsystem import accountSubsystem

class accountsStage(accountForecast, accountSubsystem):

    @property
    def name(self):
        return "accounts"
