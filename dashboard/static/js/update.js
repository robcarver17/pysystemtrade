function update_capital() {
  $.ajax({
    type: "GET",
    url: "/capital",
    success: function(data) {
      $('#capital-tl').html('$'+data['now'].toLocaleString());
      if (data['now'] >= data['yesterday']) {
        $('#capital-tl').addClass('green');
      } else {
        $('#capital-tl').addClass('red');
      }
    }
  }
  );
}

function update_costs() {
  $.ajax({
    type: "GET",
    url: "/costs",
    success: function(data) {
      $.each(data["table_of_SR_costs"], function(instrument, cost) {
        $("#costs_table tbody").append(
          `<tr><td>${instrument}</td><td>${cost["SR_cost"]}</td></tr>`
        );
      });
      $.each(data["combined_df_costs"], function(instrument, vals) {
        $("#costs_detail_table tbody").append(
          `<tr><td>${instrument}</td>
          <td>${vals["% Difference"]}</td>
          <td>${vals["Configured"]}</td>
          <td>${vals["bid_ask_sampled"]}</td>
          <td>${vals["bid_ask_trades"]}</td>
          <td>${vals["estimate"]}</td>
          <td>${vals["total_trades"]}</td>
          <td>${vals["weight_config"]}</td>
          <td>${vals["weight_samples"]}</td>
          <td>${vals["weight_trades"]}</td>
          </tr>`
        );
      });
    }
  });
}

function update_forex() {
  $.ajax({
    type: "GET",
    url: "/forex",
    success: function(data) {
      $.each(data, function(currency, balance) {
        $("#forex_table tbody").append(`<tr><td>${currency}</td><td>${balance}</td></tr>`);
      });
    }
  }
  );
}

function update_liquidity() {
  $.ajax({
    type: "GET",
    url: "/liquidity",
    success: function(data) {
      $.each(data, function(instrument, vals) {
        var contracts = "";
        var risk = "";
        if (vals["contracts"] < 100) {
          contracts = `<td class="red">${vals["contracts"]}</td>`;
        } else {
          contracts = `<td>${vals["contracts"]}</td>`;
        }
        if (vals["risk"] < 1.5) {
          risk = `<td class="red">${vals["risk"].toFixed(1)}</td>`;
        } else {
          risk = `<td>${vals["risk"].toFixed(1)}</td>`;
        }
        $("#liquidity_table tbody").append(
          `<tr><td>${instrument}</td>${contracts}
          ${risk}</tr>`
        );
      });
    }
  }
  );
}

function update_pandl() {
  $.ajax({
    type: "GET",
    url: "/pandl",
    success: function(data) {
      $.each(data, function(k, v) {
      });
    }
  }
  );
}

function update_processes() {
  $.ajax({
    type: "GET",
    url: "/processes",
    success: function(data) {
      if (data['running_modes']['run_stack_handler'] == 'running') {
        $('#stack-tl').addClass("green");
      } else if (data['running_modes']['run_stack_handler'] == 'crashed') {
        $('#stack-tl').addClass("red");
      } else {
        $('#stack-tl').addClass("orange");
      }
      $("#processes_status > tbody").empty();
      $.each(data['running_modes'], function(process, status) {
        if (status == 'crashed') {
        $("#processes_status tbody").append(`
          <tr><td>${process}</td>
          <td class="red">${status}</td>
          </tr>`);
        } else {
          $("#processes_status tbody").append(`
          <tr><td>${process}</td>
          <td>${status}</td>
          </tr>`);
        }
      }
      );
      if (data["prices_update"]) {
        $('#prices-tl').addClass("green");
      } else {
        $('#prices-tl').addClass("red");
      }

    }
  }
  );
}

function update_reconcile() {
  $.ajax({
    type: "GET",
    url: "/reconcile",
    success: function(data) {
      var overall = "green";
      $("#reconcile_strategy > tbody").empty();
      $("#reconcile_contract > tbody").empty();
      $("#reconcile_broker > tbody").empty();
      $.each(data['strategy'], function(contract, details) {
        if (details['break']) {
        $("#reconcile_strategy tbody").append(`
          <tr><td>${contract}</td>
          <td class="red">${details['current']}</td>
          <td class="red">${details['optimal']}</td>
          </tr>`);
          overall = "orange";
        } else {
        $("#reconcile_strategy tbody").append(`
          <tr><td>${contract}</td>
          <td>${details['current']}</td>
          <td>${details['optimal']}</td>
          </tr>`);
        }
      }
      );
      $.each(data['positions'], function(contract, details) {
        var line = `<tr><td>${details['code']}</td>
          <td>${details['contract_date']}</td>`;
        if (details['code'] in data['db_breaks']) {
          line += `<td class="red">${details['db_position']}</td>`;
          overall = "red";
        } else {
          line += `<td>${details['db_position']}</td>`;
        }
        if (details['code'] in data['ib_breaks']) {
          line += `<td class="red">${details['ib_position']}</td>`;
          overall = "red";
        } else {
          line += `<td>${details['ib_position']}</td>`;
        }
        $("#reconcile_contract tbody").append(line);
      }
      );
      $('#breaks-tl').addClass(overall);
      if (data['gateway_ok']) {
        $('#gateway-tl').addClass("green");
      } else {
        $('#gateway-tl').addClass("red");
      }
    }
  }
  );
}

function update_risk() {
  $.ajax({
    type: "GET",
    url: "/risk",
    success: function(data) {
      $.each(data, function(k, v) {
      });
    }
  }
  );
}

function update_rolls() {
  $.ajax({
    type: "GET",
    url: "/rolls",
    success: function(data) {
      $("#rolls_status > tbody").empty();
      $("#rolls_details > tbody").empty();
      var overall = "green";
      $.each(data, function(contract, details) {
        var buttons = "";
        $.each(details['allowable'], function(_, option) {
          buttons += `<button onClick="roll_post('${contract}', '${option}')">${option}</button>`
        });
        $("#rolls_status tbody").append(`
          <tr id="rolls_${contract}"><td>${contract}</td>
          <td>${details['status']}</td>
          <td>${details['roll_expiry']}</td>
          <td>${details['carry_expiry']}</td>
          <td>${details['price_expiry']}</td>
          <td>${buttons}</td>
          </tr>`);
        if (details['roll_expiry'] < 0) {
          overall = "red";
        } else if (details['roll_expiry'] < 5 && overall != "red") {
          overall = "orange";
        }
        var row_data = "";
        $.each(details['contract_labels'], function(i, entry) {
          row_data +=`
            <td>${details['contract_labels'][i]}<br>
            ${details['positions'][i]}<br>
            ${details['volumes'][i].toFixed(3)}<br></td>
            `;
        }
        );
        $("#rolls_details tbody").append(`
          <tr><td>${contract}</td>${row_data}</tr>`
        );
      }
      );
      $("#rolls-tl").addClass(overall);
    }
  });
}

function update_strategy() {
  $.ajax({
    type: "GET",
    url: "/strategy",
    success: function(data) {
      $.each(data, function(k, v) {
      });
    }
  }
  );
}

function update_trades() {
  $.ajax({
    type: "GET",
    url: "/trades",
    success: function(data) {
      $.each(data, function(k, v) {
      });
    }
  }
  );
}

function roll_post(instrument, state, confirmed = false) {
  $.ajax({
    type: "POST",
    url: "/rolls",
    data: {'instrument': instrument, 'state': state, 'confirmed': confirmed},
    success: function(data)
    {
      $("#roll_prices").addClass("hidden");
      if (data["new_state"] == "Roll_Adjusted") {
        // Lots has changed so refresh everything
        update_rolls();
      } else if (data["single"]){
        // Populate the div to show the new prices
        $("#roll_prices").removeClass("hidden");
        $("#roll_instrument_name").text("Proposed Adjusted Prices - " + instrument);
        $.each(data['single'], function(date, val) {
          current = val['current'] ? val['current'] : "";
          $("#roll_prices_single tbody").append(`
            <tr>
            <td>${date}</td>
            <td>${current}</td>
            <td>${val['new']}</td>
            </tr>`);
        });
        $.each(data['multiple'], function(date, val) {
          current = val['current'] ? val['current'] : {'CARRY': '', 'PRICE': '', 'FORWARD': ''};
          $("#roll_prices_multiple tbody").append(`
            <tr>
            <td>${date}</td>
            <td>${val['new']['CARRY_CONTRACT']}</td>
            <td>${current['CARRY']}</td>
            <td>${val['new']['CARRY']}</td>
            <td>${val['new']['PRICE_CONTRACT']}</td>
            <td>${current['PRICE']}</td>
            <td>${val['new']['PRICE']}</td>
            <td>${val['new']['FORWARD_CONTRACT']}</td>
            <td>${current['FORWARD']}</td>
            <td>${val['new']['FORWARD']}</td>
            </tr>`);
        });
        $("#roll_prices").append(`<button onClick="roll_post('${instrument}', '${state}', true)">${state}</button>`);
        $("#roll_prices").display = true;
      } else if (data["allowable"]) {
        // Only need to update this line
        var buttons = "";
        $.each(data['allowable'], function(_, option) {
          buttons += `<button onClick="roll_post('${instrument}', '${option}')">${option}</button>`
        });
        $("#rolls_" + instrument).find("td:eq(1)").html(data["new_state"]);
        $("#rolls_" + instrument).find("td:eq(5)").html(buttons);
      }
    }
  });
}

$(document).ready(update_capital());
$(document).ready(update_forex());
$(document).ready(update_pandl());
$(document).ready(update_processes());
$(document).ready(update_reconcile());
$(document).ready(update_risk());
$(document).ready(update_strategy());
$(document).ready(update_trades());
$(document).ready(update_rolls());
$(document).ready(update_liquidity());
$(document).ready(update_costs());

