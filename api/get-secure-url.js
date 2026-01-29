const crypto = require('crypto');
const { createClient } = require('@libsql/client');

// CONFIGURATION
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY;
// Fallback sur la clé maître si la DB n'est pas configurée
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; 

// CONNEXION TURSO (Si les vars existent)
let db = null;
if (process.env.TURSO_DB_URL && process.env.TURSO_DB_TOKEN) {
    db = createClient({
        url: process.env.TURSO_DB_URL,
        authToken: process.env.TURSO_DB_TOKEN,
    });
}

// ... (Fonctions TOTP inchangées) ...
function getTOTP(secret) {
    try {
        const key = Buffer.from(base32tohex(secret), 'hex');
        const epoch = Math.round(new Date().getTime() / 1000.0);
        const time = Buffer.alloc(8);
        let counter = Math.floor(epoch / 30);
        
        time.writeUInt32BE(0, 0);
        time.writeUInt32BE(counter, 4);

        const hmac = crypto.createHmac('sha1', key);
        hmac.update(time);
        const h = hmac.digest();

        const offset = h[h.length - 1] & 0xf;
        const v = (h[offset] & 0x7f) << 24 |
                (h[offset + 1] & 0xff) << 16 |
                (h[offset + 2] & 0xff) << 8 |
                (h[offset + 3] & 0xff);

        let code = (v % 1000000).toString();
        return code.padStart(6, '0');
    } catch (e) {
        console.error("Erreur calcul TOTP pour secret:", secret, e);
        return "000000";
    }
}

function base32tohex(base32) {
    const base32chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    let bits = "";
    let hex = "";
    // Clean string
    base32 = base32.replace(/=/g, "").toUpperCase();
    
    for (let i = 0; i < base32.length; i++) {
        const val = base32chars.indexOf(base32.charAt(i));
        if (val === -1) throw new Error("Invalid Base32 character: " + base32.charAt(i));
        bits += val.toString(2).padStart(5, '0');
    }
    for (let i = 0; i + 4 <= bits.length; i += 4) {
        const chunk = bits.substr(i, 4);
        hex = hex + parseInt(chunk, 2).toString(16);
    }
    return hex;
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
                if(row.totp_secret) secrets.push({ type: 'USER', secret: row.totp_secret });
            });
        } catch (e) {
            console.error("Erreur lecture DB Turso:", e);
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

        // 3. BRUTEFORCE CHECK (On cherche "QUI" a généré ce code)
        // Pour < 1000 users, c'est instantané.
        for (const entry of activeSecrets) {
            const validCode = getTOTP(entry.secret);
            
            // TODO: Ajouter vérification +/- 30s pour tolérance
            if (code === validCode) {
                authorized = true;
                console.log(`Accès autorisé via clé ${entry.type}`);
                break; // Trouvé !
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
