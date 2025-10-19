/**
 * Form Filler Module
 * Handles detection and filling of LinkedIn job application forms
 */

export class FormFiller {
  constructor(page, userProfile) {
    this.page = page;
    this.userProfile = userProfile;
  }

  /**
   * Detect all form fields on the current page
   */
  async detectFormFields() {
    console.log('Detecting form fields...');
    
    const fields = {
      textInputs: [],
      textAreas: [],
      dropdowns: [],
      checkboxes: [],
      radioButtons: [],
      fileUploads: []
    };

    try {
      // Detect text inputs
      fields.textInputs = await this.page.locator('input[type="text"], input[type="email"], input[type="tel"]').all();
      
      // Detect text areas
      fields.textAreas = await this.page.locator('textarea').all();
      
      // Detect dropdowns
      fields.dropdowns = await this.page.locator('select').all();
      
      // Detect checkboxes
      fields.checkboxes = await this.page.locator('input[type="checkbox"]').all();
      
      // Detect radio buttons
      fields.radioButtons = await this.page.locator('input[type="radio"]').all();
      
      // Detect file uploads
      fields.fileUploads = await this.page.locator('input[type="file"]').all();
      
      console.log(`Found ${fields.textInputs.length} text inputs`);
      console.log(`Found ${fields.textAreas.length} text areas`);
      console.log(`Found ${fields.dropdowns.length} dropdowns`);
      console.log(`Found ${fields.checkboxes.length} checkboxes`);
      console.log(`Found ${fields.radioButtons.length} radio buttons`);
      console.log(`Found ${fields.fileUploads.length} file upload fields`);
      
      return fields;
    } catch (error) {
      console.error('Error detecting form fields:', error.message);
      return fields;
    }
  }

  /**
   * Auto-fill all detected form fields with user profile data
   */
  async autoFillForm() {
    console.log('Starting auto-fill process...');
    
    try {
      // Fill common LinkedIn Easy Apply fields
      await this.fillPhoneNumber();
      await this.delay(300);
      
      await this.fillLocation();
      await this.delay(300);
      
      await this.fillYearsOfExperience();
      await this.delay(300);
      
      await this.handleDropdowns();
      await this.delay(300);
      
      await this.fillTextAreas();
      await this.delay(300);
      
      console.log('✓ Auto-fill completed');
      return true;
    } catch (error) {
      console.error('Auto-fill error:', error.message);
      return false;
    }
  }

  /**
   * Fill phone number field
   */
  async fillPhoneNumber() {
    try {
      const phoneField = this.page.locator('input[id*="phoneNumber"], input[name*="phone"]').first();
      const isVisible = await phoneField.isVisible({ timeout: 1000 }).catch(() => false);
      
      if (isVisible) {
        await phoneField.fill(this.userProfile.personalInfo.phone);
        console.log('✓ Filled phone number');
      }
    } catch (error) {
      // Field might not exist on this page
      console.log('- Phone number field not found (may not be required)');
    }
  }

  /**
   * Fill location/city field
   */
  async fillLocation() {
    try {
      const locationField = this.page.locator('input[id*="city"], input[name*="location"]').first();
      const isVisible = await locationField.isVisible({ timeout: 1000 }).catch(() => false);
      
      if (isVisible) {
        const location = `${this.userProfile.personalInfo.location.city}, ${this.userProfile.personalInfo.location.state}`;
        await locationField.fill(location);
        console.log('✓ Filled location');
      }
    } catch (error) {
      console.log('- Location field not found (may not be required)');
    }
  }

  /**
   * Fill years of experience field
   */
  async fillYearsOfExperience() {
    try {
      const experienceField = this.page.locator('input[id*="experience"], input[name*="years"]').first();
      const isVisible = await experienceField.isVisible({ timeout: 1000 }).catch(() => false);
      
      if (isVisible) {
        await experienceField.fill(this.userProfile.preferences.yearsOfExperience.toString());
        console.log('✓ Filled years of experience');
      }
    } catch (error) {
      console.log('- Years of experience field not found (may not be required)');
    }
  }

  /**
   * Handle dropdown selections
   */
  async handleDropdowns() {
    try {
      const dropdowns = await this.page.locator('select').all();
      
      for (const dropdown of dropdowns) {
        const isVisible = await dropdown.isVisible({ timeout: 1000 }).catch(() => false);
        if (!isVisible) continue;
        
        const id = await dropdown.getAttribute('id');
        const name = await dropdown.getAttribute('name');
        
        // Handle specific dropdowns based on common patterns
        if (id?.includes('visa') || name?.includes('visa')) {
          await this.handleVisaDropdown(dropdown);
        } else if (id?.includes('experience') || name?.includes('experience')) {
          await this.handleExperienceDropdown(dropdown);
        }
      }
    } catch (error) {
      console.log('Error handling dropdowns:', error.message);
    }
  }

  /**
   * Handle visa sponsorship dropdown
   */
  async handleVisaDropdown(dropdown) {
    try {
      const requiresSponsorship = this.userProfile.preferences.requiresSponsorship;
      const value = requiresSponsorship ? 'Yes' : 'No';
      
      await dropdown.selectOption({ label: value });
      console.log(`✓ Selected visa sponsorship: ${value}`);
    } catch (error) {
      console.log('Could not set visa dropdown');
    }
  }

  /**
   * Handle experience level dropdown
   */
  async handleExperienceDropdown(dropdown) {
    try {
      const years = this.userProfile.preferences.yearsOfExperience;
      
      // Map years to common experience levels
      let level = 'Entry level';
      if (years >= 8) level = 'Director';
      else if (years >= 5) level = 'Senior';
      else if (years >= 2) level = 'Mid-Senior level';
      
      await dropdown.selectOption({ label: level });
      console.log(`✓ Selected experience level: ${level}`);
    } catch (error) {
      console.log('Could not set experience dropdown');
    }
  }

  /**
   * Fill text area fields (like "Why do you want to work here?")
   */
  async fillTextAreas() {
    try {
      const textAreas = await this.page.locator('textarea').all();
      
      for (const textArea of textAreas) {
        const isVisible = await textArea.isVisible({ timeout: 1000 }).catch(() => false);
        if (!isVisible) continue;
        
        const label = await this.getFieldLabel(textArea);
        
        // Use common answers from profile if available
        if (label?.toLowerCase().includes('why')) {
          await textArea.fill(this.userProfile.commonAnswers.whyThisCompany);
          console.log('✓ Filled "why this company" field');
        } else if (label?.toLowerCase().includes('strength')) {
          await textArea.fill(this.userProfile.commonAnswers.greatestStrength);
          console.log('✓ Filled "greatest strength" field');
        }
      }
    } catch (error) {
      console.log('Error filling text areas:', error.message);
    }
  }

  /**
   * Upload resume/documents
   */
  async uploadResume() {
    try {
      console.log('Looking for file upload field...');
      
      const fileInput = this.page.locator('input[type="file"]').first();
      const isVisible = await fileInput.isVisible({ timeout: 5000 }).catch(() => false);
      
      if (isVisible) {
        const resumePath = this.userProfile.documents.resume;
        
        // Convert relative path to absolute
        const absolutePath = resumePath.startsWith('.') 
          ? process.cwd() + '/' + resumePath.substring(2)
          : resumePath;
        
        await fileInput.setInputFiles(absolutePath);
        console.log('✓ Resume uploaded');
        
        // Wait for upload to complete
        await this.delay(2000);
        
        return true;
      } else {
        console.log('- No file upload field found (may not be required)');
        return false;
      }
    } catch (error) {
      console.error('Error uploading resume:', error.message);
      return false;
    }
  }

  /**
   * Get label text for a form field
   */
  async getFieldLabel(element) {
    try {
      const id = await element.getAttribute('id');
      if (id) {
        const label = await this.page.locator(`label[for="${id}"]`).textContent();
        return label;
      }
      
      // Try to find label by proximity
      const parentLabel = await element.locator('xpath=ancestor::label').textContent().catch(() => null);
      return parentLabel;
    } catch (error) {
      return null;
    }
  }

  /**
   * Click "Next" or "Review" button to proceed to next step
   */
  async clickNext() {
    try {
      // Look for common next button patterns
      const nextButton = this.page.locator('button:has-text("Next"), button:has-text("Review"), button:has-text("Continue")').first();
      
      const isVisible = await nextButton.isVisible({ timeout: 3000 }).catch(() => false);
      
      if (isVisible) {
        await nextButton.click();
        console.log('✓ Clicked Next button');
        await this.delay(2000);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error clicking next:', error.message);
      return false;
    }
  }

  /**
   * Submit the application
   */
  async submitApplication() {
    try {
      console.log('Looking for Submit button...');
      
      const submitButton = this.page.locator('button:has-text("Submit application"), button:has-text("Submit")').first();
      
      const isVisible = await submitButton.isVisible({ timeout: 3000 }).catch(() => false);
      
      if (isVisible) {
        await submitButton.click();
        console.log('✓ Application submitted!');
        
        // Wait for confirmation
        await this.delay(3000);
        
        return true;
      } else {
        console.log('⚠️  Submit button not found');
        return false;
      }
    } catch (error) {
      console.error('Error submitting application:', error.message);
      return false;
    }
  }

  /**
   * Check if we're on a multi-step form and detect current step
   */
  async detectFormStep() {
    try {
      // LinkedIn Easy Apply often shows progress like "1 of 3"
      const progressText = await this.page.locator('[class*="artdeco-modal__header"]').textContent().catch(() => '');
      
      if (progressText.includes('of')) {
        const match = progressText.match(/(\d+)\s*of\s*(\d+)/);
        if (match) {
          return {
            current: parseInt(match[1]),
            total: parseInt(match[2])
          };
        }
      }
      
      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Utility: Add delay
   */
  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
