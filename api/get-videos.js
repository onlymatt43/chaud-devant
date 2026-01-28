export default async function handler(req, res) {
  // Config (Idéalement dans les variables d'environnement Vercel)
  // Valeurs par défaut tirées de config.default.json (Public)
  const libraryId = process.env.BUNNY_LIBRARY_ID || '581630';
  const accessKey = process.env.BUNNY_ACCESS_KEY || '7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27';
  const pullZone = process.env.BUNNY_PULL_ZONE || 'https://vz-72668a20-6b9.b-cdn.net';

  try {
    const response = await fetch(
      `https://video.bunnycdn.com/library/${libraryId}/videos?itemsPerPage=1000&orderBy=date`,
      {
        method: 'GET',
        headers: { AccessKey: accessKey, accept: 'application/json' }
      }
    );

    if (!response.ok) throw new Error('Erreur API Bunny');
    
    const data = await response.json();
    const projects = {};

    // On regroupe les vidéos par projet selon leur titre : "NomDuProjet (Format)"
    data.items.forEach(v => {
      // Ex: "solo-basement-talk (9x16)" -> id: "solo-basement-talk", format: "9x16"
      // Si le titre ne contient pas de format entre parenthèses, on assume que c'est du 16x9 ou un raw
      const match = v.title.match(/^(.*) \((.*)\)$/);
      
      let id = v.title;
      let format = '16x9'; // Défaut si pas détecté

      if (match) {
        id = match[1];
        format = match[2];
      }

      if (!projects[id]) {
        projects[id] = {
          id: id,
          updated_at: v.dateCreated,
          bunny_urls: {}
        };
      }
      
      // Construction de l'URL MP4 directe pour la balise <video>
      // Format: hhtps://{pullZone}/{guid}/play_720p.mp4
      projects[id].bunny_urls[format] = `${pullZone}/${v.guid}/play_720p.mp4`;
      
      // On garde la date la plus récente du groupe
      if (new Date(v.dateCreated) > new Date(projects[id].updated_at)) {
        projects[id].updated_at = v.dateCreated;
      }
    });

    // Conversion de l'objet en liste triée (plus récent en premier)
    const videosList = Object.values(projects).sort((a, b) => 
      new Date(b.updated_at) - new Date(a.updated_at)
    );

    res.status(200).json(videosList);
  } catch (error) {
    console.error('Erreur:', error);
    res.status(500).json({ error: error.message });
  }
}
