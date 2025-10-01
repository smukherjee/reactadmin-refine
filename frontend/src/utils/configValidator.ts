export interface ConfigValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  config: Record<string, any>;
}

export class ConfigValidator {
  private errors: string[] = [];
  private warnings: string[] = [];
  private config: Record<string, any> = {};

  validate(): ConfigValidationResult {
    this.errors = [];
    this.warnings = [];
    this.config = {};

    // Validate environment variables
    this.validateEnvironment();

    // Validate API configuration
    this.validateApiConfig();

    // Validate authentication setup
    this.validateAuthConfig();

    // Validate tenant configuration
    this.validateTenantConfig();

    return {
      isValid: this.errors.length === 0,
      errors: this.errors,
      warnings: this.warnings,
      config: this.config,
    };
  }

  private validateEnvironment() {
    console.log('🔍 Validating environment configuration...');

    // Required environment variables
    const requiredEnvVars = [
      'VITE_API_URL',
      'VITE_BACKEND_URL',
    ];

    const optionalEnvVars = [
      'VITE_DEBUG_MODE',
      'VITE_APP_TITLE',
    ];

    // Check required variables
    requiredEnvVars.forEach(varName => {
      const value = import.meta.env[varName];
      this.config[varName] = value;

      if (!value) {
        this.errors.push(`Missing required environment variable: ${varName}`);
      } else {
        console.log(`✅ ${varName} = ${value}`);
      }
    });

    // Check optional variables
    optionalEnvVars.forEach(varName => {
      const value = import.meta.env[varName];
      this.config[varName] = value;

      if (value) {
        console.log(`✅ ${varName} = ${value}`);
      } else {
        this.warnings.push(`Optional environment variable not set: ${varName}`);
      }
    });

    // Validate URLs
    const apiUrl = import.meta.env.VITE_API_URL;
    const backendUrl = import.meta.env.VITE_BACKEND_URL;

    if (apiUrl && !apiUrl.startsWith('/') && !apiUrl.startsWith('http')) {
      this.warnings.push('VITE_API_URL should start with / or http(s)://');
    }

    if (backendUrl && !backendUrl.startsWith('http')) {
      this.errors.push('VITE_BACKEND_URL must start with http:// or https://');
    }
  }

  private validateApiConfig() {
    console.log('🔍 Validating API configuration...');

    const apiUrl = import.meta.env.VITE_API_URL || '/api/v2';
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

    this.config.apiUrl = apiUrl;
    this.config.backendUrl = backendUrl;
    this.config.fullApiUrl = apiUrl.startsWith('http') ? apiUrl : `${backendUrl}${apiUrl}`;

    console.log(`✅ API URL: ${apiUrl}`);
    console.log(`✅ Backend URL: ${backendUrl}`);
    console.log(`✅ Full API URL: ${this.config.fullApiUrl}`);

    // Check for potential CORS issues
    if (window.location.origin !== backendUrl && !apiUrl.startsWith('/')) {
      this.warnings.push('Potential CORS issue: API URL is absolute but different from current origin');
    }
  }

  private validateAuthConfig() {
    console.log('🔍 Validating authentication configuration...');

    const token = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const user = localStorage.getItem('user');
    const sessionId = localStorage.getItem('session_id');

    this.config.auth = {
      hasAccessToken: !!token,
      hasRefreshToken: !!refreshToken,
      hasUser: !!user,
      hasSessionId: !!sessionId,
    };

    if (token) {
      console.log('✅ Access token found');
      
      // Check token expiry (basic check)
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000;
        const now = Date.now();
        
        if (exp < now) {
          this.warnings.push('Access token appears to be expired');
        } else {
          console.log(`✅ Token expires: ${new Date(exp).toLocaleString()}`);
        }
      } catch (error) {
        this.warnings.push('Could not parse access token');
      }
    } else {
      console.log('⚠️ No access token found');
    }

    if (refreshToken) {
      console.log('✅ Refresh token found');
    } else {
      console.log('⚠️ No refresh token found');
    }

    if (user) {
      try {
        const userObj = JSON.parse(user);
        console.log(`✅ User: ${userObj.email || userObj.username}`);
        this.config.user = {
          email: userObj.email,
          username: userObj.username,
          isActive: userObj.is_active,
          isSuperuser: userObj.is_superuser,
        };
      } catch (error) {
        this.errors.push('Invalid user data in localStorage');
      }
    }
  }

  private validateTenantConfig() {
    console.log('🔍 Validating tenant configuration...');

    const tenantId = localStorage.getItem('current_tenant_id');
    const user = localStorage.getItem('user');

    this.config.tenant = {
      currentTenantId: tenantId,
      hasTenant: !!tenantId,
    };

    if (tenantId) {
      console.log(`✅ Current tenant: ${tenantId}`);
    } else {
      this.warnings.push('No current tenant selected - some features may not work');
    }

    if (user) {
      try {
        const userObj = JSON.parse(user);
        const availableTenants = userObj.available_tenants || [];
        const currentTenant = userObj.current_tenant;

        this.config.tenant.availableTenants = availableTenants.length;
        this.config.tenant.currentTenant = currentTenant;

        console.log(`✅ Available tenants: ${availableTenants.length}`);
        
        if (currentTenant) {
          console.log(`✅ Current tenant: ${currentTenant.name} (${currentTenant.id})`);
        }

        if (availableTenants.length === 0) {
          this.warnings.push('User has no available tenants');
        }
      } catch (error) {
        this.warnings.push('Could not parse tenant information from user data');
      }
    }
  }

  printValidationReport() {
    console.log('\n📋 Configuration Validation Report');
    console.log('================================');

    if (this.errors.length > 0) {
      console.log('\n❌ ERRORS:');
      this.errors.forEach(error => console.log(`   • ${error}`));
    }

    if (this.warnings.length > 0) {
      console.log('\n⚠️ WARNINGS:');
      this.warnings.forEach(warning => console.log(`   • ${warning}`));
    }

    if (this.errors.length === 0 && this.warnings.length === 0) {
      console.log('\n✅ All configuration checks passed!');
    }

    console.log('\n📊 Configuration Summary:');
    console.log('========================');
    console.log(JSON.stringify(this.config, null, 2));
  }
}

export const validateConfiguration = (): ConfigValidationResult => {
  const validator = new ConfigValidator();
  const result = validator.validate();
  validator.printValidationReport();
  return result;
};

export default ConfigValidator;