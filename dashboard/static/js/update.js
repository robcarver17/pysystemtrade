$(document).ready(function(){
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
);

$(document).ready(function(){
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
);

$(document).ready(function(){
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
);

$(document).ready(function(){
  $.ajax({
    type: "GET",
    url: "/rolls",
    success: function(data) {
      $("#rolls_status > tbody").empty();
      $("#rolls_details > tbody").empty();
      var overall = "green";
      $.each(data, function(contract, details) {
        $("#rolls_status tbody").append(`
          <tr><td>${contract}</td>
          <td>${details['status']}</td>
          <td>${details['roll_expiry']}</td>
          <td>${details['carry_expiry']}</td>
          <td>${details['price_expiry']}</td>
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
});

