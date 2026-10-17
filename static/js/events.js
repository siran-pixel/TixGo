/**
 * ShowSpot Events & Catalog Interaction JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Quick search filter interaction
    const heroInput = document.getElementById('heroSearchInput');
    if (heroInput) {
        let debounceTimeout = null;
        heroInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                // Client-side quick filter if on page
                const term = e.target.value.toLowerCase().trim();
                const cards = document.querySelectorAll('.event-card');
                if (cards.length > 0) {
                    cards.forEach(card => {
                        const title = card.getAttribute('data-title').toLowerCase();
                        const city = card.getAttribute('data-city').toLowerCase();
                        const cat = card.getAttribute('data-category').toLowerCase();
                        
                        if (title.includes(term) || city.includes(term) || cat.includes(term)) {
                            card.style.display = 'flex';
                        } else {
                            card.style.display = 'none';
                        }
                    });
                }
            }, 250);
        });
    }
});
