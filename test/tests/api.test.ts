import { test, expect } from '@playwright/test';
import axios from 'axios';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import waitOn from 'wait-on';

const API_URL = 'http://localhost:5000/api/users';
let flaskProcess: ChildProcess | null = null;

async function startFlaskApp() {
  try {
    // Check if the app is already running
    try {
      await axios.get('http://localhost:5000');
      console.log('Flask app is already running');
      return;
    } catch {
      // App is not running, proceed to start it
      console.log('Starting Flask app...');
      
      // Get the path to the Python executable in the virtual environment
      const pythonPath = process.platform === 'win32' ? 
        path.resolve(__dirname, '../../.venv/Scripts/python.exe') : 
        path.resolve(__dirname, '../../.venv/bin/python');
      
      const apiPath = path.resolve(__dirname, '../../api.py');
      
      flaskProcess = spawn(pythonPath, [apiPath], {
        stdio: 'pipe',
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1'
        }
      });

      flaskProcess.stdout?.on('data', (data: Buffer) => {
        console.log(`Flask stdout: ${data.toString()}`);
      });

      flaskProcess.stderr?.on('data', (data: Buffer) => {
        console.error(`Flask stderr: ${data.toString()}`);
      });

      flaskProcess.on('exit', (code: number | null) => {
        if (code !== null && code !== 0) {
          console.error(`Flask process exited with code ${code}`);
        }
      });

      // Wait for the server to be ready
      await waitOn({
        resources: ['http://localhost:5000'],
        timeout: 30000, // 30 seconds timeout
        interval: 100,  // Check every 100ms
      });

      console.log('Flask app is ready');
    }
  } catch (error) {
    console.error('Error starting Flask app:', error);
    throw error;
  }
}

async function stopFlaskApp() {
  if (flaskProcess) {
    console.log('Stopping Flask app...');
    try {
      if (process.platform === 'win32') {
        // On Windows, we need to use taskkill to ensure child processes are terminated
        const taskkill = spawn('taskkill', ['/pid', flaskProcess.pid!.toString(), '/f', '/t']);
        await new Promise<void>((resolve) => {
          taskkill.on('close', () => {
            resolve();
          });
        });
      } else {
        flaskProcess.kill('SIGTERM');
        await new Promise<void>((resolve) => {
          flaskProcess!.on('exit', () => {
            resolve();
          });
        });
      }
    } catch (error) {
      console.error('Error stopping Flask app:', error);
    } finally {
      flaskProcess = null;
    }
  }
}

test.describe('User API Tests', () => {
  let userId: number;
  let testUsername: string;
  let testEmail: string;

  function generateRandomUser() {
    const timestamp = new Date().getTime();
    const random = Math.floor(Math.random() * 10000);
    return {
      username: `testuser_${timestamp}_${random}`,
      email: `testuser_${timestamp}_${random}@example.com`
    };
  }

  test.beforeAll(async () => {
    // Start the Flask app first
    await startFlaskApp();

    console.log('Setting up: Clearing existing data...');
    try {
      // Soft delete all existing users
      const response = await axios.get(API_URL);
      for (const user of response.data) {
        console.log(`Soft deleting user ${user.id}...`);
        await axios.delete(`${API_URL}/${user.id}`);
      }
      
      // Verify cleanup
      const afterDelete = await axios.get(API_URL);
      if (afterDelete.data.length === 0) {
        console.log('Database cleared successfully');
      } else {
        console.warn(`Warning: ${afterDelete.data.length} active users remain`);
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        console.log('No users to clean up');
      } else {
        console.error('Error during database cleanup:', error.message);
      }
    }
  });

  test.afterAll(async () => {
    await stopFlaskApp();
  });

  test('should create and manage users', async () => {
    // 1. Create a new user with random credentials
    const { username, email } = generateRandomUser();
    testUsername = username;
    testEmail = email;
    console.log(`Creating new user with username: ${username}, email: ${email}`);
    
    let response = await axios.post(API_URL, {
      username: testUsername,
      email: testEmail
    });
    
    expect(response.status).toBe(201);
    expect(Array.isArray(response.data)).toBeTruthy();
    expect(response.data[0]).toBeDefined();
    userId = response.data[0].id;
    console.log('Created user with ID:', userId);

    // 2. Get all users
    console.log('Getting all users...');
    response = await axios.get(API_URL);
    expect(response.status).toBe(200);
    expect(Array.isArray(response.data)).toBeTruthy();
    expect(response.data.length).toBeGreaterThan(0);
    console.log('Found users:', response.data.length);

    // 3. Get specific user
    console.log('Getting specific user:', userId);
    response = await axios.get(`${API_URL}/${userId}`);
    expect(response.status).toBe(200);
    expect(response.data.id).toBe(userId);
    expect(response.data.username).toBe(testUsername);
    expect(response.data.email).toBe(testEmail);
    console.log('Retrieved user:', response.data);

    // 4. Update user with new random credentials
    const { username: newUsername, email: newEmail } = generateRandomUser();
    console.log(`Updating user ${userId} with username: ${newUsername}, email: ${newEmail}`);
    response = await axios.put(`${API_URL}/${userId}`, {
      username: newUsername,
      email: newEmail
    });
    expect(response.status).toBe(200);
    expect(response.data.username).toBe(newUsername);
    expect(response.data.email).toBe(newEmail);
    console.log('Updated user:', response.data);

    // 5. Delete user
    console.log('Deleting user:', userId);
    response = await axios.delete(`${API_URL}/${userId}`);
    expect(response.status).toBe(204);

    // 6. Verify deletion
    response = await axios.get(API_URL);
    const deletedUser = response.data.find((user: any) => user.id === userId);
    expect(deletedUser).toBeUndefined();
    console.log('User successfully deleted');
  });

  test('should handle non-existent user', async () => {
    try {
      await axios.get(`${API_URL}/999999`);
      // If we get here, the test should fail because we expected a 404
      expect(false).toBe(true);
    } catch (error: any) {
      expect(error.response.status).toBe(404);
      expect(error.response.data.message).toBe('Could not find user with that id');
    }
  });

  test('should handle duplicate usernames and emails', async () => {
    // Create first user
    const { username, email } = generateRandomUser();
    let response = await axios.post(API_URL, {
      username,
      email
    });
    expect(response.status).toBe(201);
    
    // Try to create another user with same username and email
    try {
      await axios.post(API_URL, {
        username,
        email
      });
      expect(false).toBe(true); // Should not reach here
    } catch (error: any) {
      expect(error.response.status).toBe(400);
      expect(error.response.data.message).toContain('already exists');
    }

    // Clean up
    const userId = response.data[0].id;
    await axios.delete(`${API_URL}/${userId}`);
  });
});