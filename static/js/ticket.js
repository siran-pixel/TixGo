/**
 * ShowSpot E-Ticket Interaction & Web Share JavaScript
 */

async function handleShareTicket(bookingRef, eventName) {
    const ticketUrl = `${window.location.origin}/tickets/${bookingRef}`;
    const shareData = {
        title: `ShowSpot E-Ticket - ${eventName}`,
        text: `Here are my tickets for ${eventName} on ShowSpot (Ref: ${bookingRef})`,
        url: ticketUrl,
    };

    if (navigator.share && navigator.canShare && navigator.canShare(shareData)) {
        try {
            await navigator.share(shareData);
            showToast('Ticket link shared successfully!', 'success');
            return;
        } catch (err) {
            if (err.name !== 'AbortError') {
                copyTicketLinkFallback(ticketUrl);
            }
            return;
        }
    }

    // Fallback: Copy link to clipboard
    copyTicketLinkFallback(ticketUrl);
}

function copyTicketLinkFallback(url) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(() => {
            showToast('Ticket URL copied to clipboard!', 'success');
        }).catch(() => {
            fallbackPromptCopy(url);
        });
    } else {
        fallbackPromptCopy(url);
    }
}

function fallbackPromptCopy(url) {
    window.prompt('Copy this ticket link to share:', url);
}
