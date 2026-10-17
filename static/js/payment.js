/**
 * ShowSpot Simulated Payment Gateway Interaction
 */

let selectedPaymentMethod = 'UPI';

function switchPaymentTab(method, btn) {
    selectedPaymentMethod = method;
    document.querySelectorAll('.pay-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.payment-panel').forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    const targetPanel = document.getElementById(`panel${method}`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }
}

async function processPaymentSubmission() {
    const payBtn = document.getElementById('payNowBtn');
    const payBtnText = document.getElementById('payBtnText');
    const payBtnIcon = document.getElementById('payBtnIcon');

    // Collect payment details
    const paymentDetails = {};

    if (selectedPaymentMethod === 'UPI') {
        const upiVal = document.getElementById('upiId')?.value || 'user@upi';
        paymentDetails.upi_id = upiVal;
    } else if (selectedPaymentMethod === 'CREDIT_CARD') {
        paymentDetails.card_number = document.getElementById('ccNumber')?.value;
        paymentDetails.expiry = document.getElementById('ccExpiry')?.value;
        paymentDetails.cardholder = document.getElementById('ccHolder')?.value;
    } else if (selectedPaymentMethod === 'DEBIT_CARD') {
        paymentDetails.card_number = document.getElementById('dcNumber')?.value;
        paymentDetails.expiry = document.getElementById('dcExpiry')?.value;
    } else if (selectedPaymentMethod === 'NET_BANKING') {
        const selectedBank = document.querySelector('input[name="selected_bank"]:checked')?.value || 'HDFC';
        paymentDetails.bank = selectedBank;
    }

    try {
        // UI Loading state
        payBtn.disabled = true;
        payBtnText.textContent = 'Processing Payment & Issuing Tickets...';
        payBtnIcon.className = 'fa-solid fa-spinner fa-spin';

        const response = await fetch('/api/payment/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                payment_method: selectedPaymentMethod,
                payment_details: paymentDetails,
            }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast('Payment successful! Redirecting to your tickets...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 800);
        } else {
            showToast(data.message || 'Payment processing failed. Please try again.', 'danger');
            payBtn.disabled = false;
            payBtnText.textContent = 'Pay Now';
            payBtnIcon.className = 'fa-solid fa-lock';
        }
    } catch (err) {
        showToast('Network error during transaction processing.', 'danger');
        payBtn.disabled = false;
        payBtnText.textContent = 'Pay Now';
        payBtnIcon.className = 'fa-solid fa-lock';
    }
}
