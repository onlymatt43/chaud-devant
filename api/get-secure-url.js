const crypto = require('crypto');
// Pour tester sans base de données utilisateurs complexes, 
// on va utiliser une Clé Maître temporaire pour la démo.
// Dans le futur, cette clé devra venir d'une base de données liée à l'utilisateur.
const MASTER_TOTP_KEY = process.env.TOTP_SECRET_KEY || "JBSWY3DPEHPK3PXP"; // Exemple de clé Google Auth par défaut
const BUNNY_PRIVATE_KEY = process.env.BUNNY_TOKEN_KEY; // La clé Bunny (à mettre dans Vercel ENV)

// Fonction simple TOTP (Time-based One-Time Password)
// Implémentation minimaliste compatible Google Authenticator sans grosse librairie
function getTOTP(secret) {
    const key = Buffer.from(base32tohex(secret), 'hex');
    const epoch = Math.round(new Date().getTime() / 1000.0);
    const time = Buffer.alloc(8);
    // Google Auth utilise des steps de 30 secondes
    let counter = Math.floor(epoch / 30);
    
    // Write Big Endian 64bit integer
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
}

function base32tohex(base32) {
    const base32chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    let bits = "";
    let hex = "";
    for (let i = 0; i < base32.length; i++) {
        const val = base32chars.indexOf(base32.charAt(i).toUpperCase());
        bits += val.toString(2).padStart(5, '0');
    }
    for (let i = 0; i + 4 <= bits.length; i += 4) {
        const chunk = bits.substr(i, 4);
        hex = hex + parseInt(chunk, 2).toString(16);
    }
    return hex;
}

// Fonction signature Bunny
function signBunnyUrl(videoId, securityKey) {
    const expires = Math.floor(Date.now() / 1000) + 3600; // +1 heure
    const path = `/${videoId}/playlist.m3u8`; // HLS Playlist
    const toSign = securityKey + path + expires;
    const signature = crypto.createHash('sha256').update(toSign).digest('hex');
    const baseUrl = "https://vz-c69f4e3f-963.b-cdn.net"; // Private Zone
    return `${baseUrl}${path}?token=${signature}&expires=${expires}`;
}

module.exports = async (req, res) => {
    // 1. CORS
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    try {
        const { code, videoId } = req.body;
        
        if (!code || !videoId) {
            return res.status(400).json({ error: 'Missing code or videoId' });
        }

        // 2. VERIFICATION DU CODE (Le Videur)
        // On calcule le code valide MAINTENANT
        // On accepte aussi le code précédent et suivant pour la souplesse (dérive d'horloge)
        const currentCode = getTOTP(MASTER_TOTP_KEY);
        
        console.log(`Serveur attend: ${currentCode} | Reçu: ${code}`);

        // Note: Pour une vraie prod, vérifier +/- 1 step (30s)
        if (code !== currentCode) {
             return res.status(403).json({ error: 'Code incorrect ou expiré' });
        }

        // 3. GENERATION DU PASS (La Signature)
        if (!BUNNY_PRIVATE_KEY) {
            // Si pas configuré sur Vercel, on ne peut pas signer
            return res.status(500).json({ error: 'Server misconfigured (Missing Bunny Key)' });
        }

        const signedUrl = signBunnyUrl(videoId, BUNNY_PRIVATE_KEY);

        // 4. LIVRAISON
        return res.status(200).json({ 
            success: true, 
            url: signedUrl 
        });

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: 'Internal Server Error' });
    }
};
