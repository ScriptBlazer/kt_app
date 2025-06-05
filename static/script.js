// Define and export checkMobileView globally
function checkMobileView(containerId) {
  const contentContainer = document.getElementById(containerId);
  const mobileWarning = document.getElementById("mobile-warning");

  function toggleMobileWarning() {
    if (window.innerWidth < 600) {
      // Mobile view threshold
      contentContainer.style.display = "none";
      mobileWarning.style.display = "block";
    } else {
      contentContainer.style.display = "block";
      mobileWarning.style.display = "none";
    }
  }

  // Initial check on load and resize event
  toggleMobileWarning();
  window.addEventListener("resize", toggleMobileWarning);
}

// Expose checkMobileView function for HTML files
window.checkMobileView = checkMobileView;

document.addEventListener("DOMContentLoaded", () => {
  console.log("Page fully loaded");
  console.log("Donut");

  // Time input formatting
  const timeInputs = document.querySelectorAll(
    '[name="job_time"], [name="expense_time"]'
  );

  timeInputs.forEach((input) => {
    input.addEventListener("input", (e) => {
      const value = e.target.value.replace(/\D/g, "").slice(0, 4);
      e.target.value =
        value.length > 2 ? `${value.slice(0, 2)}:${value.slice(2)}` : value;
    });
  });

  // Disable scroll on all number inputs globally
  document
    .querySelectorAll(
      'input[type="number"], #payment-section input[name$="payment_amount"]'
    )
    .forEach((input) => {
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

  // Helper function to set the cursor position, only for supported input types
  function setCaretPosition(elem, pos) {
    if (
      elem.type === "text" ||
      elem.type === "search" ||
      elem.type === "url" ||
      elem.type === "tel" ||
      elem.type === "password"
    ) {
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
  }

  // Handle input for fields that allow commas and dots
  decimalFieldsWithCommaAndDot.forEach((input) => {
    input.addEventListener("input", (e) => {
      let original = input.value;
      let position = input.selectionStart;

      // Replace commas with dots
      let cleaned = original.replace(",", ".");

      // Remove invalid characters (only digits and dots)
      cleaned = cleaned.replace(/[^0-9.]/g, "");

      // Allow only one dot
      const parts = cleaned.split(".");
      if (parts.length > 2) {
        cleaned = parts[0] + "." + parts[1];
      }

      // Only update the value if it has changed
      if (cleaned !== original) {
        input.value = cleaned;

        // Adjust the caret to the right position
        let diff = original.length - cleaned.length;
        let newPos = position - diff;
        setCaretPosition(input, Math.max(0, newPos));
      }
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

  // Select all toggle headers
  const toggleHeaders = document.querySelectorAll(".toggle-header");

  // Add event listeners to each header
  toggleHeaders.forEach((header) => {
    const sectionId = header.getAttribute("data-section-id");

    // Check if sectionId exists to avoid errors
    if (sectionId) {
      header.addEventListener("click", () => {
        toggleSection(sectionId);
      });
    }
  });

  // Toggle Section Function
  window.toggleSection = function (sectionId) {
    const section = document.getElementById(sectionId);
    const arrow = document.getElementById(sectionId + "-arrow");

    if (!arrow) {
      console.error("Arrow element not found for section: ", sectionId);
      return;
    }

    const currentDisplay = window.getComputedStyle(section).display;

    if (currentDisplay === "none") {
      section.style.display = "block";
      arrow.textContent = "▲";
    } else {
      section.style.display = "none";
      arrow.textContent = "▼";
    }
  };

  // Function to display the modal
  function showModal(errorMessage) {
    const modal = document.getElementById("error-modal");
    const modalMessage = document.getElementById("modal-message");
    modalMessage.textContent = errorMessage;
    modal.style.display = "flex";
  }

  // Function to close the modal, now attached to the global window object
  function closeModal() {
    const modal = document.getElementById("error-modal");
    if (modal) {
      modal.style.display = "none";
    }
  }
  window.closeModal = closeModal; // Attach to window for global access

  // Attach event listener to the close button
  const closeButton = document.querySelector(".close-button");
  if (closeButton) {
    closeButton.addEventListener("click", closeModal);
  }

  // Check if the error message exists and show the modal
  const modalTrigger = document.getElementById("modal-trigger");
  if (modalTrigger) {
    const errorMessage = modalTrigger.textContent.trim();
    if (errorMessage) {
      showModal(errorMessage);
    }
  }

  // Example function for job-related form validation
  function validateJobCompletion() {
    const isCompletedChecked = document.getElementById("is_completed").checked;
    const paidTo = document.getElementById("paid_to").value;
    const paymentType = document.querySelector(
      'select[name="payment_type"]'
    ).value;

    if (isCompletedChecked && (paidTo === "Select an option" || !paymentType)) {
      alert(
        'Please set "Paid to" and "Payment Type" before completing the job.'
      );
      return false; // Prevent form submission
    }
    return true; // Allow form submission
  }

  // Attach form validation for job forms
  document.querySelectorAll("form.job-form").forEach((form) => {
    form.addEventListener("submit", function (event) {
      if (!validateJobCompletion()) {
        event.preventDefault(); // Prevent form submission if validation fails
      }
    });
  });
});
