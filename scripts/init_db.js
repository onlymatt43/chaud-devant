require('dotenv').config();
const { createClient } = require('@libsql/client');

const url = process.env.TURSO_DB_URL;
const authToken = process.env.TURSO_DB_TOKEN;

if (!url || !authToken) {
  console.error("❌ ERREUR: TURSO_DB_URL ou TURSO_DB_TOKEN manquant dans le fichier .env");
  process.exit(1);
}

// Nettoyage de l'URL pour éviter les erreurs communes
// On force le mode libsql:// si possible ou https://
const finalUrl = url.includes('turso.io') && !url.startsWith('libsql') ? url.replace('https://', 'libsql://') : url;
console.log(`Target URL: ${finalUrl}`);

const db = createClient({ 
    url: finalUrl, 
    authToken 
});

async function main() {
  console.log("🔌 Connexion à Turso...");
  
  try {
    // Test simple de connexion
    await db.execute("SELECT 1");
    console.log("✅ Connexion réussie !");

    console.log("🛠  Création de la table 'users'...");
    
    await db.execute(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        totp_secret TEXT NOT NULL,
        payhip_license_key TEXT UNIQUE,
        active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    console.log("✅ Table 'users' prête (ou déjà existante) !");
    
    // Vérification
    const result = await db.execute("SELECT count(*) as count FROM users");
    console.log(`📊 Nombre d'utilisateurs actuels : ${result.rows[0].count}`);

  } catch (e) {
    console.error("❌ Erreur:", e);
    // Si ca plante ici, c'est peut etre un probleme de protocole, on suggère une solution
    console.log("\n💡 SI VOUS AVEZ UNE ERREUR 400:");
    console.log("Essayez de lancer ce SQL directement dans votre console Turso (sur le site web) :");
    console.log(`
      CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        totp_secret TEXT NOT NULL,
        payhip_license_key TEXT UNIQUE,
        active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  }
}

main();
