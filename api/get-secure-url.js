const crypto = require('crypto');
// We remove the otplib dependency completely to avoid versioning hell and crashes
// const { TOTP } = require('otplib'); 

// CONFIGURATION
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY || process.env.BUNNY_ACCESS_KEY;
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; 

// 1. Initialisation Client DB (Safe mode: Web/HTTP only)
let db = null;
try {
    const { createClient } = require('@libsql/client/web'); 
    
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

// ------ NATIVE TOTP IMPLEMENTATION (No Dependencies) ------
function base32ToBuffer(str) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let binary = '';
  // Remove padding if any
  str = str.replace(/=+$/, '');
  for (let i = 0; i < str.length; i++) {
    const val = alphabet.indexOf(str[i].toUpperCase());
    if (val === -1) continue;
    binary += val.toString(2).padStart(5, '0');
  }
  const len = Math.floor(binary.length / 8);
  const buf = Buffer.alloc(len);
  for (let i = 0; i < len; i++) {
    buf[i] = parseInt(binary.slice(i * 8, (i + 1) * 8), 2);
  }
  return buf;
}

function verifyTOTP(token, secret, window = 2) {
    if (!token || !secret) return false;
    try {
        const secretBuf = base32ToBuffer(secret);
        const time = Math.floor(Date.now() / 1000 / 30);
        
        // Window check (widened to +/- 1 minute)
        for (let i = -window; i <= window; i++) {
            const t = time + i;
            const counterBuf = Buffer.alloc(8);
            counterBuf.writeUInt32BE(0, 0); 
            counterBuf.writeUInt32BE(t, 4);

            const hmac = crypto.createHmac('sha1', secretBuf);
            hmac.update(counterBuf);
            const digest = hmac.digest();

            const offset = digest[digest.length - 1] & 0xf;
            const code = (
                ((digest[offset] & 0x7f) << 24) |
                ((digest[offset + 1] & 0xff) << 16) |
                ((digest[offset + 2] & 0xff) << 8) |
                (digest[offset + 3] & 0xff)
            ) % 1000000;

            const calculatedToken = code.toString().padStart(6, '0');
            if (calculatedToken === token) return true;
        }
        return false;
    } catch (e) {
        console.error("Native TOTP Check Error:", e.message);
        return false;
    }
}
// -----------------------------------------------------------

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
        let { code, videoId } = req.body;
        if (!code || !videoId) return res.status(400).json({ error: 'Missing code or videoId' });
        
        // Clean input (remove spaces, trim)
        code = String(code).replace(/\s+/g, '');

        const activeSecrets = await getActiveSecrets();
        console.log(`Vérification de ${activeSecrets.length} clés pour le code ${code}...`);

        let authorized = false;

        for (const entry of activeSecrets) {
            try {
                // Use robust native check
                if (verifyTOTP(code, entry.secret)) {
                    authorized = true;
                    console.log(`Accès autorisé via clé ${entry.type}`);
                    break; 
                }
            } catch (err) {
                 console.log(`Invalid secret ignored for ${entry.type}:`, err.message);
            }
        }

        if (!authorized) {
             console.log("Accès refusé: Aucun secret ne correspond au code " + code);
             return res.status(403).json({ error: 'Code invalide ou expiré' });
        }

        let signingKey = process.env.BUNNY_TOKEN_KEY;
        let keySource = "BUNNY_TOKEN_KEY";

        if (!signingKey) {
            signingKey = process.env.BUNNY_ACCESS_KEY; 
            keySource = "BUNNY_ACCESS_KEY (Fallback - Is this the Token Key or API Key?)";
        }
        
        if (!signingKey) {
            console.error("Missing Security Key (BUNNY_TOKEN_KEY)");
            return res.status(500).json({ error: 'Server Config Error: Missing BUNNY_TOKEN_KEY' });
        }

        // CLEAN THE KEY (Crucial! Remove spaces that copy-paste might add)
        signingKey = signingKey.trim();

        // LOGGING FOR DEBUG (Safe - only first 4 chars)
        console.log(`Signing with [${keySource}]: ${signingKey.substring(0, 4)}... (Length: ${signingKey.length})`);

        const signedUrl = signBunnyUrl(videoId, signingKey);
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
