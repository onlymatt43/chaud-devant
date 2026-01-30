const crypto = require('crypto');
const { authenticator } = require('otplib');

// CONFIGURATION
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY || process.env.BUNNY_ACCESS_KEY;
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; 

// 1. Initialisation Client DB (Safe mode: Web/HTTP only)
// On utilise l'import 'web' pour éviter les crashs de modules natifs sur Vercel
let db = null;
try {
    const { createClient } = require('@libsql/client/web'); // <-- CHANGEMENT CLÉ ICI
    
    if (process.env.TURSO_DB_URL && process.env.TURSO_DB_TOKEN) {
        const url = process.env.TURSO_DB_URL.replace('libsql://', 'https://');
        console.log("Initializing Turso Web Client with URL:", url);
        
        db = createClient({
            url: url,
            authToken: process.env.TURSO_DB_TOKEN,
        });
    }
} catch (error) {
    console.warn("Could not load @libsql/client/web:", error.message);
}

async function getActiveSecrets() {
    const secrets = [];
    
    // Toujours ajouter la clé maître
    if (MASTER_TOTP_KEY) secrets.push({ type: 'MASTER', secret: MASTER_TOTP_KEY });

    // Fetch DB
    if (db) {
        try {
            const result = await db.execute("SELECT totp_secret FROM users WHERE active = 1");
            result.rows.forEach(row => {
                const secret = row.totp_secret; 
                if(secret) secrets.push({ type: 'USER', secret: String(secret) });
            });
        } catch (e) {
            console.error("DB Read Error:", e.message);
        }
    }
    return secrets;
}

function signBunnyUrl(videoId, securityKey) {
    try {
        const expires = Math.floor(Date.now() / 1000) + 3600; // +1 heure
        const path = `/${videoId}/play_720p.mp4`; 
        const toSign = securityKey + path + expires;
        const signature = crypto.createHash('sha256').update(toSign).digest('hex');
        const baseUrl = process.env.BUNNY_PRIVATE_PULL_ZONE || "https://vz-c69f4e3f-963.b-cdn.net"; 
        return `${baseUrl}${path}?token=${signature}&expires=${expires}`;
    } catch(e) {
        console.error("Scaling/Signing error:", e);
        throw e;
    }
}

module.exports = async (req, res) => {
    // 1. CORS
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (req.method === 'OPTIONS') { res.status(200).end(); return; }
    if (req.method !== 'POST') { return res.status(405).json({ error: 'Method not allowed' }); }

    try {
        const { code, videoId } = req.body;
        if (!code || !videoId) return res.status(400).json({ error: 'Missing code or videoId' });

        // Force reload secrets on each request (Serverless context)
        const activeSecrets = await getActiveSecrets();
        console.log(`Vérification de ${activeSecrets.length} clés pour le code ${code}...`);

        let authorized = false;

        // Config otplib (On utilise l'instance importée directement)
        authenticator.options = { window: 1 }; // +/- 30s
        
        for (const entry of activeSecrets) {
            try {
                if (authenticator.check(code, entry.secret)) {
                    authorized = true;
                    console.log(`Accès autorisé via clé ${entry.type}`);
                    break; 
                }
            } catch (err) {
                // Ignore invalid secrets
                 console.log(`Invalid secret ignored for ${entry.type}`);
            }
        }

        if (!authorized) {
             console.log("Accès refusé: Aucun secret ne correspond au code " + code);
             return res.status(403).json({ error: 'Code invalide ou expiré' });
        }

        // 4. GENERATION DU PASS
        if (!BUNNY_PRIVATE_KEY) {
            console.error("Missing BUNNY_PRIVATE_KEY Env Var");
            return res.status(500).json({ error: 'Server misconfigured: Missing Video Key' });
        }

        const signedUrl = signBunnyUrl(videoId, BUNNY_PRIVATE_KEY);
        console.log("URL signée générée avec succès");

        return res.status(200).json({ success: true, url: signedUrl });

    } catch (error) {
        console.error("API CRASH:", error);
        return res.status(500).json({ 
            error: 'Internal Server Error', 
            details: error.message
        });
    }
};
