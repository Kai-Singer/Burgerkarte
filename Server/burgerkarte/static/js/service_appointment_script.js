document.querySelectorAll('.appointment.booked').forEach(element => {
  element.addEventListener('click', function (event) {
    if (event.target.closest('.button')) return;
    const details = this.querySelector('.appointment_details');
    details.classList.toggle('hidden');
  });
});