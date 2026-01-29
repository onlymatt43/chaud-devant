// CONFIGURATION (à migrer dans Vercel ENV idéalement)
const PUBLIC = {
  id: process.env.BUNNY_LIBRARY_ID || '581630',
  key: process.env.BUNNY_ACCESS_KEY || '7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27',
  pull: process.env.BUNNY_PULL_ZONE || 'https://vz-72668a20-6b9.b-cdn.net'
};

const PRIVATE = {
  id: process.env.BUNNY_PRIVATE_LIBRARY_ID || '552081',
  key: process.env.BUNNY_PRIVATE_ACCESS_KEY || '202d4df5-5617-4738-9c82a7cae508-e3c5-48ef',
  pull: process.env.BUNNY_PRIVATE_PULL_ZONE || 'https://vz-c69f4e3f-963.b-cdn.net'
};

// Fonction helper pour récupérer une librairie
async function fetchLibrary(config, isPrivate = false) {
  try {
    const response = await fetch(
      `https://video.bunnycdn.com/library/${config.id}/videos?itemsPerPage=1000&orderBy=date`,
      {
        method: 'GET',
        headers: { AccessKey: config.key, accept: 'application/json' }
      }
    );

    if (!response.ok) {
      console.error(`Erreur fetch library ${config.id}: ${response.status}`);
      return []; 
    }

    const data = await response.json();
    return data.items.map(item => ({ ...item, _isPrivate: isPrivate, _pull: config.pull }));
  } catch (e) {
    console.error(`Exception fetch library ${config.id}:`, e);
    return [];
  }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');

  try {
    // 1. Fetch Parallèle
    const [publicItems, privateItems] = await Promise.all([
      fetchLibrary(PUBLIC, false),
      fetchLibrary(PRIVATE, true)
    ]);

    const allItems = [...publicItems, ...privateItems];
    const projects = {};

    // 2. Groupement et Parsing
    allItems.forEach(v => {
      // Ex: "solo-basement-talk (9x16)" -> id: "solo-basement-talk", format: "9x16"
      const match = v.title.match(/^(.*) \((.*)\)$/);
      
      let id = v.title;
      let format = '16x9';

      if (match) {
        id = match[1];
        format = match[2];
      }

      if (!projects[id]) {
        projects[id] = {
          id: id,
          updated_at: v.dateCreated,
          bunny_urls: {},
          guids: {}, // Stocke les GUID pour la signature
          thumbnails: {},
          locked: false
        };
      }
      
      const videoUrl = `${v._pull}/${v.guid}/play_720p.mp4`;
      projects[id].bunny_urls[format] = videoUrl;
      projects[id].guids[format] = v.guid;
      projects[id].thumbnails[format] = `${v._pull}/${v.guid}/${v.thumbnailFileName || 'thumbnail.jpg'}`;

      if (v._isPrivate) {
        projects[id].locked = true;
      }
      
      if (new Date(v.dateCreated) > new Date(projects[id].updated_at)) {
        projects[id].updated_at = v.dateCreated;
      }
    });

    const videosList = Object.values(projects).sort((a, b) => 
      new Date(b.updated_at) - new Date(a.updated_at)
    );

    res.status(200).json(videosList);
  } catch (error) {
    console.error('Erreur:', error);
    res.status(500).json({ error: error.message });
  }
}
