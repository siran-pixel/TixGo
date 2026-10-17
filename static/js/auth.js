/**
 * ShowSpot Authentication & OTP JavaScript
 */

// Toggle Password Visibility
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Signup Form Validation
document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signupForm');
    const resetForm = document.getElementById('resetForm');

    const checkPasswordMatch = (pwId, cpwId, errId) => {
        const pw = document.getElementById(pwId);
        const cpw = document.getElementById(cpwId);
        const err = document.getElementById(errId);

        if (pw && cpw && err) {
            const validate = () => {
                if (cpw.value && pw.value !== cpw.value) {
                    err.classList.remove('hidden');
                    return false;
                } else {
                    err.classList.add('hidden');
                    return true;
                }
            };
            pw.addEventListener('input', validate);
            cpw.addEventListener('input', validate);
        }
    };

    if (signupForm) {
        checkPasswordMatch('password', 'confirmPassword', 'passwordMismatchError');
    }

    if (resetForm) {
        checkPasswordMatch('password', 'confirmPassword', 'passwordMismatchError');
    }

    // 6-Digit OTP Box Interactions
    const otpContainer = document.getElementById('otpInputsContainer');
    if (otpContainer) {
        setupOtpBoxes(otpContainer);
        startOtpCountdown(300); // 5 minutes
    }
});

// Autofill OTP helper
function autofillOtp(code) {
    if (!code) return;
    const inputs = document.querySelectorAll('.otp-digit');
    const codeStr = String(code).trim();
    inputs.forEach((inp, idx) => {
        inp.value = codeStr[idx] || '';
    });
    if (inputs.length > 0) {
        inputs[inputs.length - 1].focus();
    }
    const hidden = document.getElementById('combinedOtpInput');
    if (hidden) hidden.value = codeStr;
    showToast('OTP auto-filled! Click "Verify & Proceed".', 'info');
}

// Setup 6-Box OTP Inputs
function setupOtpBoxes(container) {
    const inputs = container.querySelectorAll('.otp-digit');
    const hiddenInput = document.getElementById('combinedOtpInput');
    const form = document.getElementById('otpForm');

    function updateCombinedOtp() {
        let code = '';
        inputs.forEach(inp => code += inp.value.trim());
        if (hiddenInput) hiddenInput.value = code;
        return code;
    }

    inputs.forEach((input, index) => {
        // Only allow digits & auto-advance
        input.addEventListener('input', (e) => {
            const val = e.target.value;
            if (!/^\d*$/.test(val)) {
                e.target.value = '';
                return;
            }

            if (val.length >= 1) {
                e.target.value = val.slice(-1); // keep last single digit
                if (index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
            }

            updateCombinedOtp();
        });

        // Handle Arrow navigation & Backspace
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace') {
                if (!e.target.value && index > 0) {
                    inputs[index - 1].focus();
                }
            } else if (e.key === 'ArrowLeft' && index > 0) {
                inputs[index - 1].focus();
            } else if (e.key === 'ArrowRight' && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });

        // Handle Paste (e.g. user pastes 6 digits)
        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pastedData = (e.clipboardData || window.clipboardData).getData('text').trim();
            const digitsOnly = pastedData.replace(/\D/g, '').slice(0, 6);
            if (digitsOnly.length > 0) {
                inputs.forEach((inp, idx) => {
                    inp.value = digitsOnly[idx] || '';
                });
                const focusIdx = Math.min(digitsOnly.length, inputs.length - 1);
                inputs[focusIdx].focus();
                updateCombinedOtp();
            }
        });
    });

    // Handle Form Submit Event
    if (form) {
        form.addEventListener('submit', (e) => {
            const code = updateCombinedOtp();
            if (code.length !== 6) {
                e.preventDefault();
                showToast('Please enter the complete 6-digit OTP code.', 'warning');
                for (let inp of inputs) {
                    if (!inp.value.trim()) {
                        inp.focus();
                        break;
                    }
                }
                return false;
            }
        });
    }
}

// 5-Minute OTP Expiration Countdown
let countdownInterval = null;

function startOtpCountdown(durationSeconds) {
    const timerDisplay = document.getElementById('otpTimer');
    const resendBtn = document.getElementById('resendOtpBtn');
    if (!timerDisplay) return;

    let remaining = durationSeconds;

    if (countdownInterval) clearInterval(countdownInterval);

    countdownInterval = setInterval(() => {
        remaining--;

        if (remaining <= 0) {
            clearInterval(countdownInterval);
            timerDisplay.textContent = '00:00';
            timerDisplay.style.color = '#ef4444';
            if (resendBtn) {
                resendBtn.disabled = false;
            }
            showToast('OTP has expired. Please click "Resend OTP Code".', 'warning');
            return;
        }

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }, 1000);
}

// Handle Resend OTP Action
async function handleResendOtp() {
    const emailInput = document.getElementById('otpEmailInput');
    const purposeInput = document.getElementById('otpPurposeInput');
    const resendBtn = document.getElementById('resendOtpBtn');

    if (!emailInput) return;

    const email = emailInput.value;
    const purpose = purposeInput ? purposeInput.value : 'SIGNUP';

    try {
        if (resendBtn) resendBtn.disabled = true;

        const response = await fetch('/api/auth/resend-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ email: email, purpose: purpose }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast(data.message || 'New OTP sent to your email!', 'success');
            // Clear inputs
            const inputs = document.querySelectorAll('.otp-digit');
            inputs.forEach(i => i.value = '');
            if (inputs[0]) inputs[0].focus();

            // Update demo display if returned
            if (data.demo_otp) {
                const demoDisplay = document.getElementById('demoOtpCodeDisplay');
                if (demoDisplay) demoDisplay.textContent = data.demo_otp;
            }

            // Reset countdown timer
            startOtpCountdown(300);
        } else {
            showToast(data.message || 'Failed to resend OTP.', 'danger');
            if (resendBtn) resendBtn.disabled = false;
        }
    } catch (err) {
        showToast('Network error while resending OTP. Please try again.', 'danger');
        if (resendBtn) resendBtn.disabled = false;
    }
}
