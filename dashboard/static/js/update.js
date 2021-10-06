$(document).ready(function(){
  $.ajax({
    type: "GET",
    url: "/strategy",
    success: function(data) {
      $('#breaks-tl').addClass(data['overall']);
      $("#strategy_strategy > tbody").empty();
      $("#strategy_contract > tbody").empty();
      $("#strategy_broker > tbody").empty();
      $.each(data['strategy'], function(contract, details) {
        if (details['break']) {
        $("#strategy_strategy tbody").append(`
          <tr><td>${contract}</td>
          <td class="red">${details['current']}</td>
          <td class="red">${details['optimal']}</td>
          </tr>`);
        } else {
        $("#strategy_strategy tbody").append(`
          <tr><td>${contract}</td>
          <td>${details['current']}</td>
          <td>${details['optimal']}</td>
          </tr>`);
        }
      }
      );
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
        $('#capital-tl').addClass('green');
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

