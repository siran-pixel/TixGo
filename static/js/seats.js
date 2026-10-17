function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

class SeatMapEngine {
    constructor() {
        this.pageEl = document.querySelector('.seat-booking-page');
        if (!this.pageEl) return;

        this.eventId = parseInt(this.pageEl.dataset.eventId);
        this.eventType = this.pageEl.dataset.eventType;
        this.maxTickets = parseInt(this.pageEl.dataset.maxTickets || 10);
        this.lockDuration = parseInt(this.pageEl.dataset.lockDuration || 300);

        this.seatsData = [];
        this.sections = [];
        this.selectedSeats = new Map(); // seatId -> seatObj
        this.activeStand = 'Stand A';
        this.activeTier = 'all';
        this.show360Map = true;

        this.lockCountdownInterval = null;
        this.pollingInterval = null;

        // Zoom engine configuration
        this.currentZoom = 1.0;
        this.minZoom = 0.5;
        this.maxZoom = 2.0;
        this.zoomStep = 0.15;

        window.seatMapEngineInstance = this;

        this.init();
    }

    async init() {
        this.setupZoomEventListeners();
        this.applyZoom();
        if (this.eventType === 'Cricket') {
            const cardsContainer = document.getElementById('standCardsContainer');
            if (cardsContainer) {
                this.renderCricketSplitFormat(cardsContainer);
            }
        }
        await this.loadSeats();
        this.startStatusPolling();
    }

    async loadSeats() {
        const viewport = document.getElementById('seatGridViewport');
        try {
            const response = await fetch(`/api/events/${this.eventId}/seats`);
            const data = await response.json();

            if (data.success) {
                this.seatsData = data.seats;
                this.sections = data.sections || [];
                this.renderSeatMap();

                // Restore any pre-existing session locks
                this.seatsData.filter(s => s.is_my_lock).forEach(s => {
                    this.selectedSeats.set(s.id, s);
                });

                if (this.selectedSeats.size > 0) {
                    const firstLock = Array.from(this.selectedSeats.values())[0];
                    this.startLockCountdown(firstLock.seconds_remaining || this.lockDuration);
                }

                this.updateSummaryUI();
            } else {
                if (viewport) {
                    viewport.innerHTML = `<div class="seat-loading-state"><p class="text-danger">${data.message || 'Failed to load seats.'}</p></div>`;
                }
            }
        } catch (err) {
            console.error('Error loading seats:', err);
            if (viewport) {
                viewport.innerHTML = `<div class="seat-loading-state"><p class="text-danger">Network error loading seat layout.</p></div>`;
            }
        }
    }

    renderSeatMap() {
        const viewport = document.getElementById('seatGridViewport');
        if (viewport) {
            viewport.innerHTML = '';
        }

        if (this.eventType === 'Cricket') {
            this.renderCricketLayout(viewport);
        } else if (this.eventType === 'Cinema' || this.eventType === 'Theater') {
            if (viewport) this.renderCinemaLayout(viewport);
        } else if (this.eventType === 'Concert') {
            if (viewport) this.renderConcertLayout(viewport);
        } else {
            if (viewport) this.renderGeneralLayout(viewport);
        }
    }

    // Group helper
    groupSeatsBySectionAndRow(seats) {
        const sections = {};
        seats.forEach(seat => {
            if (!sections[seat.section]) sections[seat.section] = {};

            let rowKey = seat.row_label;
            if (!rowKey) {
                if (seat.seat_number.includes('-')) {
                    const parts = seat.seat_number.split('-');
                    if (parts.length >= 3) {
                        // Cricket stadium (e.g. A-L1-01 -> stand-row-seat)
                        rowKey = parts[1];
                    } else if (parts[0].toUpperCase() === 'ELITE' || parts[0].toUpperCase() === 'VIP') {
                        // Elite / VIP section: group into horizontal rows of 10 seats (E1 to E5)
                        const seatNum = parseInt(parts[1], 10) || 1;
                        const rowIdx = Math.ceil(seatNum / 10);
                        rowKey = `E${rowIdx}`;
                    } else if (/^[A-Z]+\d+$/i.test(parts[0])) {
                        // Concert Gold (e.g. G1-5) or Silver (e.g. S1-10) -> parts[0] is the row identifier ('G1', 'S1')
                        rowKey = parts[0];
                    } else {
                        rowKey = parts[0];
                    }
                } else {
                    // e.g. Cinema / Theater / General: A1 -> row 'A'
                    rowKey = seat.seat_number.replace(/[0-9]/g, '') || 'R';
                }
            }

            if (!sections[seat.section][rowKey]) sections[seat.section][rowKey] = [];
            sections[seat.section][rowKey].push(seat);
        });
        return sections;
    }

    // Cinema Layout Rendering
    renderCinemaLayout(container) {
        const sections = this.groupSeatsBySectionAndRow(this.seatsData);

        // Position Standard seats first (closer to screen), then Balcony seats (rear/elevated)
        const preferredSectionOrder = ['Standard', 'Balcony'];
        const orderedSectionNames = Object.keys(sections).sort((a, b) => {
            let indexA = preferredSectionOrder.findIndex(name => a.toLowerCase().includes(name.toLowerCase()));
            let indexB = preferredSectionOrder.findIndex(name => b.toLowerCase().includes(name.toLowerCase()));
            if (indexA === -1) indexA = 99;
            if (indexB === -1) indexB = 99;
            return indexA - indexB;
        });

        for (const sectionName of orderedSectionNames) {
            const rows = sections[sectionName];
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'seat-section-block';

            const firstSeat = Object.values(rows)[0][0];
            sectionDiv.innerHTML = `<h4 class="section-block-title">${sectionName.toUpperCase()} &bull; ₹${firstSeat.price}</h4>`;

            for (const [rowLabel, rowSeats] of Object.entries(rows)) {
                const rowDiv = document.createElement('div');
                rowDiv.className = 'seat-row';

                const labelSpan = document.createElement('span');
                labelSpan.className = 'row-label';
                labelSpan.textContent = rowLabel;
                rowDiv.appendChild(labelSpan);

                rowSeats.forEach(seat => {
                    const seatEl = this.createSeatElement(seat);
                    rowDiv.appendChild(seatEl);
                });

                sectionDiv.appendChild(rowDiv);
            }
            container.appendChild(sectionDiv);
        }
    }

    // Cricket Stadium Layout Rendering (Circular Stadium Map + Right-Side Ticket Listing Cards)
    renderCricketLayout(container) {
        const cardsContainer = document.getElementById('standCardsContainer');
        if (cardsContainer) {
            this.renderCricketSplitFormat(cardsContainer);
            return;
        }

        // Fallback for non-split container
        if (container) {
            container.innerHTML = '<div class="seat-loading-state"><p>Loading Cricket Stadium Layout...</p></div>';
        }
    }

    renderCricketSplitFormat(cardsContainer) {
        this.cricketSvgZoom = 1.0;
        this.cricketQty = parseInt(document.getElementById('cricketQtyDropdown')?.value || 2);
        window.cricketEngine = {
            zoomIn: () => this.cricketZoomIn(),
            zoomOut: () => this.cricketZoomOut(),
        };

        // Configuration matching user screenshot
        this.cricketStandConfigs = [
            {
                name: "H Upper",
                sectorSelector: ".sector-h-upper",
                row: "Row G",
                price: 4338,
                rating: "7.8 Great",
                features: ["tickets_together", "Clear view", "Resale not allowed"],
                tag: { text: "Best price", type: "best-price", icon: "fa-solid fa-tag" },
                matchKeywords: ["h - upper", "stand h", "upper", "h"]
            },
            {
                name: "D Corporate",
                sectorSelector: ".sector-d-corporate",
                row: "Row C",
                price: 5162,
                rating: "9.3 Amazing",
                features: ["tickets_together", "Clear view"],
                tag: { text: "Best deal", type: "best-deal", icon: "fa-solid fa-sparkles" },
                matchKeywords: ["d - lower", "corporate", "stand d", "d"]
            },
            {
                name: "Grand Terrace",
                sectorSelector: ".sector-grand-terrace",
                row: "Row A",
                price: 6283,
                rating: "8.7 Excellent",
                features: ["tickets_together", "Clear view"],
                tag: { text: "Only 2 left", type: "only-left", icon: "fa-solid fa-bookmark" },
                matchKeywords: ["pavilion end - upper", "grand terrace", "terrace", "pavilion"]
            },
            {
                name: "B Stand",
                sectorSelector: ".sector-b-stand",
                row: "Row BLANK",
                price: 4488,
                rating: "8.3 Great",
                features: ["tickets_together", "Clear view", "Instant download"],
                tag: { text: "Selling fast", type: "selling-fast", icon: "fa-solid fa-fire" },
                matchKeywords: ["stand b", "b - lower", "b - upper", "b"]
            },
            {
                name: "A Stand",
                sectorSelector: ".sector-a-stand",
                row: "Row D",
                price: 4636,
                rating: "8.5 Great",
                features: ["tickets_together", "Clear view"],
                tag: { text: "Best value", type: "best-price", icon: "fa-solid fa-thumbs-up" },
                matchKeywords: ["stand a", "a - lower", "a - upper", "a"]
            },
            {
                name: "Platinum Lounge",
                sectorSelector: ".sector-platinum-lounge",
                row: "Row VIP",
                price: 21691,
                rating: "9.8 Premium",
                features: ["tickets_together", "Prime Pavilion View & Buffet Dining", "VIP Fast-track Entry"],
                tag: { text: "VIP Hospitality", type: "best-deal", icon: "fa-solid fa-crown" },
                matchKeywords: ["pavilion end - lower", "platinum", "vip", "lounge"]
            },
            {
                name: "E Executive",
                sectorSelector: ".sector-e-executive",
                row: "Row B",
                price: 6732,
                rating: "8.9 Great",
                features: ["tickets_together", "Clear view", "Prime Lower Stand View"],
                tag: { text: "Executive Club", type: "best-price", icon: "fa-solid fa-star" },
                matchKeywords: ["stand e", "e - lower", "executive", "e"]
            },
            {
                name: "Stand F",
                sectorSelector: ".sector-stand-f",
                row: "Row E",
                price: 5982,
                rating: "8.1 Great",
                features: ["tickets_together", "Clear view"],
                tag: { text: "Popular", type: "best-price", icon: "fa-solid fa-fire" },
                matchKeywords: ["stand f", "f - lower", "f - upper", "f"]
            },
            {
                name: "P Terrace",
                sectorSelector: ".sector-p-corp",
                row: "Row Terrace",
                price: 13464,
                rating: "9.5 Outstanding",
                features: ["tickets_together", "Panoramic Pitch View"],
                tag: { text: "Terrace Access", type: "best-deal", icon: "fa-solid fa-ticket" },
                matchKeywords: ["p terrace", "stand c", "stand g"]
            },
            {
                name: "P Corp",
                sectorSelector: ".sector-p-corp",
                row: "Corporate Box",
                price: 34407,
                rating: "9.9 Luxury",
                features: ["tickets_together", "Full Corporate Box Hospitality"],
                tag: { text: "Corporate Luxury", type: "best-deal", icon: "fa-solid fa-gem" },
                matchKeywords: ["p corp", "corporate box", "stand i"]
            },
            {
                name: "C Stand",
                sectorSelector: ".sector-c-stand",
                row: "Row C",
                price: 3850,
                rating: "8.4 Great",
                features: ["tickets_together", "Clear view", "Instant download"],
                tag: { text: "Best value", type: "best-price", icon: "fa-solid fa-tag" },
                matchKeywords: ["stand c", "c - lower", "c - upper", "c"]
            },
            {
                name: "E Stand",
                sectorSelector: ".sector-e-stand",
                row: "Row E",
                price: 4500,
                rating: "8.6 Great",
                features: ["tickets_together", "Clear view", "Mid Stand Elevation"],
                tag: { text: "Popular", type: "best-price", icon: "fa-solid fa-fire" },
                matchKeywords: ["stand e - upper", "stand e", "e"]
            },
            {
                name: "Block 1",
                sectorSelector: ".sector-block-1",
                row: "Row 1",
                price: 4150,
                rating: "8.2 Great",
                features: ["tickets_together", "Inner Ring Pitch View"],
                tag: { text: "Pitch view", type: "best-deal", icon: "fa-solid fa-star" },
                matchKeywords: ["stand g - lower", "stand g", "g"]
            },
            {
                name: "Block 2",
                sectorSelector: ".sector-block-2",
                row: "Row 2",
                price: 4150,
                rating: "8.3 Great",
                features: ["tickets_together", "Clear view", "Near Boundary"],
                tag: { text: "Selling fast", type: "selling-fast", icon: "fa-solid fa-fire" },
                matchKeywords: ["stand g - upper", "stand g"]
            },
            {
                name: "P3 Block 2",
                sectorSelector: ".sector-p3-block2",
                row: "Row P3",
                price: 4950,
                rating: "8.8 Great",
                features: ["tickets_together", "Clear view", "Elevated Sightline"],
                tag: { text: "Great view", type: "best-price", icon: "fa-solid fa-thumbs-up" },
                matchKeywords: ["stand a - upper", "stand a"]
            },
            {
                name: "P1 Annexe Stand",
                sectorSelector: ".sector-p1-annexe",
                row: "Row P1",
                price: 4850,
                rating: "8.5 Great",
                features: ["tickets_together", "Annexe View & Easy Entry"],
                tag: { text: "Annexe Stand", type: "best-deal", icon: "fa-solid fa-bookmark" },
                matchKeywords: ["stand f - upper", "stand f"]
            },
            {
                name: "GR Vishwanath Stand P2",
                sectorSelector: ".sector-p2-vishwanath",
                row: "Row P2",
                price: 5450,
                rating: "9.1 Amazing",
                features: ["tickets_together", "Prime Boundary Action View"],
                tag: { text: "Pavilion View", type: "best-deal", icon: "fa-solid fa-crown" },
                matchKeywords: ["stand d - upper", "stand d"]
            },
            {
                name: "M3 / M4",
                sectorSelector: ".sector-m4",
                row: "Row M",
                price: 3950,
                rating: "8.0 Good",
                features: ["tickets_together", "Clear view of pitch"],
                tag: { text: "Value ticket", type: "best-price", icon: "fa-solid fa-tag" },
                matchKeywords: ["stand h - lower", "stand h"]
            },
            {
                name: "M4 Stand",
                sectorSelector: ".sector-m-inner",
                row: "Row M4",
                price: 3950,
                rating: "8.1 Good",
                features: ["tickets_together", "Inner Ring Seating"],
                tag: { text: "Inner stand", type: "best-price", icon: "fa-solid fa-ticket" },
                matchKeywords: ["stand i - lower", "stand i"]
            },
            {
                name: "M2 / M1",
                sectorSelector: ".sector-m-inner-south",
                row: "Row M2",
                price: 3750,
                rating: "7.9 Good",
                features: ["tickets_together", "Budget-Friendly Seating"],
                tag: { text: "Budget deal", type: "best-price", icon: "fa-solid fa-tag" },
                matchKeywords: ["stand i - upper", "stand i"]
            },
            {
                name: "P1 Stand",
                sectorSelector: ".sector-p1-inner",
                row: "Row P1",
                price: 4200,
                rating: "8.3 Great",
                features: ["tickets_together", "Close to Pitch"],
                tag: { text: "Inner pitch view", type: "best-deal", icon: "fa-solid fa-star" },
                matchKeywords: ["stand c - lower", "stand c"]
            }
        ];

        // Map real seats to each stand configuration
        this.cricketStandSeatsMap = new Map();
        this.cricketStandConfigs.forEach(cfg => {
            let matching = [];
            for (const kw of cfg.matchKeywords) {
                matching = this.seatsData.filter(s => s.section.toLowerCase().includes(kw));
                if (matching.length > 0) break;
            }
            if (matching.length === 0) {
                matching = this.seatsData;
            }
            this.cricketStandSeatsMap.set(cfg.name, matching);
        });

        const existingCards = cardsContainer.querySelectorAll('.cricket-ticket-card');
        if (existingCards.length > 0) {
            existingCards.forEach(card => {
                const standName = card.dataset.stand;
                card.onclick = () => this.selectCricketStand(standName);
                const btn = card.querySelector('.card-select-btn');
                if (btn) {
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        this.selectCricketStand(standName);
                    };
                }
            });
        } else {
            const qtyText = this.cricketQty === 1 ? '1 ticket' : `${this.cricketQty} tickets together`;

            this.cricketStandConfigs.forEach((cfg, idx) => {
                const cardEl = document.createElement('div');
                const slug = cfg.name.toLowerCase().replace(/[^a-z0-9]/g, '-');
                cardEl.className = `cricket-ticket-card ${idx === 0 ? 'selected-card' : ''}`;
                cardEl.id = `cricket-card-${slug}`;
                cardEl.dataset.stand = cfg.name;
                cardEl.onclick = () => this.selectCricketStand(cfg.name);

                const featuresHtml = cfg.features.map(f => {
                    if (f === 'tickets_together') {
                        return `<li><i class="fa-solid fa-users"></i> <span class="card-qty-label">${qtyText}</span></li>`;
                    }
                    if (f.toLowerCase().includes('resale')) {
                        return `<li><i class="fa-solid fa-triangle-exclamation"></i> ${f}</li>`;
                    }
                    if (f.toLowerCase().includes('instant') || f.toLowerCase().includes('fast')) {
                        return `<li><i class="fa-solid fa-bolt"></i> ${f}</li>`;
                    }
                    return `<li><i class="fa-regular fa-eye"></i> ${f}</li>`;
                }).join('');

                const qty = this.cricketQty || 2;
                const total = cfg.price * qty;

                cardEl.innerHTML = `
                    <div class="card-main-row">
                        <div class="card-left-info">
                            <h4 class="card-stand-name">${escapeHtml(cfg.name)}</h4>
                            <div class="card-row-info"><i class="fa-solid fa-location-dot" style="color: #94a3b8; font-size: 0.75rem; margin-right: 4px;"></i>${escapeHtml(cfg.row)} &bull; Stadium Stand</div>
                            <ul class="card-features-list">
                                ${featuresHtml}
                            </ul>
                            <div class="card-tag-pill tag-${cfg.tag.type}">
                                <i class="${cfg.tag.icon}"></i> ${escapeHtml(cfg.tag.text)}
                            </div>
                        </div>
                        <div class="card-right-info">
                            <div class="card-price-value" data-base-price="${cfg.price}">INR ${total.toLocaleString('en-IN')}</div>
                            <div class="card-price-calc" data-base-price="${cfg.price}" style="${qty > 1 ? '' : 'display: none;'}">(${qty} &times; INR ${cfg.price.toLocaleString('en-IN')})</div>
                            <div class="card-unit-price">INR ${cfg.price.toLocaleString('en-IN')} / ticket</div>
                            <div class="card-rating-badge">
                                ${escapeHtml(cfg.rating)}
                            </div>
                            <button type="button" class="card-select-btn" onclick="event.stopPropagation(); window.seatMapEngineInstance.selectCricketStand('${cfg.name}')">
                                Select
                            </button>
                        </div>
                    </div>
                `;

                cardsContainer.appendChild(cardEl);
            });
        }

        // Apply price calculation for selected quantity
        this.onCricketQtyChanged(this.cricketQty || 2, false);

        // Automatically select initial first stand (H Upper)
        this.selectCricketStand(this.activeCricketStand || "H Upper", false);
    }

    cricketZoomIn() {
        this.cricketSvgZoom = Math.min(1.6, (this.cricketSvgZoom || 1.0) + 0.15);
        const svg = document.getElementById('cricketStadiumSvg');
        if (svg) svg.style.transform = `scale(${this.cricketSvgZoom})`;
    }

    cricketZoomOut() {
        this.cricketSvgZoom = Math.max(0.7, (this.cricketSvgZoom || 1.0) - 0.15);
        const svg = document.getElementById('cricketStadiumSvg');
        if (svg) svg.style.transform = `scale(${this.cricketSvgZoom})`;
    }

    onCricketQtyChanged(newQty, doLock = true) {
        this.cricketQty = parseInt(newQty) || 2;
        const qtyText = this.cricketQty === 1 ? '1 ticket' : `${this.cricketQty} tickets together`;

        // 1. Update ticket quantity labels across all cards
        document.querySelectorAll('.card-qty-label').forEach(el => {
            el.textContent = qtyText;
        });

        // 2. Recalculate ticket prices on all stand cards
        document.querySelectorAll('.cricket-ticket-card').forEach(card => {
            const priceValEl = card.querySelector('.card-price-value');
            const priceCalcEl = card.querySelector('.card-price-calc');
            if (priceValEl) {
                const basePrice = parseFloat(priceValEl.dataset.basePrice) || 0;
                const total = basePrice * this.cricketQty;
                priceValEl.textContent = `INR ${total.toLocaleString('en-IN')}`;
                if (priceCalcEl) {
                    if (this.cricketQty > 1) {
                        priceCalcEl.innerHTML = `(${this.cricketQty} &times; INR ${basePrice.toLocaleString('en-IN')})`;
                        priceCalcEl.style.display = 'inline-block';
                    } else {
                        priceCalcEl.style.display = 'none';
                    }
                }
            }
        });

        // 3. Reselect currently active stand to update seat lock and bottom summary bar
        const activeStand = this.activeCricketStand || 'H Upper';
        this.selectCricketStand(activeStand, doLock);
    }

    async selectCricketStand(standName, doLock = true) {
        this.activeCricketStand = standName;
        const cfg = (this.cricketStandConfigs || []).find(c => c.name === standName) || { name: standName, price: 4338 };

        // Highlight card in right column
        document.querySelectorAll('.cricket-ticket-card').forEach(c => {
            if (c.dataset.stand === standName) {
                c.classList.add('selected-card');
                c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                c.classList.remove('selected-card');
            }
        });

        // Highlight sector in left stadium SVG
        document.querySelectorAll('.stadium-sector').forEach(sec => {
            sec.classList.remove('sector-selected');
        });
        if (cfg && cfg.sectorSelector) {
            const sectorEl = document.querySelector(cfg.sectorSelector);
            if (sectorEl) {
                sectorEl.classList.add('sector-selected');
            }
        }

        // Highlight active floating badge pill
        document.querySelectorAll('.floating-badge-pill').forEach(pill => {
            pill.classList.remove('active-pill');
        });
        const activePill = document.querySelector(`.floating-badge-pill[data-stand="${standName}"]`);
        if (activePill) {
            activePill.classList.add('active-pill');
        }

        // Reserve matching tickets in this stand
        const seatsPool = (this.cricketStandSeatsMap && this.cricketStandSeatsMap.get(standName)) || this.seatsData;
        const available = seatsPool.filter(s => s.status === 'AVAILABLE' || s.is_my_lock);
        const targetQty = this.cricketQty || 2;
        const toSelect = available.slice(0, Math.min(targetQty, available.length));

        // Release previously held seats
        if (this.selectedSeats.size > 0) {
            this.selectedSeats.clear();
        }

        toSelect.forEach(s => {
            if (cfg.price) {
                s.price = cfg.price;
            }
            this.selectedSeats.set(s.id, s);
        });

        if (doLock && toSelect.length > 0) {
            await this.syncLocksWithServer();
        }
        this.updateSummaryUI();
    }

    // Concert Layout Rendering
    renderConcertLayout(container) {
        const sections = this.groupSeatsBySectionAndRow(this.seatsData);

        const orderedSectionNames = Object.keys(sections).sort((a, b) => {
            const secA = (this.sections || []).find(s => s.name && s.name.toLowerCase() === a.toLowerCase());
            const secB = (this.sections || []).find(s => s.name && s.name.toLowerCase() === b.toLowerCase());
            if (secA && secB && secA.display_order !== undefined && secB.display_order !== undefined) {
                return secA.display_order - secB.display_order;
            }
            const priceA = Object.values(sections[a])[0]?.[0]?.price || 0;
            const priceB = Object.values(sections[b])[0]?.[0]?.price || 0;
            return priceB - priceA;
        });

        for (const sectionName of orderedSectionNames) {
            const rows = sections[sectionName];
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'seat-section-block';

            const firstSeat = Object.values(rows)[0][0];
            const secMeta = (this.sections || []).find(s => s.name && s.name.toLowerCase() === sectionName.toLowerCase());
            const secColor = secMeta && secMeta.color ? secMeta.color : '#a855f7';
            sectionDiv.style.borderLeft = `4px solid ${secColor}`;

            sectionDiv.innerHTML = `
                <div class="section-block-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;">
                    <h4 class="section-block-title" style="margin: 0; display: flex; align-items: center; gap: 0.5rem; color: #1e293b;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: ${secColor}; display: inline-block;"></span>
                        <span>${escapeHtml(sectionName)}</span>
                        <span style="font-size: 0.85rem; color: #64748b; font-weight: 600;">&bull; ₹${parseFloat(firstSeat.price).toLocaleString('en-IN')} / ticket</span>
                    </h4>
                    <span class="badge badge-secondary" style="font-size: 0.75rem;">${Object.values(rows).flat().length} Seats</span>
                </div>
            `;

            for (const [rowLabel, rowSeats] of Object.entries(rows)) {
                const rowDiv = document.createElement('div');
                rowDiv.className = 'seat-row';

                const labelSpan = document.createElement('span');
                labelSpan.className = 'row-label';
                labelSpan.textContent = rowLabel;
                rowDiv.appendChild(labelSpan);

                rowSeats.forEach(seat => {
                    const seatEl = this.createSeatElement(seat);
                    rowDiv.appendChild(seatEl);
                });

                sectionDiv.appendChild(rowDiv);
            }
            container.appendChild(sectionDiv);
        }
    }

    // General Layout Rendering
    renderGeneralLayout(container) {
        const sections = this.groupSeatsBySectionAndRow(this.seatsData);

        const orderedSectionNames = Object.keys(sections).sort((a, b) => {
            const secA = (this.sections || []).find(s => s.name && s.name.toLowerCase() === a.toLowerCase());
            const secB = (this.sections || []).find(s => s.name && s.name.toLowerCase() === b.toLowerCase());
            if (secA && secB && secA.display_order !== undefined && secB.display_order !== undefined) {
                return secA.display_order - secB.display_order;
            }
            const priceA = Object.values(sections[a])[0]?.[0]?.price || 0;
            const priceB = Object.values(sections[b])[0]?.[0]?.price || 0;
            return priceB - priceA;
        });

        for (const sectionName of orderedSectionNames) {
            const rows = sections[sectionName];
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'seat-section-block';

            const firstSeat = Object.values(rows)[0][0];
            const secMeta = (this.sections || []).find(s => s.name && s.name.toLowerCase() === sectionName.toLowerCase());
            const secColor = secMeta && secMeta.color ? secMeta.color : '#06b6d4';
            sectionDiv.style.borderLeft = `4px solid ${secColor}`;

            sectionDiv.innerHTML = `
                <div class="section-block-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;">
                    <h4 class="section-block-title" style="margin: 0; display: flex; align-items: center; gap: 0.5rem; color: #1e293b;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: ${secColor}; display: inline-block;"></span>
                        <span>${escapeHtml(sectionName)}</span>
                        <span style="font-size: 0.85rem; color: #64748b; font-weight: 600;">&bull; ₹${parseFloat(firstSeat.price).toLocaleString('en-IN')} / ticket</span>
                    </h4>
                    <span class="badge badge-secondary" style="font-size: 0.75rem;">${Object.values(rows).flat().length} Seats</span>
                </div>
            `;

            for (const [rowLabel, rowSeats] of Object.entries(rows)) {
                const rowDiv = document.createElement('div');
                rowDiv.className = 'seat-row';

                const labelSpan = document.createElement('span');
                labelSpan.className = 'row-label';
                labelSpan.textContent = rowLabel;
                rowDiv.appendChild(labelSpan);

                rowSeats.forEach(seat => {
                    const seatEl = this.createSeatElement(seat);
                    rowDiv.appendChild(seatEl);
                });

                sectionDiv.appendChild(rowDiv);
            }
            container.appendChild(sectionDiv);
        }
    }

    // Create Individual Seat Element
    createSeatElement(seat) {
        const div = document.createElement('div');
        div.id = `seat-${seat.id}`;
        div.dataset.seatId = seat.id;
        div.dataset.seatNumber = seat.seat_number;
        div.dataset.price = seat.price;

        let status = seat.status.toLowerCase();
        if (this.selectedSeats.has(seat.id)) {
            status = 'selected';
        }

        const isAdminLocked = status === 'admin_locked' || status === 'admin-locked';
        div.className = `seat ${isAdminLocked ? 'admin-locked disabled' : status}`;

        // Clean seat label (show seat index or clean number)
        let numLabel = seat.seat_index ? seat.seat_index : seat.seat_number;
        if (!seat.seat_index) {
            if (numLabel.includes('-')) {
                const parts = numLabel.split('-');
                numLabel = parts[parts.length - 1];
            } else {
                numLabel = numLabel.replace(/^[A-Z]+/, '');
            }
        }

        let titleText = `${seat.section} • Row ${seat.row_label || ''} Seat ${seat.seat_index || numLabel} (${seat.seat_number}) - ₹${parseFloat(seat.price).toLocaleString('en-IN')}`;
        if (isAdminLocked) {
            const reasonTxt = seat.admin_reserve_reason ? ` (${seat.admin_reserve_reason})` : '';
            titleText = `${seat.seat_number} - Reserved by Admin${reasonTxt}`;
        }
        div.title = titleText;

        if (isAdminLocked) {
            div.innerHTML = '<i class="fa-solid fa-user-tie"></i>';
        } else if (status === 'locked') {
            div.innerHTML = '<i class="fa-solid fa-lock"></i>';
        } else if (status !== 'booked') {
            div.textContent = numLabel;
        }

        div.addEventListener('click', () => this.handleSeatClick(seat));
        return div;
    }

    // Handle Seat Click & Server-Side Locking
    async handleSeatClick(seat) {
        if (seat.status === 'ADMIN_LOCKED' || seat.status === 'admin_locked') {
            const reason = seat.admin_reserve_reason ? ` for ${seat.admin_reserve_reason}` : '';
            showToast(`This seat is reserved by the admin${reason}.`, 'warning');
            return;
        }

        if (seat.status === 'BOOKED') {
            showToast(`Seat ${seat.seat_number} is already booked.`, 'info');
            return;
        }

        if (seat.status === 'LOCKED' && !this.selectedSeats.has(seat.id)) {
            showToast(`Seat ${seat.seat_number} is currently locked by another user.`, 'warning');
            return;
        }

        // Toggle Selection
        if (this.selectedSeats.has(seat.id)) {
            // Unselect seat
            this.selectedSeats.delete(seat.id);
            seat.status = 'AVAILABLE';
            this.updateSeatElementState(seat.id, 'available');

            // Explicitly release the deselected seat on server
            this.releaseSingleSeat(seat.id);

            // If all unselected, release locks and hide countdown
            if (this.selectedSeats.size === 0) {
                if (this.lockCountdownInterval) {
                    clearInterval(this.lockCountdownInterval);
                }
                const countdownBox = document.getElementById('lockCountdownBox');
                if (countdownBox) countdownBox.classList.add('hidden');
            } else {
                // Refresh server locks with remaining seats
                await this.syncLocksWithServer();
            }
            this.updateSummaryUI();
            return;
        }

        // Check Maximum Limit
        if (this.selectedSeats.size >= this.maxTickets) {
            showToast(`Maximum ${this.maxTickets} tickets can be booked in one transaction.`, 'warning');
            return;
        }

        // Temporary optimistic select
        this.selectedSeats.set(seat.id, seat);
        this.updateSeatElementState(seat.id, 'selected');

        // Request Server-Side 5-Minute Lock
        const success = await this.syncLocksWithServer();
        if (!success) {
            // Rollback optimistic selection
            this.selectedSeats.delete(seat.id);
            seat.status = 'AVAILABLE';
            this.updateSeatElementState(seat.id, 'available');
        }

        this.updateSummaryUI();
    }

    // Explicitly release a single seat lock
    async releaseSingleSeat(seatId) {
        try {
            await fetch('/api/seats/release', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seat_ids: [seatId] }),
            });
        } catch (err) {}
    }

    // Sync Locks with Server via POST /api/seats/lock
    async syncLocksWithServer() {
        const seatIds = Array.from(this.selectedSeats.keys());
        if (seatIds.length === 0) return true;

        try {
            const response = await fetch('/api/seats/lock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    event_id: this.eventId,
                    seat_ids: seatIds,
                }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
                const lockData = data.data;
                this.startLockCountdown(lockData.seconds_remaining || this.lockDuration);
                return true;
            } else {
                showToast(data.message || 'Seat is unavailable.', 'danger');
                return false;
            }
        } catch (err) {
            showToast('Network error while locking seat.', 'danger');
            return false;
        }
    }

    // Release All Locks Held by Session
    async releaseAllLocks() {
        if (this.lockCountdownInterval) {
            clearInterval(this.lockCountdownInterval);
        }
        const countdownBox = document.getElementById('lockCountdownBox');
        if (countdownBox) countdownBox.classList.add('hidden');

        try {
            await fetch('/api/seats/release', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
        } catch (err) {}
    }

    // Update Single Seat Element Class
    updateSeatElementState(seatId, state) {
        const el = document.getElementById(`seat-${seatId}`);
        if (!el) return;

        const stateLower = state.toLowerCase();
        if (stateLower === 'admin_locked' || stateLower === 'admin-locked') {
            el.className = 'seat admin-locked disabled';
            const seatObj = this.seatsData.find(s => s.id === seatId);
            const reasonTxt = seatObj && seatObj.admin_reserve_reason ? ` (${seatObj.admin_reserve_reason})` : '';
            el.title = `Seat ${seatObj ? seatObj.seat_number : ''} - Reserved by Admin${reasonTxt}`;
            el.innerHTML = '<i class="fa-solid fa-user-tie"></i>';
        } else {
            el.className = `seat ${stateLower}`;
            if (stateLower === 'locked') {
                el.innerHTML = '<i class="fa-solid fa-lock"></i>';
            } else if (stateLower === 'booked') {
                el.innerHTML = '';
            } else {
                const seatObj = this.seatsData.find(s => s.id === seatId);
                if (seatObj) {
                    let num = seatObj.seat_number;
                    if (num.includes('-')) num = num.split('-').pop();
                    else num = num.replace(/^[A-Z]+/, '');
                    el.textContent = num;
                }
            }
        }
    }

    // Start 5-Minute Lock Countdown
    startLockCountdown(seconds) {
        const countdownBox = document.getElementById('lockCountdownBox');
        const display = document.getElementById('lockTimerDisplay');
        if (!countdownBox || !display) return;

        countdownBox.classList.remove('hidden');
        let remaining = seconds;

        if (this.lockCountdownInterval) clearInterval(this.lockCountdownInterval);

        this.lockCountdownInterval = setInterval(() => {
            remaining--;

            if (remaining <= 0) {
                clearInterval(this.lockCountdownInterval);
                display.textContent = '00:00';
                showToast('Your 5-minute seat lock has expired. Please reselect your seats.', 'danger');
                
                // Clear state
                this.selectedSeats.forEach((_, id) => {
                    this.updateSeatElementState(id, 'available');
                });
                this.selectedSeats.clear();
                this.updateSummaryUI();
                countdownBox.classList.add('hidden');
                return;
            }

            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            display.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }, 1000);
    }

    // Update Bottom Summary Bar & Proceed Button
    updateSummaryUI() {
        const countEl = document.getElementById('selectedCount');
        const chipsEl = document.getElementById('selectedSeatsChips');
        const priceEl = document.getElementById('totalPriceDisplay');
        const proceedBtn = document.getElementById('proceedToAttendeeBtn');

        const count = this.selectedSeats.size;
        countEl.textContent = count;

        let grandTotal = 0;
        chipsEl.innerHTML = '';

        if (count === 0) {
            chipsEl.innerHTML = '<span class="no-selection-hint">Click on available seats on the map to reserve</span>';
            priceEl.textContent = '₹0';
            proceedBtn.disabled = true;
            return;
        }

        // Group selected seats by section/stand
        const bySection = new Map();
        this.selectedSeats.forEach(seat => {
            const secName = seat.section || 'General';
            if (!bySection.has(secName)) {
                bySection.set(secName, {
                    name: secName,
                    price: parseFloat(seat.price),
                    seats: [],
                });
            }
            bySection.get(secName).seats.push(seat);
            grandTotal += parseFloat(seat.price);
        });

        // Display formatted summary chips: Section – Seat1, Seat2 = Qty × ₹Price = ₹Total
        bySection.forEach(secGroup => {
            const qty = secGroup.seats.length;
            const secTotal = qty * secGroup.price;
            const seatNames = secGroup.seats.map(s => {
                let label = s.seat_number;
                if (s.row_label && s.seat_index) {
                    label = `${s.row_label}${s.seat_index}`;
                } else if (label.includes('-')) {
                    const parts = label.split('-');
                    label = parts[parts.length - 1];
                }
                return label;
            }).join(', ');

            const chip = document.createElement('span');
            chip.className = 'selected-chip dynamic-section-summary';
            chip.style.display = 'inline-flex';
            chip.style.alignItems = 'center';
            chip.style.gap = '0.35rem';
            chip.style.padding = '0.35rem 0.85rem';
            chip.style.borderRadius = '999px';
            chip.style.background = '#fff7ed';
            chip.style.border = '1px solid #fed7aa';
            chip.style.color = '#c2410c';
            chip.style.fontSize = '0.85rem';
            chip.style.fontWeight = '700';
            chip.style.margin = '0.2rem';

            chip.innerHTML = `
                <span><strong>${escapeHtml(secGroup.name)}</strong> &ndash; ${escapeHtml(seatNames)} = ${qty} &times; ₹${secGroup.price.toLocaleString('en-IN')} = <strong>₹${secTotal.toLocaleString('en-IN')}</strong></span>
            `;
            chipsEl.appendChild(chip);
        });

        priceEl.textContent = `₹${grandTotal.toLocaleString('en-IN')}`;
        proceedBtn.disabled = false;
    }

    // Real-Time Polling for Concurrency
    startStatusPolling() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);

        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/events/${this.eventId}/seat-status`);
                const data = await response.json();

                if (data.success && data.status_map) {
                    for (const [seatIdStr, status] of Object.entries(data.status_map)) {
                        const seatId = parseInt(seatIdStr);
                        const seatObj = this.seatsData.find(s => s.id === seatId);
                        if (seatObj) {
                            seatObj.status = status;
                            if (data.reason_map && data.reason_map[seatId]) {
                                seatObj.admin_reserve_reason = data.reason_map[seatId];
                            }
                        }

                        // If seat became BOOKED or ADMIN_LOCKED, deselect it if user had it selected
                        if (status === 'BOOKED' || status === 'ADMIN_LOCKED') {
                            if (this.selectedSeats.has(seatId)) {
                                this.selectedSeats.delete(seatId);
                                this.updateSummaryUI();
                                showToast(`Seat ${seatObj ? seatObj.seat_number : ''} is reserved/unavailable.`, 'warning');
                            }
                            this.updateSeatElementState(seatId, status);
                        } else if (!this.selectedSeats.has(seatId)) {
                            this.updateSeatElementState(seatId, status);
                        }
                    }
                }
            } catch (e) {}
        }, 4000);
    }

    // ==========================================
    // Interactive Zoom Controls Engine
    // ==========================================
    zoomIn() {
        this.setZoom(this.currentZoom + this.zoomStep);
    }

    zoomOut() {
        this.setZoom(this.currentZoom - this.zoomStep);
    }

    resetZoom() {
        this.setZoom(1.0);
    }

    setZoom(level) {
        this.currentZoom = Math.min(this.maxZoom, Math.max(this.minZoom, parseFloat(level.toFixed(2))));
        this.applyZoom();
    }

    applyZoom() {
        const viewport = document.getElementById('seatGridViewport');
        const badge = document.getElementById('zoomLevelDisplay');
        const zoomInBtn = document.getElementById('zoomInBtn');
        const zoomOutBtn = document.getElementById('zoomOutBtn');

        if (viewport) {
            viewport.style.transform = `scale(${this.currentZoom})`;
        }

        if (badge) {
            badge.textContent = `${Math.round(this.currentZoom * 100)}%`;
        }

        if (zoomInBtn) {
            zoomInBtn.disabled = this.currentZoom >= this.maxZoom;
        }

        if (zoomOutBtn) {
            zoomOutBtn.disabled = this.currentZoom <= this.minZoom;
        }
    }

    setupZoomEventListeners() {
        const layoutCard = document.querySelector('.seat-layout-card');
        if (!layoutCard) return;

        // Mouse Wheel Zoom with Ctrl + Wheel
        layoutCard.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                if (e.deltaY < 0) {
                    this.zoomIn();
                } else {
                    this.zoomOut();
                }
            }
        }, { passive: false });

        // Touch Pinch-to-Zoom for Mobile
        let touchStartDist = 0;
        let initialZoom = 1.0;

        layoutCard.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                touchStartDist = Math.hypot(
                    e.touches[0].pageX - e.touches[1].pageX,
                    e.touches[0].pageY - e.touches[1].pageY
                );
                initialZoom = this.currentZoom;
            }
        }, { passive: true });

        layoutCard.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2 && touchStartDist > 0) {
                const currentDist = Math.hypot(
                    e.touches[0].pageX - e.touches[1].pageX,
                    e.touches[0].pageY - e.touches[1].pageY
                );
                const scaleDiff = (currentDist - touchStartDist) / 250;
                this.setZoom(initialZoom + scaleDiff);
            }
        }, { passive: true });

        layoutCard.addEventListener('touchend', () => {
            touchStartDist = 0;
        }, { passive: true });
    }
}

// Global filter callbacks for Cricket Stadium
let seatMapEngineInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    seatMapEngineInstance = new SeatMapEngine();
    window.seatMapEngineInstance = seatMapEngineInstance;
});

function selectCricketSector(standName) {
    if (window.seatMapEngineInstance) {
        window.seatMapEngineInstance.selectCricketStand(standName, true);
    }
}

function onCricketQtyChanged(newQty) {
    if (window.seatMapEngineInstance) {
        window.seatMapEngineInstance.onCricketQtyChanged(newQty);
    }
}

function filterStadiumStand(stand, btn) {
    if (!btn) {
        btn = document.querySelector(`.stand-tab[data-stand="${stand}"]`);
    }
    document.querySelectorAll('.stand-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');

    if (seatMapEngineInstance) {
        seatMapEngineInstance.activeStand = stand;
        seatMapEngineInstance.renderSeatMap();
    }
}

function filterStadiumTier(tier, btn) {
    document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (seatMapEngineInstance) {
        seatMapEngineInstance.activeTier = tier;
        seatMapEngineInstance.renderSeatMap();
    }
}

function selectStandTier(stand, tier) {
    // Sync Stand Tabs
    document.querySelectorAll('.stand-tab').forEach(t => {
        if (t.dataset.stand && t.dataset.stand.toLowerCase() === stand.toLowerCase()) {
            t.classList.add('active');
        } else {
            t.classList.remove('active');
        }
    });

    // Sync Tier Buttons
    document.querySelectorAll('.tier-btn').forEach(b => {
        if (b.dataset.tier && b.dataset.tier.toLowerCase() === tier.toLowerCase()) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });

    if (seatMapEngineInstance) {
        seatMapEngineInstance.activeStand = stand;
        seatMapEngineInstance.activeTier = tier;
        seatMapEngineInstance.renderSeatMap();
    }

    // Smooth scroll to seat grid viewport
    const seatViewport = document.getElementById('seatGridViewport');
    if (seatViewport) {
        seatViewport.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function toggle360StadiumView() {
    const wrapper = document.getElementById('cricket360StadiumWrapper');
    const toggleBtn = document.getElementById('toggle360MapBtn');
    if (!wrapper) return;

    wrapper.classList.toggle('hidden');
    if (toggleBtn) {
        const isHidden = wrapper.classList.contains('hidden');
        toggleBtn.classList.toggle('active', !isHidden);
    }
}

function handleProceedToAttendees() {
    if (!seatMapEngineInstance || seatMapEngineInstance.selectedSeats.size === 0) return;
    window.location.href = `/booking/attendees?event_id=${seatMapEngineInstance.eventId}`;
}
