
export const fetchWithToken = async (url, options = {}) => {
  // Holen Sie den Access-Token aus dem localStorage (oder wo auch immer Sie ihn speichern)
  const accessToken = localStorage.getItem('access_token');

  // Bereiten Sie die Header vor
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers, // Erlaubt das Überschreiben von Headern
  };

  // Fügen Sie den Authorization-Header hinzu, falls ein Token vorhanden ist
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Behandeln Sie HTTP-Fehler
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      error: 'Failed to parse error response from server',
    }));
    // Werfen Sie einen Fehler, damit er von der aufrufenden Funktion im catch-Block behandelt werden kann
    throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
  }

  // Geben Sie die JSON-Antwort zurück
  return response.json();
};
