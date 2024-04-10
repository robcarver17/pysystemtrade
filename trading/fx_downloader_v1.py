import investpy
import pandas as pd
from datetime import datetime, timedelta

# Define the currency pair and date range
currency_pair = 'EUR/USD'
start_date = (datetime.today() - timedelta(days=30)).strftime('%d/%m/%Y')  # starting from 30 days ago
end_date = datetime.today().strftime('%d/%m/%Y')  # until today

try:
    # Fetch hourly forex data
    data = investpy.get_currency_cross_historical_data(currency_pair=currency_pair,
                                                       from_date=start_date,
                                                       to_date=end_date,
                                                       interval='1hour')

    # Reset index to make the 'Date' column available for operations
    data.reset_index(inplace=True)

    # Extract beginning and end dates from the DataFrame
    begin_date = data['Date'].iloc[0]
    end_date = data['Date'].iloc[-1]

    # Save the data to CSV
    data.to_csv(f'{currency_pair.replace("/", "_")}_hourly_data.csv', index=False)

    # Save beginning and end dates to separate CSV files
    pd.DataFrame([begin_date], columns=['BeginDate']).to_csv(f'{currency_pair.replace("/", "_")}_begin_date.csv',
                                                             index=False)
    pd.DataFrame([end_date], columns=['EndDate']).to_csv(f'{currency_pair.replace("/", "_")}_end_date.csv', index=False)

    print(f"Hourly data for {currency_pair} has been saved. Begin Date: {begin_date}, End Date: {end_date}")
except Exception as e:
    print(f"An error occurred: {e}")
