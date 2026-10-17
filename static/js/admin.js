/**
 * ShowSpot Admin Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const adminSidebar = document.getElementById('adminSidebar');

    if (sidebarToggle && adminSidebar) {
        sidebarToggle.addEventListener('click', () => {
            adminSidebar.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!adminSidebar.contains(e.target) && !sidebarToggle.contains(e.target) && window.innerWidth <= 992) {
                adminSidebar.classList.remove('show');
            }
        });
    }
});
