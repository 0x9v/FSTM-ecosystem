require('dotenv').config();

module.exports = {
    PORT: 3000,
    GEMINI_API_KEY: process.env.GEMINI_API_KEY,
    // Safely parse the comma-separated strings from .env into an array
    ADMIN_IDS: process.env.ADMIN_IDS ? process.env.ADMIN_IDS.split(',') : [],
    FSTM_GROUP_ID: process.env.FSTM_GROUP_ID,
    WATCHDOG_GROUP_IDS: process.env.WATCHDOG_GROUP_IDS ? process.env.WATCHDOG_GROUP_IDS.split(',') : [],
    COOLDOWN_TIMES: {
        '!last': 60000,
        '!help': 30000,
        '!today': 60000,
        '!uptime': 10000,
        '!tmrw': 60000,
        '!ping': 5000,
        '!id': 5000,
        '!secret': 20000,
        '!emoonai': 15000
    }
};
