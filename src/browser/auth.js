/**
 * LinkedIn Authentication Module
 * Handles login and session management
 */

import { config } from 'dotenv';
config();

export class LinkedInAuth {
  constructor(page) {
    this.page = page;
    this.isAuthenticated = false;
  }

  /**
   * Navigate to LinkedIn login page
   */
  async navigateToLogin() {
    console.log('Navigating to LinkedIn login page...');
    await this.page.goto('https://www.linkedin.com/login', {
      waitUntil: 'networkidle'
    });
  }

  /**
   * Perform login with credentials
   * @param {string} email - LinkedIn email
   * @param {string} password - LinkedIn password
   */
  async login(email, password) {
    try {
      console.log('Starting login process...');
      
      // Navigate to login page
      await this.navigateToLogin();
      
      // Wait for login form to be visible
      await this.page.waitForSelector('#username', { timeout: 10000 });
      
      // Fill in email
      console.log('Filling email...');
      await this.page.fill('#username', email);
      
      // Small delay to mimic human behavior
      await this.delay(500);
      
      // Fill in password
      console.log('Filling password...');
      await this.page.fill('#password', password);
      
      // Small delay before clicking
      await this.delay(500);
      
      // Click sign in button
      console.log('Clicking sign in button...');
      await this.page.click('button[type="submit"]');
      
      // Wait for navigation after login
      await this.page.waitForLoadState('networkidle', { timeout: 15000 });
      
      // Check if login was successful
      await this.verifyLogin();
      
      console.log('Login successful!');
      this.isAuthenticated = true;
      
      return true;
    } catch (error) {
      console.error('Login failed:', error.message);
      
      // Check for common error scenarios
      await this.handleLoginErrors();
      
      this.isAuthenticated = false;
      return false;
    }
  }

  /**
   * Verify if login was successful
   */
  async verifyLogin() {
    const currentUrl = this.page.url();
    
    // If we're still on the login page, login failed
    if (currentUrl.includes('/login')) {
      throw new Error('Still on login page - credentials may be incorrect');
    }
    
    // If we see the feed or checkpoint, login was successful
    if (currentUrl.includes('/feed') || currentUrl.includes('/checkpoint')) {
      return true;
    }
    
    // Additional verification: check for navigation bar
    const hasNavBar = await this.page.locator('nav.global-nav').count() > 0;
    if (!hasNavBar) {
      throw new Error('Login verification failed - expected elements not found');
    }
    
    return true;
  }

  /**
   * Handle common login errors
   */
  async handleLoginErrors() {
    // Check for "wrong password" error
    const errorMessage = await this.page.locator('.alert-content').textContent().catch(() => '');
    
    if (errorMessage.includes('password')) {
      console.error('❌ Incorrect password');
    } else if (errorMessage.includes('email')) {
      console.error('❌ Email not found');
    }
    
    // Check if 2FA is required
    const has2FA = await this.page.locator('input[id*="verification"]').count() > 0;
    if (has2FA) {
      console.log('⚠️  2FA detected - manual intervention required');
      console.log('Please complete the 2FA challenge in the browser window');
      
      // Wait for user to complete 2FA (up to 2 minutes)
      await this.page.waitForURL(/linkedin\.com\/(feed|mynetwork)/, { 
        timeout: 120000 
      }).catch(() => {
        console.log('2FA timeout - please try again');
      });
    }
    
    // Check for CAPTCHA
    const hasCaptcha = await this.page.locator('iframe[title*="recaptcha"]').count() > 0;
    if (hasCaptcha) {
      console.log('⚠️  CAPTCHA detected - manual intervention required');
      console.log('Please complete the CAPTCHA in the browser window');
      
      // Wait for user to complete CAPTCHA
      await this.delay(30000); // Wait 30 seconds for manual CAPTCHA completion
    }
  }

  /**
   * Check if currently authenticated
   */
  async checkAuth() {
    try {
      const currentUrl = this.page.url();
      
      // If we're on LinkedIn and not on login page, likely authenticated
      if (currentUrl.includes('linkedin.com') && !currentUrl.includes('/login')) {
        this.isAuthenticated = true;
        return true;
      }
      
      this.isAuthenticated = false;
      return false;
    } catch (error) {
      this.isAuthenticated = false;
      return false;
    }
  }

  /**
   * Logout from LinkedIn
   */
  async logout() {
    try {
      console.log('Logging out...');
      
      // Navigate to logout URL
      await this.page.goto('https://www.linkedin.com/m/logout');
      
      await this.delay(2000);
      
      this.isAuthenticated = false;
      console.log('Logged out successfully');
      
      return true;
    } catch (error) {
      console.error('Logout failed:', error.message);
      return false;
    }
  }

  /**
   * Utility: Add delay to mimic human behavior
   */
  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
