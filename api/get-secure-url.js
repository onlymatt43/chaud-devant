const crypto = require('crypto');
const { createClient } = require('@libsql/client');
const { authenticator } = require('otplib');

// CONFIGURATION
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY;
// Fallback sur la clé maître si la DB n'est pas configurée
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; 

// CONNEXION TURSO (Optimisé pour Serverless HTTP)
let db = null;
if (process.env.TURSO_DB_URL && process.env.TURSO_DB_TOKEN) {
    // Force HTTP pour Vercel pour éviter les soucis de WebSocket
    const url = process.env.TURSO_DB_URL.replace('libsql://', 'https://');
    
    db = createClient({
        url: url,
        authToken: process.env.TURSO_DB_TOKEN,
        intMode: 'bigint' // Prévention erreur 400
    });
}

// Fonction pour récupérer les secrets actifs depuis Turso
async function getActiveSecrets() {
    const secrets = [];
    
    // 1. Toujours ajouter la clé maître (fallback/admin)
    if (MASTER_TOTP_KEY) secrets.push({ type: 'MASTER', secret: MASTER_TOTP_KEY });

    // 2. Fetch depuis Turso si connecté
    if (db) {
        try {
            // On suppose une table 'users' avec une colonne 'totp_secret'
            const result = await db.execute("SELECT totp_secret FROM users WHERE active = 1");
            result.rows.forEach(row => {
                // Gestion des types retournés par intMode: bigint
                const secret = row.totp_secret; 
                if(secret) secrets.push({ type: 'USER', secret: String(secret) });
            });
        } catch (e) {
            console.error("Erreur lecture DB Turso (Vercel):", e);
        }
    }
    return secrets;
}

// Fonction signature Bunny
function signBunnyUrl(videoId, securityKey) {
    const expires = Math.floor(Date.now() / 1000) + 3600; // +1 heure
    const path = `/${videoId}/play_720p.mp4`; 
    const toSign = securityKey + path + expires;
    const signature = crypto.createHash('sha256').update(toSign).digest('hex');
    const baseUrl = process.env.BUNNY_PRIVATE_PULL_ZONE || "https://vz-c69f4e3f-963.b-cdn.net"; 
    return `${baseUrl}${path}?token=${signature}&expires=${expires}`;
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

        // 2. RECUPERATION DES CLÉS
        const activeSecrets = await getActiveSecrets();
        console.log(`Vérification de ${activeSecrets.length} clés pour le code ${code}...`);

        let authorized = false;

        // 3. CHECK (otplib gère la fenêtre de temps et la crypto correctement)
        authenticator.options = { window: 1 }; // Tolérance +/- 30s
        
        for (const entry of activeSecrets) {
            try {
                // Vérifie le token avec otplib
                const isValid = authenticator.check(code, entry.secret);
                
                if (isValid) {
                    authorized = true;
                    console.log(`Accès autorisé via clé ${entry.type}`);
                    break; 
                }
            } catch (err) {
                console.warn(`Erreur vérif secret ${entry.type}:`, err.message);
            }
        }

        if (!authorized) {
             return res.status(403).json({ error: 'Code invalide ou expiré' });
        }

        // 4. GENERATION DU PASS
        if (!BUNNY_PRIVATE_KEY) return res.status(500).json({ error: 'Server misconfigured' });

        const signedUrl = signBunnyUrl(videoId, BUNNY_PRIVATE_KEY);

        return res.status(200).json({ success: true, url: signedUrl });

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: 'Internal Server Error' });
    }
};
