## Generate expected spread from actual trades, and sampled spreads
import datetime
from sysdata.data_blob import dataBlob

from syscore.constants import arg_not_supplied
from sysproduction.reporting.reporting_functions import body_text
from sysproduction.reporting.api import reportingApi

SLIPPAGE_REPORT_TEXT = body_text(
    "Slippage calculations: First three columns are slippage (mid to executed price) from 3 sources:\n"
    + "- bid_ask_trades: The difference between the mid price and bid/ask price when a trade is entered\n"
    + "- total_trades: The difference between the mid price and actual fill price when a trade occurs\n"
    + "- bid_ask_sampled: The difference between mid and bid/ask when a regular sample is taken, not when trading\n"
    + "\nThe following three columns show how our estimate of slippage is calculated using weights\n"
    + "- weight_trades: Weighting given to trades (most conservative of bid_ask_trades and total_trades)\n"
    + "- weight_samples: Weighting given to samples\n"
    + "- weight_config: Weighting given to current configured value\n"
    + "\nThe weights vary depending on how many trades and samples we have\n"
    + "\nFinally we have:\n"
    + "- The estimate based on the calculations above\n"
    + "- The current configured value\n"
    + "- The % difference between these values (estimate and configured). Positive means the estimate is higher (costs not conservative enough)"
)


def slippage_report(
    data: dataBlob = arg_not_supplied,
    calendar_days_back: int = 250,
    end_date: datetime.datetime = arg_not_supplied,
    start_date: datetime.datetime = arg_not_supplied,
):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data,
        start_date=start_date,
        end_date=end_date,
        calendar_days_back=calendar_days_back,
    )

    formatted_output = []

    formatted_output.append(reporting_api.std_header("Slippage report"))
    formatted_output.append(SLIPPAGE_REPORT_TEXT)
    formatted_output.append(reporting_api.table_of_slippage_comparison())
    formatted_output.append(body_text("* indicates currently held position"))
    formatted_output.append(reporting_api.table_of_slippage_comparison_tick_adjusted())
    formatted_output.append(body_text("* indicates currently held position"))
    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == "__main__":
    slippage_report()
