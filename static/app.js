function showInitial() {
    document.getElementById('initial').style.display = 'block';
    document.getElementById('signup').style.display = 'none';
    document.getElementById('login').style.display = 'none';
    document.getElementById('referral').style.display = 'none';
    
    // Hide any success or error messages
    document.getElementById('signup-success').style.display = 'none';
    document.getElementById('signup-error').style.display = 'none';
}


function showSignUp() {
    document.getElementById('initial').style.display = 'none';
    document.getElementById('signup').style.display = 'block';
}

function showLogin() {
    document.getElementById('initial').style.display = 'none';
    document.getElementById('login').style.display = 'block';
}

function signUp() {
    const phone = document.getElementById('signup-phone').value;
    const password = document.getElementById('signup-password').value;

    fetch('/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === "Signup successful.") {
            document.getElementById('signup-success').style.display = 'block';
            document.getElementById('signup-error').style.display = 'none';
            setTimeout(showLogin, 2000); // Redirect to login after 2 seconds
        } else {
            document.getElementById('signup-error').innerText = data.message;
            document.getElementById('signup-error').style.display = 'block';
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function login() {
    const phone = document.getElementById('login-phone').value;
    const password = document.getElementById('login-password').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            localStorage.setItem('token', data.token);
            showReferralView(data);
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function sendReferral() {
    const contactNumber = document.getElementById('contact-number').value;
    const referralType = document.querySelector('input[name="referral-type"]:checked').value;

    const referralCode = localStorage.getItem('referralCode');
    const referralLink = `https://api.whatsapp.com/send?phone=${contactNumber}&text=Hi%20User%2C%0A%0AYou%20have%20been%20referred%20to%20https%3A%2F%2Fwww.beepkart.com%0A%0ABeepKart%20is%20a%20trusted%20place%20to%20buy%20and%20sell%20used%20bikes.%0A%0AUse%20this%20referral%20code%20to%20transact%20and%20get%20Rs%20500%20%0A%0AReferral%20code%3A%20${referralCode}`;

    window.location.href = referralLink;

    // Optionally, send the referral data to your server
    fetch('/send_referral', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': localStorage.getItem('token')
        },
        body: JSON.stringify({ referred_phone: contactNumber, referral_type: referralType })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === "Referral sent.") {
            loadReferrals();
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}


function loadReferrals() {
    fetch('/protected', {
        method: 'GET',
        headers: {
            'Authorization': localStorage.getItem('token')
        }
    })
    .then(response => response.json())
    .then(data => {
        const referralList = document.getElementById('referral-list');
        referralList.innerHTML = '';

        data.referrals.forEach(referral => {
            const li = document.createElement('li');
            const status = referral.purchased ? 'Event Done' : 'Event Pending';
            const type = referral.type ? `Type: ${referral.type}` : 'Type: Unknown';
            li.textContent = `${referral.referred_phone} - ${status} - ${type}`;
            referralList.appendChild(li);
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}


function showReferralView(userData) {
    document.getElementById('initial').style.display = 'none';
    document.getElementById('signup').style.display = 'none';
    document.getElementById('login').style.display = 'none';
    document.getElementById('referral').style.display = 'block';

    loadReferrals();
}

function logout() {
    localStorage.removeItem('token');
    showInitial();
}

window.onload = function() {
    const token = localStorage.getItem('token');
    if (token) {
        fetch('/protected', {
            method: 'GET',
            headers: {
                'Authorization': token
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                showReferralView(data);
            } else {
                showInitial();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showInitial();
        });
    } else {
        showInitial();
    }
};
