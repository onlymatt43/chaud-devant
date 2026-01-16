export default async function handler(req, res) {
  const libraryId = process.env.BUNNY_LIBRARY_ID;
  const accessKey = process.env.BUNNY_ACCESS_KEY;

  if (!libraryId || !accessKey) {
    return res.status(500).json({ error: 'Config Bunny manquante sur Vercel' });
  }

  try {
    const response = await fetch(
      `https://video.bunnycdn.com/library/${libraryId}/videos?itemsPerPage=50&orderBy=date`,
      {
        method: 'GET',
        headers: {
          AccessKey: accessKey,
          accept: 'application/json',
        }
      }
    );

    if (!response.ok) throw new Error('Erreur API Bunny');
    
    const data = await response.json();

    // On transforme les données de Bunny pour notre interface
    const videos = data.items.map(v => ({
      id: v.title,
      guid: v.guid,
      updated_at: v.dateCreated,
      width: v.width,
      height: v.height,
      url: `https://iframe.mediadelivery.net/play/${libraryId}/${v.guid}`
    }));

    res.status(200).json(videos);
  } catch (error) {
    console.error('Erreur:', error);
    res.status(500).json({ error: error.message });
  }
}
