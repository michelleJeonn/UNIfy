import { spawn } from 'child_process';

function call_gemini_api(a: number, b: number): Promise<any> {
  return new Promise((resolve, reject) => {
    // 1. Define the Python process
    const pythonProcess = spawn('python3', ['gemini_api.py']); // Use 'python' or 'python3' as appropriate
    
    // Data to send to Python
    const inputData = JSON.stringify({ a, b });

    let data = '';
    let errorData = '';

    // 2. Capture output from Python (stdout)
    pythonProcess.stdout.on('data', (chunk) => {
      data += chunk.toString();
    });

    // 3. Capture errors from Python (stderr)
    pythonProcess.stderr.on('data', (chunk) => {
      errorData += chunk.toString();
    });

    // 4. Handle process exit
    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        // Reject if the Python script failed
        reject(new Error(`Python script failed with code ${code}. Error: ${errorData}`));
        return;
      }
      try {
        // Parse and resolve the JSON output
        resolve(JSON.parse(data));
      } catch (e) {
        reject(new Error(`Failed to parse JSON from Python: ${data}`));
      }
    });

    // 5. Send input data to Python (stdin)
    pythonProcess.stdin.write(inputData);
    pythonProcess.stdin.end();
  });
}

// Example usage:
runPythonScript(5, 12)
  .then(result => {
    console.log("Result from Python:", result);
  })
  .catch(err => {
    console.error("Error running Python:", err.message);
  });