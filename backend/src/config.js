// src/config.js
const required = ['GEMINI_API_KEY', 'TASK_API_BASE_URL', 'CANDIDATE_ID'];

for (const key of required) {
  if (!process.env[key]) {
    console.error(`FATAL: Missing required environment variable: ${key}`);
    process.exit(1);
  }
}

export const config = {
  geminiApiKey: process.env.GEMINI_API_KEY,
  taskApiBase: process.env.TASK_API_BASE_URL.replace(/\/$/, ''),
  candidateId: process.env.CANDIDATE_ID.toLowerCase().trim(),
  port: parseInt(process.env.PORT || '3001', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
};

// Guard: candidate_id must look like an email
if (!config.candidateId.includes('@')) {
  console.error('FATAL: CANDIDATE_ID must be a valid email address');
  process.exit(1);
}
