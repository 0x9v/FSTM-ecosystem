const { GEMINI_API_KEY } = require('./config');

async function fetchGeminiResponse(userText) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key=${GEMINI_API_KEY}`;

    const systemPrompt = `You are a highly intelligent, direct AI assistant in a WhatsApp group for FSTM engineering students. 
CRITICAL RULES:
1. NEVER use LaTeX (like \\int, $x$, \\[ \\]). Write all math in plain text (e.g., "x^2", "integral from 0 to 1").
2. NEVER use Markdown headers (#, ##).
3. ONLY use WhatsApp supported markdown: *bold*, _italic_, ~strikethrough~, and \`\`\`code\`\`\`.
4. Keep answers concise, structured, and easy to read on a phone.`;

    const payload = {
        system_instruction: {
            parts: [{ text: systemPrompt }]
        },
        contents: [{
            parts: [{ text: userText }]
        }]
    };

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    
    if (data.candidates && data.candidates.length > 0) {
        return data.candidates[0].content.parts[0].text;
    } else {
        console.error('[-] Gemini API Response Error:', data);
        throw new Error("Invalid API response");
    }
}

module.exports = { fetchGeminiResponse };
