const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const config = require('./src/config');
const { handleMessage } = require('./src/handlers/messageRouter');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    dumpio: true,
    puppeteer: {
        executablePath: '/usr/bin/chromium',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--mute-audio',
            '--no-zygote',
            '--no-first-run',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--metrics-recording-only',
            '--js-flags="--max-old-space-size=512"'
        ]
    }
});

client.on('qr', (qr) => {
    console.log('\n[*] scan this qr code:');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('[+] session authenticated successfully!');
});

client.on('auth_failure', (msg) => {
    console.error('[-] authentication failure:', msg);
});

client.on('ready', async () => {
    console.log('\n[+] system online: whatsapp broadcast engine active.');
    console.log('[*] synchronizing chat cache to prevent lazy-load crashes...');
    try {
        await client.getChats();
        console.log('[+] cache synchronized. api is fully primed for broadcast.');
    } catch (err) {
        console.error('[-] minor cache sync error, proceeding anyway.');
    }
});

client.on('disconnected', (reason) => {
    console.error('[-] whatsapp engine disconnected:', reason);
    console.log('[*] commencing autonomous self-healing protocol...');
    
    client.destroy().then(() => {
        console.log('[+] client destroyed. forcing pm2 restart...');
        process.exit(1);
    }).catch((err) => {
        console.error('[-] failed to destroy client cleanly:', err);
        process.exit(1);
    });
});

client.on('message', async (msg) => {
    await handleMessage(client, msg);
});

app.post('/api/grades', async (req, res) => {
    const { chatId, message } = req.body;
    if (!chatId || !message) return res.status(400).json({ error: "invalid payload" });

    try {
        await client.sendMessage(chatId, message);
        console.log(`[+] broadcast dispatched to: ${chatId}`);
        res.status(200).json({ status: "success" });
    } catch (err) {
        console.error(`[-] broadcast failed:`, err);
        res.status(500).json({ error: err.toString().toLowerCase() });
    }
});

console.log('[*] attempting to launch puppeteer and initialize whatsapp...');
client.initialize();

app.listen(config.PORT, () => {
    console.log(`[*] local api listening on http://localhost:${config.PORT}`);
});

process.on('unhandledRejection', (error) => {
    console.error('[-] unhandled fatal rejection:', error.message ? error.message.toLowerCase() : error);
    // note: the string matching below must remain case-sensitive so puppeteer recognizes it
    if (error.message && (error.message.includes('Execution context was destroyed') || error.message.includes('Session closed'))) {
        console.log('[*] chromium renderer crashed. triggering pm2 reboot...');
        process.exit(1);
    }
});
