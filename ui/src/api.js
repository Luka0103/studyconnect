
export const fetchWithToken = async (url, options = {}) => {
 
  const accessToken = localStorage.getItem('access_token');

  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers, 
  };


  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      error: 'Failed to parse error response from server',
    }));

    throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
  }


  return response.json();
};
