// script.js

/**
 * Fetches reservations from localStorage and displays them on the page.
 */
async function fetchAndDisplayReservations() {
  try {
    // Retrieve reservations data from localStorage
    const reservations = JSON.parse(localStorage.getItem('reservations')) || [];

    // Get the container where reservations will be displayed
    const reservationsContainer = document.getElementById('reservations-container');

    // Clear any existing content in the container
    reservationsContainer.innerHTML = '';

    // Display each reservation
    reservations.forEach(reservation => {
      const reservationElement = document.createElement('div');
      reservationElement.classList.add('reservation-item');
      reservationElement.textContent = `Name: ${reservation.name}, Email: ${reservation.email}, Zeit: ${reservation.time}, Personenzahl: ${reservation.personenZahl}`;
      reservationsContainer.appendChild(reservationElement);
    });
  } catch (error) {
    console.error('Error fetching and displaying reservations:', error);
  }
}

/**
 * Validates the reservation form inputs.
 * @param {Object} formData - The form data to validate.
 * @returns {boolean} - True if valid, false otherwise.
 */
function validateForm(formData) {
  const { name, email, time, personenZahl } = formData;

  // Basic validation checks
  if (!name || !email || !time || personenZahl <= 0) {
    alert('Bitte alle Felder korrekt ausfüllen.');
    return false;
  }

  // Email format validation
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(email)) {
    alert('Bitte eine gültige E-Mail-Adresse eingeben.');
    return false;
  }

  // Time format validation (assuming HH:MM)
  const timePattern = /^([01]?\d|2[0-3]):([0-5]?\d)$/;
  if (!timePattern.test(time)) {
    alert('Bitte eine gültige Zeit im Format HH:MM eingeben.');
    return false;
  }

  return true;
}

/**
 * Handles the form submission.
 * @param {Event} event - The form submit event.
 */
function handleFormSubmit(event) {
  event.preventDefault();

  // Get form elements
  const nameInput = document.getElementById('name');
  const emailInput = document.getElementById('email');
  const timeInput = document.getElementById('time');
  const personenZahlInput = document.getElementById('personenzahl');

  // Collect form data
  const formData = {
    name: nameInput.value.trim(),
    email: emailInput.value.trim(),
    time: timeInput.value,
    personenZahl: parseInt(personenZahlInput.value, 10),
  };

  // Validate form data
  if (!validateForm(formData)) {
    return;
  }

  // Add reservation to localStorage
  const reservations = JSON.parse(localStorage.getItem('reservations')) || [];
  reservations.push(formData);
  localStorage.setItem('reservations', JSON.stringify(reservations));

  // Clear form inputs
  nameInput.value = '';
  emailInput.value = '';
  timeInput.value = '';
  personenZahlInput.value = '';

  // Fetch and display updated reservations
  fetchAndDisplayReservations();
}

// Add event listener to the form
document.addEventListener('DOMContentLoaded', () => {
  const reservationForm = document.getElementById('reservation-form');
  if (reservationForm) {
    reservationForm.addEventListener('submit', handleFormSubmit);
    fetchAndDisplayReservations(); // Fetch and display reservations on page load
  }
});