/**
 * API service for UNIfy Flask backend integration
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export interface StudentProfile {
  mental_health: string;
  physical_health: string;
  courses: string;
  gpa: number;
  severity: 'mild' | 'moderate' | 'severe';
}

export interface University {
  name: string;
  score: number;
  accessibility_rating: number;
  disability_support_rating: number;
  available_accommodations: string[];
  location: string;
  reason: string;
}

export interface RecommendationResponse {
  success: boolean;
  source: string;
  needed_accommodations: string[];
  recommendations: University[];
  error?: {
    code: string;
    message: string;
  };
}

/**
 * Get university recommendations from the Flask API
 */
export async function getRecommendations(profile: StudentProfile): Promise<RecommendationResponse> {
  try {
    console.log('API Base URL:', API_BASE_URL);
    console.log('Sending profile:', profile);

    const response = await fetch(`${API_BASE_URL}/api/recommendations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * Test the API connection
 */
export async function testAPI(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/test`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Test Error:', error);
    throw error;
  }
}

/**
 * Get recommendations directly from Gemini AI
 */
export async function getGeminiRecommendations(profile: StudentProfile): Promise<RecommendationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/gemini`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Gemini API Error:', error);
    throw error;
  }
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Health Check Error:', error);
    throw error;
  }
}


// TODO:
// need to figure out how to run python script in node env
// fetch and parse response into export interface RecommendationResponse data type 
// fix front end in Recommendations.tsx to format and parse this new data response.


// All the necessary gemini api code is in gemini_api.py

// pages/api/run-script.ts (Next.js API Route)
import { NextApiRequest, NextApiResponse } from 'next';
import path from 'path';
import { runPythonScript } from '../../lib/python-runner';

export async function gemini_handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method Not Allowed' });
  }

  try {
    const profile: StudentProfile = req.body;

    const result = await call_gemini_api(profile);

    res.status(200).json(result);
  } catch (error: any) {
    console.error('Gemini Handler Error:', error);
    res.status(500).json({ success: false, message: error.message });
  }
}

async function call_gemini_api(profile: StudentProfile): Promise<RecommendationResponse> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python3', ['gemini_api.py']);

    const inputData = JSON.stringify(profile);

    let data = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (chunk) => {
      data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
      errorData += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python script failed with code ${code}. Error: ${errorData}`));
        return;
      }
      try {
        const result: RecommendationResponse = JSON.parse(data);
        resolve(result);
      } catch (e) {
        reject(new Error(`Failed to parse JSON from Python: ${data}`));
      }
    });

    pythonProcess.stdin.write(inputData);
    pythonProcess.stdin.end();
  });
}








export async function gemini_handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method Not Allowed' });
  }

  try {
    const { num1, num2 } = req.body;
    
    // Define the path to the Python script
    const scriptPath = path.join(process.cwd(), 'scripts', 'script.py');
    
    // Run the script with input data
    const result = await call_gemini_api(scriptPath, { num1, num2 });

    // Return the result from Python
    res.status(200).json(result);
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
}



import { spawn } from 'child_process';

export async function call_gemini_api(profile: StudentProfile): Promise<any> {
  return new Promise((resolve, reject) => {
    // TODO: Does this work?
    const pythonProcess = spawn('python3', ['gemini_api.py']); // Use 'python' or 'python3' as appropriate
    
    // Data to send to Python
    const inputData = JSON.stringify({
      mental_health: profile.mental_health,
      physical_health: profile.physical_health,
      courses: profile.courses,
      gpa: profile.gpa,
      severity: profile.severity,
    });

    let data = '';
    let errorData = '';

    //  Capture output from Python (stdout)
    pythonProcess.stdout.on('data', (chunk) => {
      data += chunk.toString();
    });

    // Capture errors from Python (stderr)
    pythonProcess.stderr.on('data', (chunk) => {
      errorData += chunk.toString();
    });

    // Handle process exit
    pythonProcess.on('close', (code: number) => {
      if (code !== 0) {
      // Reject if the Python script failed
      reject(new Error(`Python script failed with code ${code}. Error: ${errorData}`));
      return;
      }
      try {
      // Parse and resolve the JSON output
      const result: RecommendationResponse = JSON.parse(data);
      resolve(result);
      } catch (e) {
      reject(new Error(`Failed to parse JSON from Python: ${data}`));
      }
    });

    // 5. Send input data to Python (stdin)
    pythonProcess.stdin.write(inputData);
    pythonProcess.stdin.end();
  });
}

// Recommendations.source
// recommandations.needed_accommodations
// recommandations.recommendations
// Is a map 
