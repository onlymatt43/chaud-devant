const crypto = require('crypto');
const { authenticator } = require('otplib');

// Defensive require for @libsql/client
let createClient;
try {
    const libsql = require('@libsql/client');
    createClient = libsql.createClient;
    console.log("@libsql/client loaded successfully");
} catch (e) {
    console.warn("Optional dependency @libsql/client not found or failed to load:", e.message);
}

// CONFIGURATION
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY || process.env.BUNNY_ACCESS_KEY;
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; 

// CONNEXION TURSO (Optimisé pour Serverless HTTP)
let db = null;

function getDb() {
    if (db) return db;
    // Si createClient n'a pas pu être chargé, on abandonne l'initialisation DB
    if (!createClient) {
        console.warn("Skipping DB init because createClient is undefined");
        return null;
    }

    if (process.env.TURSO_DB_URL && process.env.TURSO_DB_TOKEN) {
        try {
            const url = process.env.TURSO_DB_URL.replace('libsql://', 'https://');
            console.log("Initializing Turso Client with URL:", url);
            
            db = createClient({
                url: url,
                authToken: process.env.TURSO_DB_TOKEN,
            });
        } catch (e) {
            console.error("Failed to initialize Turso client:", e);
        }
    } else {
        console.warn("Skipping DB init: Missing Environment Variables");
    }
    return db;
}

async function getActiveSecrets() {
    const secrets = [];
    
    // 1. Toujours ajouter la clé maître (fallback/admin)
    if (MASTER_TOTP_KEY) secrets.push({ type: 'MASTER', secret: MASTER_TOTP_KEY });

    // 2. Fetch depuis Turso si connecté
    const client = getDb();
    if (client) {
        try {
            const result = await client.execute("SELECT totp_secret FROM users WHERE active = 1");
            result.rows.forEach(row => {
                const secret = row.totp_secret; 
                if(secret) secrets.push({ type: 'USER', secret: String(secret) });
            });
        } catch (e) {
            console.warn("Erreur lecture DB Turso (Fallback sur Master Key uniquement):", e.message);
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

        // Config otplib
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
