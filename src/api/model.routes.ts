import express, { Request, Response } from 'express';
import { config } from '../config';

const router = express.Router();

// GET /api/models - List available models
router.get('/models', (req: Response, res: Response) => {
  const models = Object.entries(config.models).map(([provider, modelConfig]) => ({
    provider,
    default: modelConfig.default,
    alternatives: modelConfig.alternatives,
  }));
  
  res.json({ models });
});

// GET /api/models/:provider - List models for specific provider
router.get('/models/:provider', (req: Response, res: Response) => {
  const { provider } = req.params;
  const modelConfig = config.models[provider as keyof typeof config.models];
  
  if (!modelConfig) {
    return res.status(404).json({ error: 'Provider not found' });
  }
  
  res.json({
    provider,
    default: modelConfig.default,
    alternatives: modelConfig.alternatives,
  });
});

export default router;
