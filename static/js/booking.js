/**
 * ShowSpot Attendee & Booking Flow JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    const attendeesForm = document.getElementById('attendeesForm');
    if (attendeesForm) {
        attendeesForm.addEventListener('submit', (e) => {
            const submitBtn = document.getElementById('submitAttendeesBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validating Attendees...';
            }
        });
    }
});
