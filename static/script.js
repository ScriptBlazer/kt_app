document.addEventListener("DOMContentLoaded", () => {
  console.log("Page fully loaded");
  console.log("Donut");

  // Time input formatting
  const timeInput = document.querySelector('[name="job_time"]');
  if (timeInput) {
    timeInput.addEventListener("input", (e) => {
      const value = e.target.value.replace(/\D/g, "").slice(0, 4);
      e.target.value =
        value.length > 2 ? `${value.slice(0, 2)}:${value.slice(2)}` : value;
    });
  }

  // Disable scroll on number inputs
  document.querySelectorAll('input[type="number"]').forEach((input) => {
    input.addEventListener("focus", () =>
      input.addEventListener("wheel", preventScroll)
    );
    input.addEventListener("blur", () =>
      input.removeEventListener("wheel", preventScroll)
    );
  });

  function preventScroll(event) {
    event.preventDefault();
  }

  // Initialize decimal fields
  const decimalFieldsWithCommaAndDot = document.querySelectorAll(
    '[name="job_price"], [name="fuel_cost"], [name="driver_fee"]'
  );

  const decimalFieldsWithDotOnly = document.querySelectorAll(
    '[name="kilometers"], [name="no_of_passengers"]'
  );

  // Helper function to set the cursor position
  function setCaretPosition(elem, pos) {
    if (elem.setSelectionRange) {
      elem.focus();
      elem.setSelectionRange(pos, pos);
    } else if (elem.createTextRange) {
      var range = elem.createTextRange();
      range.collapse(true);
      range.moveEnd("character", pos);
      range.moveStart("character", pos);
      range.select();
    }
  }

  // Handle input for fields that allow commas and dots
  decimalFieldsWithCommaAndDot.forEach((input) => {
    input.addEventListener("input", (e) => {
      let caretPosition = input.selectionStart; // Save the cursor position

      console.log(`Input detected in ${input.name}:`, e.target.value);

      // Allow numbers, commas, and dots only
      let oldValue = e.target.value;
      e.target.value = e.target.value.replace(/[^0-9.,]/g, "");

      // Replace multiple commas or dots, only allow one decimal separator
      const valueWithSingleCommaOrDot = e.target.value.replace(
        /[,.]/g,
        (match, index, fullString) => {
          // Only allow one decimal separator (either dot or comma), and convert comma to dot for standardization
          if (
            fullString.indexOf(".") === index ||
            fullString.indexOf(",") === index
          ) {
            return fullString.indexOf(".") === index ? "." : ".";
          }
          return "";
        }
      );

      e.target.value = valueWithSingleCommaOrDot;

      // Restore the cursor position if no drastic change occurred
      if (oldValue.length >= e.target.value.length) {
        setCaretPosition(input, caretPosition); // Restore the cursor position
      }

      console.log(`Validated input for ${input.name}:`, e.target.value);
    });
  });

  // Handle input for fields that allow only dots
  decimalFieldsWithDotOnly.forEach((input) => {
    input.addEventListener("input", (e) => {
      let caretPosition = input.selectionStart; // Save the cursor position

      console.log(`Input detected in ${input.name}:`, e.target.value);

      // Replace any invalid characters (anything other than numbers and a decimal point)
      let oldValue = e.target.value;
      e.target.value = e.target.value.replace(/[^0-9.]/g, "");

      // Ensure there is only one decimal point allowed
      const parts = e.target.value.split(".");
      if (parts.length > 2) {
        e.target.value = parts[0] + "." + parts[1]; // Keep only the first decimal part
      }

      // Restore the cursor position if no drastic change occurred
      if (oldValue.length >= e.target.value.length) {
        setCaretPosition(input, caretPosition); // Restore the cursor position
      }

      console.log(`Validated input for ${input.name}:`, e.target.value);
    });
  });

  // Chart Data for all pie charts
  console.log("Checking for chartData...");
  console.log(window.chartData);

  if (window.chartData) {
    if (window.chartData.monthly_fuel_cost !== undefined) {
      console.log("Rendering monthly chart...");
      renderPieChart(
        "monthlyChart",
        "Monthly Totals",
        parseFloat(window.chartData.monthly_fuel_cost),
        parseFloat(window.chartData.monthly_total_agent_fees),
        parseFloat(window.chartData.monthly_total_driver_fees),
        parseFloat(window.chartData.monthly_total_profit)
      );
    }
    if (window.chartData.yearly_fuel_cost !== undefined) {
      console.log("Rendering yearly chart...");
      renderPieChart(
        "yearlyChart",
        "Yearly Totals",
        parseFloat(window.chartData.yearly_fuel_cost),
        parseFloat(window.chartData.yearly_total_agent_fees),
        parseFloat(window.chartData.yearly_total_driver_fees),
        parseFloat(window.chartData.yearly_total_profit)
      );
    }
    if (window.chartData.overall_fuel_cost !== undefined) {
      console.log("Rendering overall chart...");
      renderPieChart(
        "overallChart",
        "Overall Totals",
        parseFloat(window.chartData.overall_fuel_cost),
        parseFloat(window.chartData.overall_total_agent_fees),
        parseFloat(window.chartData.overall_total_driver_fees),
        parseFloat(window.chartData.overall_total_profit)
      );
    }
  }
});

function renderPieChart(
  chartId,
  title,
  fuelCost,
  agentFees,
  driverFees,
  profit
) {
  const ctx = document.getElementById(chartId);
  if (!ctx) {
    console.error(`Canvas element with id "${chartId}" not found.`);
    return;
  }
  console.log(`Rendering chart ${chartId} with data:`, {
    title,
    fuelCost,
    agentFees,
    driverFees,
    profit,
  });
  new Chart(ctx.getContext("2d"), {
    type: "pie",
    data: {
      labels: ["Fuel Cost", "Agent Fees", "Driver Fees", "Profit"],
      datasets: [
        {
          label: title,
          data: [fuelCost, agentFees, driverFees, profit],
          backgroundColor: [
            "rgba(255, 99, 132, 0.8)",
            "rgba(54, 162, 235, 0.8)",
            "rgba(255, 206, 86, 0.8)",
            "rgba(75, 192, 192, 0.8)",
          ],
          borderColor: [
            "rgba(255, 99, 132, 1)",
            "rgba(54, 162, 235, 1)",
            "rgba(255, 206, 86, 1)",
            "rgba(75, 192, 192, 1)",
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}
