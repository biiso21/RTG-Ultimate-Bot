// دوال مساعدة للوحة التحكم

function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function showToast(message, type = 'success') {
    const toast = $(`
        <div class="toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `);
    $('body').append(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    setTimeout(() => toast.remove(), 3000);
}

async function fetchAPI(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (data) options.body = JSON.stringify(data);
    
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

function updateProgressBar(element, percent) {
    $(element).css('width', percent + '%').attr('aria-valuenow', percent);
    $(element).text(percent + '%');
}

// تحميل الإحصائيات تلقائياً كل 30 ثانية
let statsInterval = null;

function startAutoRefresh(guildId) {
    if (statsInterval) clearInterval(statsInterval);
    statsInterval = setInterval(() => {
        if (guildId) loadStats(guildId);
    }, 30000);
}

function stopAutoRefresh() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
}