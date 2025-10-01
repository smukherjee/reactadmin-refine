import { apiService } from '../services/api';

export interface ApiTestResult {
  endpoint: string;
  success: boolean;
  error?: string;
  data?: any;
  statusCode?: number;
}

export class ApiTester {
  private results: ApiTestResult[] = [];

  private async testEndpoint(
    name: string,
    testFn: () => Promise<any>
  ): Promise<ApiTestResult> {
    try {
      const data = await testFn();
      const result = {
        endpoint: name,
        success: true,
        data,
      };
      this.results.push(result);
      return result;
    } catch (error: any) {
      const result = {
        endpoint: name,
        success: false,
        error: error.message || 'Unknown error',
        statusCode: error.response?.status,
      };
      this.results.push(result);
      return result;
    }
  }

  async runBasicTests(): Promise<ApiTestResult[]> {
    console.log('🧪 Running API Integration Tests...');
    this.results = [];

    // Test health endpoint
    await this.testEndpoint('Health Check', () => apiService.healthCheck());

    // Test authentication (if user is logged in)
    const token = localStorage.getItem('access_token');
    if (token) {
      console.log('✅ User is authenticated, testing authenticated endpoints...');

      // Test user endpoints
      try {
        await this.testEndpoint('Current User', () => apiService.getCurrentUser());
      } catch (error) {
        console.log('❌ Current user test failed');
      }

      // Test list endpoints (these require tenant)
      const tenantId = localStorage.getItem('current_tenant_id');
      if (tenantId) {
        console.log(`✅ Tenant available (${tenantId}), testing tenant-aware endpoints...`);

        await this.testEndpoint('Users List', () =>
          apiService.getList('users', { page: 1, size: 5 })
        );

        await this.testEndpoint('Roles List', () =>
          apiService.getList('roles', { page: 1, size: 5 })
        );

        await this.testEndpoint('Audit Logs List', () =>
          apiService.getList('audit-logs', { page: 1, size: 5 })
        );
      } else {
        console.log('⚠️ No tenant selected, skipping tenant-aware endpoints');
        this.results.push({
          endpoint: 'Tenant-aware endpoints',
          success: false,
          error: 'No tenant selected',
        });
      }
    } else {
      console.log('⚠️ User not authenticated, skipping authenticated tests');
      this.results.push({
        endpoint: 'Authenticated endpoints',
        success: false,
        error: 'User not authenticated',
      });
    }

    return this.results;
  }

  getResults(): ApiTestResult[] {
    return this.results;
  }

  getSummary() {
    const total = this.results.length;
    const successful = this.results.filter(r => r.success).length;
    const failed = total - successful;

    return {
      total,
      successful,
      failed,
      successRate: total > 0 ? (successful / total) * 100 : 0,
    };
  }

  printResults() {
    console.log('\n📊 API Test Results:');
    console.log('==================');

    this.results.forEach(result => {
      const status = result.success ? '✅' : '❌';
      const statusCode = result.statusCode ? ` [${result.statusCode}]` : '';
      console.log(`${status} ${result.endpoint}${statusCode}`);
      
      if (!result.success && result.error) {
        console.log(`   └─ Error: ${result.error}`);
      }
    });

    const summary = this.getSummary();
    console.log('\n📈 Summary:');
    console.log(`   Total tests: ${summary.total}`);
    console.log(`   Successful: ${summary.successful}`);
    console.log(`   Failed: ${summary.failed}`);
    console.log(`   Success rate: ${summary.successRate.toFixed(1)}%`);
  }
}

export const runApiTests = async (): Promise<ApiTestResult[]> => {
  const tester = new ApiTester();
  const results = await tester.runBasicTests();
  tester.printResults();
  return results;
};

export default ApiTester;