require('dotenv').config();
const { createClient } = require('@libsql/client');
const qrcode = require('qrcode-terminal'); 
const crypto = require('crypto');

// Config Turso
const url = process.env.TURSO_DB_URL ? process.env.TURSO_DB_URL.replace('libsql://', 'https://') : null;
const authToken = process.env.TURSO_DB_TOKEN;

if (!url || !authToken) { console.error("❌ Manque .env (TURSO_DB_URL/TOKEN)"); process.exit(1); }

// Force l'utilisation du protocole 'https' simple sans gestion de session complexe
const db = createClient({ 
    url: url.replace('libsql://', 'https://'), 
    authToken,
    // Désactive les fonctionnalités "intelligentes" qui causent l'erreur 400
    intMode: 'bigint' 
});

// --- FONCTIONS UTILITAIRES SANS LIBRAIRIE EXTERNE ---

// Génère un secret Base32 aléatoire (RFC 4648)
function generateBase32Secret(length = 20) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    const randomBytes = crypto.randomBytes(length);
    let secret = '';
    
    // Conversion simple byte -> char (suffisant pour secret)
    for (let i = 0; i < length; i++) {
        const index = randomBytes[i] % 32;
        secret += chars[index];
    }
    return secret;
}

async function main() {
    const email = process.argv[2] || "admin@chaud-devant.com"; 
    const note = process.argv[3] || "Admin Key";

    console.log(`👤 Création utilisateur : ${email} (${note})`);

    // 1. Générer Secret
    const secret = generateBase32Secret(20); // 20 chars = 100 bits entropy, standard Google Auth
    
    try {
        // 2. Insert DB
        await db.execute({
            sql: "INSERT INTO users (email, totp_secret, active) VALUES (?, ?, 1)",
            args: [email, secret]
        });

        console.log("✅ Utilisateur ajouté en base !");
        console.log("---------------------------------------------------");
        console.log(`🔑 SECRET: ${secret}`);
        console.log("---------------------------------------------------");

        // 3. Afficher QR Code
        // Format: otpauth://totp/Issuer:Account?secret=SECRET&issuer=Issuer
        const issuer = "Chaud-Devant";
        const account = encodeURIComponent(email);
        const uri = `otpauth://totp/${issuer}:${account}?secret=${secret}&issuer=${issuer}`;
        
        qrcode.generate(uri, { small: true }, function (qrcode) {
            console.log(qrcode);
        });

        console.log("\n📲 Scannez ce code avec Google Authenticator ou Authy !");

    } catch (e) {
        console.error("❌ Erreur SQL:", e);
    }
}

main();
