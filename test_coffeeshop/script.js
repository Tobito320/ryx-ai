// script.js

/**
 * Handles form submission and localStorage operations for a coffee shop reservation system.
 */

// Select DOM elements
const reservationForm = document.getElementById('reservation-form');
const reservationsList = document.getElementById('reservations-list');

// Load existing reservations from localStorage on page load
document.addEventListener('DOMContentLoaded', () => {
  renderReservations();
});

/**
 * Handles the submission of the reservation form.
 * @param {Event} event - The form submission event.
 */
function handleFormSubmit(event) {
  event.preventDefault();

  // Collect form data
  const formData = new FormData(reservationForm);
  const reservationData = {};

  for (const [key, value] of formData.entries()) {
    reservationData[key] = value;
  }

  // Validate the number of people
  if (!reservationData.people || isNaN(reservationData.people) || reservationData.people <= 0) {
    alert('Please enter a valid number of people.');
    return;
  }

  // Save reservation to localStorage
  saveReservation(reservationData);

  // Clear form and render reservations
  reservationForm.reset();
  renderReservations();
}

/**
 * Saves a reservation to localStorage.
 * @param {Object} reservation - The reservation data.
 */
function saveReservation(reservation) {
  let reservations = JSON.parse(localStorage.getItem('reservations')) || [];
  reservations.push(reservation);
  localStorage.setItem('reservations', JSON.stringify(reservations));
}

/**
 * Renders all reservations from localStorage on the page.
 */
function renderReservations() {
  const reservations = JSON.parse(localStorage.getItem('reservations')) || [];

  // Clear existing reservations
  reservationsList.innerHTML = '';

  // Render each reservation
  reservations.forEach((reservation, index) => {
    const reservationElement = document.createElement('div');
    reservationElement.classList.add('reservation-item');
    reservationElement.innerHTML = `
      <p><strong>Name:</strong> ${reservation.name}</p>
      <p><strong>Date:</strong> ${reservation.date}</p>
      <p><strong>Time:</strong> ${reservation.time}</p>
      <p><strong>People:</strong> ${reservation.people}</p>
    `;
    reservationsList.appendChild(reservationElement);
  });
}

// Add event listener to the reservation form
reservationForm.addEventListener('submit', handleFormSubmit);