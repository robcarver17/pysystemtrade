from sysdata.config.configdata import Config
from systems.provided.futures_chapter15.basesystem import futures_system
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import seaborn.objects as so
import fire 

class FuturesSystemCLI:
    def run_and_pickle(self, destination = "private.Tests.testing.pck", yaml = "command_line.Tests.private_config24.yaml"):
        """Runs the futures system and pickles it.
        :param destination (str): The relative path where the file will be saved. 
        :param yaml (str): The yaml file that will be used to configure the futures system.
        """
        my_config=Config(yaml)
        system=futures_system(config=my_config)
        system.cache.pickle(destination)
    
    def run_and_save_to_csv(self, destination = "data.csv", yaml = "command_line.Tests.private_config24.yaml" ):
        """Runs the futures system and saves specific data to a csv.
        :param destination (str): The relative path where the file will be saved. 
        :param yaml (str): The yaml file that will be used to configure the futures system.
        """
        #TODO: Update this to take specified trading rules as an argument and validate it against the yaml config file.
        my_config=Config(yaml)
        system=futures_system(config=my_config)
        # create a dataframe with all of the stategies that we care about.
        df_accel16 = system.accounts.pandl_for_trading_rule("accel16")
        df_accel32 = system.accounts.pandl_for_trading_rule("accel32")
        df_accel64 = system.accounts.pandl_for_trading_rule("accel64")

        concat_accel_df = pd.concat([df_accel16, df_accel32, df_accel64], axis=1)

        concat_accel_df.to_csv(destination)
        

    def from_pickle(self, location = "command_line.Tests.testing.pck"):
        """Unpickes the futrues system and runs specified functionalities.
        :param location (str): The relative path to where the pickeled system is located.
        """
        system = futures_system(log_level="off")
        system.cache.unpickle(location)

    def from_csv(self, location = "data.csv" ):
        """Reads the data in the specified csv and graphs it. TODO: Make graphing an argument.
        :param location (str): The relative path to where the csv is located.
        """
        df = pd.read_csv(location)

        df = df.rename(columns={"index": "date", '0': "accel16", '1': "accel32", '2': "accel64"})
        df["accel_sum"] =  df.sum(axis=1)
        # Put dates in the correct format.
        df['date'] = pd.to_datetime(df['date'])


        for col in df.columns:
            if col == "date":
                continue
            # Set up the figure and axes.
            fig, ax = plt.subplots(figsize=(12, 10))
            sns.lineplot(data=df, x='date', y=col, ax=ax)
            ax.xaxis.set_major_locator(plt.MaxNLocator(7))
            plt.xticks(rotation=25)
            ax.set_xlabel('Date')
            ax.set_ylabel('Value')
            ax.set_title(col)

            plt.savefig("graphs/"+ col)

if __name__ == '__main__':
    fire.Fire(FuturesSystemCLI)

