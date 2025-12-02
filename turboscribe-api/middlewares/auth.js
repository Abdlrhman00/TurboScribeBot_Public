function apiKeyAuth(req, res, next) {
  // Get API keys from environment (comma-separated)
  const validKeys = new Set(
    (process.env.API_KEYS).split(',')
  );

  const apiKey = req.headers['x-api-key'] || 
                 req.headers['authorization'] || 
                 req.query.apiKey;

  if (!apiKey) {
    return res.status(401).json({
      error: 'API key required',
      message: 'Provide API key via: x-api-key header, Authorization header, or apiKey query parameter'
    });
  }

  // Extract key from "Bearer {key}" format
  const key = apiKey.startsWith('Bearer ') ? apiKey.slice(7) : apiKey;
  
  if (!validKeys.has(key)) {
    return res.status(403).json({
      error: 'Invalid API key',
      message: 'The provided API key is not valid'
    });
  }

  // Add user/request tracking if needed
  req.apiKey = key;
  next();
}

module.exports = { apiKeyAuth };