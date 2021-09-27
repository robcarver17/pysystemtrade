$(document).ready(function(){
  $.ajax({
    type: "GET",
    url: "/rolls",
    success: function(data) {
      $.each(data, function(contract, details) {
        $("#rolls_status tbody").append(`
          <tr><td>${contract}</td>
          <td>${details['status']}</td>
          <td>${details['roll_expiry']}</td>
          <td>${details['carry_expiry']}</td>
          <td>${details['price_expiry']}</td>
          </tr>`);
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
    }
  });
});

