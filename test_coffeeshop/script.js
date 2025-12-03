// Import statements if needed
// import { someFunction } from './someModule';

/**
 * Function to handle form submission and save reservation data to localStorage.
 */
function handleFormSubmit(event) {
  event.preventDefault();
  const form = document.getElementById('reservationForm');
  const formData = new FormData(form);
  const reservationData = {};

  for (const [key, value] of formData.entries()) {
    reservationData[key] = value;
  }

  // Save reservation data to localStorage
  localStorage.setItem('reservation', JSON.stringify(reservationData));
  alert('Reservation saved successfully!');
}

/**
 * Function to load and display reservation data from localStorage.
 */
function loadReservation() {
  const reservationData = localStorage.getItem('reservation');
  if (reservationData) {
    const form = document.getElementById('reservationForm');
    const parsedData = JSON.parse(reservationData);

    for (const [key, value] of Object.entries(parsedData)) {
      const inputField = form.querySelector(`[name="${key}"]`);
      if (inputField) {
        inputField.value = value;
      }
    }
  }
}

/**
 * Main function to initialize the script.
 */
function init() {
  const reservationForm = document.getElementById('reservationForm');
  if (reservationForm) {
    reservationForm.addEventListener('submit', handleFormSubmit);
    loadReservation();
  } else {
    console.error('Element with id "reservationForm" not found.');
  }
}

// Initialize the script
document.addEventListener('DOMContentLoaded', init);