const fs = require('fs');
const { MessageMedia } = require('whatsapp-web.js');
const path = require('path');
const { exec } = require('child_process');
const { fetchGeminiResponse } = require('../gemini');
const config = require('../config');
const feedback_msg = "\n\n[*] enjoying the bot? drop a dm with your feedback or feature requests.";

const globalCooldowns = new Map();
const mutedGroups = new Set();
let isMaintenanceMode = false;

const customDbPath = path.join(__dirname, '../../custom_commands.json');
let customDb = {};

const loadCustomDb = () => {
    try {
        if (fs.existsSync(customDbPath)) {
            const rawData = fs.readFileSync(customDbPath, 'utf-8');
            customDb = JSON.parse(rawData);
            console.log(`[+] database hot-loaded into ram: ${Object.keys(customDb).length} commands active.`);
        }
    } catch (err) {
        console.error('[-] failed to parse custom_commands.json:', err.message.toLowerCase());
    }
};

loadCustomDb();

let fsWait = false;
fs.watch(customDbPath, (event, filename) => {
    if (filename && event === 'change') {
        if (fsWait) return;
        fsWait = true;
        setTimeout(() => { fsWait = false; }, 100); 
        console.log('[*] cli modification detected. hot-reloading database...');
        loadCustomDb();
    }
});

async function handleMessage(client, msg) {
    console.log(`\n[*] message from ${msg.from} | text: "${msg.body.toLowerCase()}"`);
    
    if (!msg.body) return; 
    
    const rawText = msg.body.toLowerCase();
    
    const chatId = msg.from; 
    const senderId = msg.author || msg.from; 
    const isAdmin = config.ADMIN_IDS.includes(senderId);
    
    const argsArray = msg.body.trim().split(/ +/);
    const command = argsArray.shift().toLowerCase();
    const argsText = argsArray.join(' '); 

    const sendDynamicReply = async (replyString) => {
        const tagMatch = replyString.match(/\[(img|sticker|audio|voice|file|video)\]/i);

        if (tagMatch) {
            const tag = tagMatch[1].toUpperCase();
            const tagFull = tagMatch[0];
            
            const parts = replyString.split(tagFull);
            const textPart = parts[0].trim().toLowerCase();
            let rawPath = parts[1].trim();
            let filePath;
            
            if (path.isAbsolute(rawPath)) {
                filePath = rawPath;
            } else {
                filePath = path.join(__dirname, '../../', rawPath);
            }

            try {
                if (textPart.length > 0) {
                    await msg.reply(textPart);
                }

                if (fs.existsSync(filePath)) {
                    const media = MessageMedia.fromFilePath(filePath);
                    
                    if (tag === 'STICKER') {
                        await client.sendMessage(msg.from, media, { sendMediaAsSticker: true, quotedMessageId: msg.id._serialized });
                    } else if (tag === 'VOICE') {
                        await client.sendMessage(msg.from, media, { sendAudioAsVoice: true, quotedMessageId: msg.id._serialized });
                    } else if (tag === 'IMG' || tag === 'AUDIO' || tag === 'FILE' || tag === 'VIDEO') {
                        await client.sendMessage(msg.from, media, { quotedMessageId: msg.id._serialized });
                    }
                    return; 
                } else {
                    console.error(`[-] file missing for tag [${tag.toLowerCase()}]: ${path.basename(filePath)}`);
                }
            } catch (err) {
                console.error(`[-] crash converting [${tag.toLowerCase()}] file '${path.basename(filePath)}' to sticker:`, err.message.toLowerCase());
                return; 
            }
        }
        
        await msg.reply(replyString.toLowerCase());
    };

    if (isMaintenanceMode && !isAdmin) {
        return;
    }

    if (!mutedGroups.has(chatId)) {
        for (const [trigger, replyText] of Object.entries(customDb)) {
            if (!trigger.startsWith('!')) {
                const regex = new RegExp(`\\b${trigger}\\b`, 'i');
                if (regex.test(rawText)) {
                    let finalReply = replyText;
                    if (Array.isArray(finalReply)) {
                        finalReply = finalReply[Math.floor(Math.random() * finalReply.length)];
                    }
                    await sendDynamicReply(finalReply);
                    return;
                }
            }
        }
    }

    if (!msg.body.startsWith('!')) return;

    if (isAdmin) {
        if (command === '!rgod' || command === '!3ya') {
            await msg.reply('[-] system offline\n\nthe server is entering hibernation. good night.');
            
            setTimeout(() => { 
                console.log('[*] initiating graceful shutdown...');
                client.destroy().then(() => {
                    exec('pm2 stop fstm-oracle'); 
                }).catch((err) => {
                    console.error('[-] failed to destroy client:', err);
                    exec('pm2 stop fstm-oracle');
                });
            }, 2500);
            
            return;
        }
        if (command === '!maint') {
            isMaintenanceMode = true;
            await msg.reply('[*] maintenance mode activated.');
            return;
        }
        if (command === '!online') {
            isMaintenanceMode = false;
            await msg.reply('[+] system online.\nnew words have been added, have fun.');
            return;
        }
        if (command === '!clear') {
            const clearPayload = "[*] clearing chat... please wait\nloading...\n███████▒▒▒ 70%\n" 
                                 + "ㅤ\n".repeat(50) 
                                 + "[+] chat cleared. fresh start.";
            await msg.reply(clearPayload);
            return;
        }

        if (command === '!tfa' ||  command === '!mreg' || command === '!hanina') {
            mutedGroups.add(chatId);
            await msg.reply('[*] serious mode activated.');

            const stickerPath = path.join(__dirname, '../../IMG/s9il.webp');
            try {
                if (fs.existsSync(stickerPath)) {
                    const media = MessageMedia.fromFilePath(stickerPath);
                    await client.sendMessage(msg.from, media, { sendMediaAsSticker: true });
                }
            } catch (err) {
                console.error("[-] failed to load combo sticker:", err);
            }
            return; 
        }
        
        if (command === '!ch3al' || command === '!fi9') {
            mutedGroups.delete(chatId);
            await msg.reply('[+] fun mode activated.');

            const stickerPath = path.join(__dirname, '../../IMG/fun.webp');
            try {
                if (fs.existsSync(stickerPath)) {
                    const media = MessageMedia.fromFilePath(stickerPath);
                    await client.sendMessage(msg.from, media, { sendMediaAsSticker: true });
                }
            } catch (err) {
                console.error("[-] failed to load fun sticker:", err);
            }
            return;
        }
        
        if (command === '!lock' || command === '!unlock') {
            const chat = await msg.getChat();
            if (chat.isGroup) {
                try {
                    await chat.setMessagesAdminsOnly(command === '!lock');
                    await msg.reply(command === '!lock' ? '[-] silence.' : '[+] break time.');
                } catch (err) {
                    await msg.reply('[-] error: insufficient admin rights.');
                }
            }
            return;
        }
    }

    if (!config.COOLDOWN_TIMES[command] && !customDb[command]) return;

    const lockKey = `${chatId}_${command}`; 
    if (!isAdmin && globalCooldowns.has(lockKey)) {
        const lastTime = globalCooldowns.get(lockKey);
        const cooldownLimit = config.COOLDOWN_TIMES[command] || 10000;
        if (Date.now() - lastTime < cooldownLimit) {
            return; 
        }
    }

    if (!isAdmin) {
        globalCooldowns.set(lockKey, Date.now());
        const cooldownLimit = config.COOLDOWN_TIMES[command] || 10000;
        setTimeout(() => {
            globalCooldowns.delete(lockKey);
        }, cooldownLimit);
    }

    if (command === '!emoonai') {
        if (!argsText) return msg.reply('[-] you forgot your question.');
        try {
            const aiResponse = await fetchGeminiResponse(argsText);
            await msg.reply(aiResponse.toLowerCase());
        } catch (err) {
            await msg.reply('[-] api error.');
        }
        return;
    }

    if (command === '!help') {
        await msg.reply(`[*] fstm oracle - menu\n\n !last : shows the last 3 modules.\n!today : shows today's modules.\n!uptime : server status.\n!help : this menu.` + feedback_msg);
        return;
    }

    if (command === '!uptime') {        
        const uptime = process.uptime();
        const hours = Math.floor(uptime / 3600);
        const minutes = Math.floor((uptime % 3600) / 60);
        await msg.reply(`[*] server status\n\n- online for : ${hours}h ${minutes}m\n- api bridge : connected [+]`);
        return;
    } 

    if (command === '!tmrw') {
        const jokes = [
            "[*] bro i am not a witch. wait until tomorrow like everyone else.",
            "[-] error 404: crystal ball not found.",
            "[*] everything will be fine.",
            "[*] watch me reply and find out you have retakes."
        ];
        await msg.reply(jokes[Math.floor(Math.random() * jokes.length)]);
        return;
    }

    if (command === '!today') {
        try {
            const filePath = path.join(__dirname, '../../recent_history.json');
            if (!fs.existsSync(filePath)) return msg.reply('[-] no new modules');
            
            const fileContent = await fs.promises.readFile(filePath, 'utf-8');
            const data = JSON.parse(fileContent);
            const now = new Date();
            const todayString = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}`;
            const todaysModules = data.filter(item => item.time && item.time.includes(todayString));
            if (todaysModules.length === 0) return msg.reply(`[-] no modules today.`);
            let text = `[*] modules displayed today\n\n`;
            todaysModules.reverse().forEach(item => { text += `[+] ${item.name} (${item.time})\n`; });
            await msg.reply(text + feedback_msg);
        } catch (err) {
            await msg.reply('[-] system error.');
        }
        return;
    }

    if (command === '!last') {
        try {
            const filePath = path.join(__dirname, '../../recent_history.json');
            if (!fs.existsSync(filePath)) return msg.reply('[-] no modules');
            
            const fileContent = await fs.promises.readFile(filePath, 'utf-8');
            const data = JSON.parse(fileContent);
            if (data.length === 0) return msg.reply('[-] no modules');
            const recent = data.slice(-3);
            let text = `[*] last added modules\n\n`;
            recent.reverse().forEach(item => { text += `[+] ${item.name} (${item.time})\n`; });
            await msg.reply(text + feedback_msg);
        } catch (err) {
            await msg.reply('[-] system error.');
        }
        return;
    }

    if (customDb[command]) {
        let finalReply = customDb[command];
        if (Array.isArray(finalReply)) {
            finalReply = finalReply[Math.floor(Math.random() * finalReply.length)];
        }
        await sendDynamicReply(finalReply);
        return;
    }

    if (command === '!ping') return msg.reply('[+] system online.');
    if (command === '!id') return msg.reply(`[*] chat id: ${msg.from}`);
}

module.exports = {
    handleMessage,
    mutedGroups,
    isMaintenanceMode
};
