from ib_insync import IB, Forex, util
import pandas as pd

# Connection parameters
host = '127.0.0.1'  # The default IP for TWS or IB Gateway
port = 4001  # The default port number. For IB Gateway, it might be 4001.
clientId = 1  # Client ID, ensure it's unique if running multiple sessions

# Forex symbol and duration
currency_pair = 'EURUSD'  # Example currency pair
duration = '365 D'  # Duration of historical data, "2 D" for 2 days as an example
barSize = '1 hour'  # 1-hour bars

# Initialize IB and connect
ib = IB()
ib.connect(host, port, clientId)

# Define the Forex contract
forex_contract = Forex(currency_pair)

# Request historical data
bars = ib.reqHistoricalData(
    forex_contract,
    endDateTime='',
    durationStr=duration,
    barSizeSetting=barSize,
    whatToShow='MIDPOINT',
    useRTH=True,
    formatDate=1
)

# Convert to DataFrame
df = util.df(bars)

# If needed, adjust the timezone
# df['date'] = df['date'].dt.tz_localize('UTC').dt.tz_convert('YourTimezone') # Replace 'YourTimezone' with your timezone, e.g., 'America/New_York'

# Extract beginning and end dates
begin_date = df['date'].iloc[0]
end_date = df['date'].iloc[-1]

# Save to CSV
df.to_csv(f'{currency_pair}_hourly_data.csv', index=False)

# Save beginning and end dates to separate CSV files
pd.DataFrame([begin_date], columns=['BeginDate']).to_csv(f'{currency_pair}_begin_date.csv', index=False)
pd.DataFrame([end_date], columns=['EndDate']).to_csv(f'{currency_pair}_end_date.csv', index=False)

# Disconnect
ib.disconnect()

print(f'Hourly data for {currency_pair} saved. Begin Date: {begin_date}, End Date: {end_date}')
