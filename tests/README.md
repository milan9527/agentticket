# Test Scripts for Ticket Auto-Processing System

This directory contains comprehensive test scripts that can be run directly by command to validate the entire system deployment and functionality.

## Quick Start

### Deploy Frontend (Task 10)
```bash
# Deploy frontend to S3 + CloudFront with Origin Access Control
python tests/run_frontend_deployment.py

# Or run individual steps:
python tests/deploy_frontend_s3_cloudfront.py  # Deploy
python tests/test_frontend_deployment.py       # Test deployment
```

### Run Complete System Tests
```bash
# Test entire system
python tests/test_complete_system.py

# Test specific components
python tests/test_complete_system.py database
python tests/test_complete_system.py agents
python tests/test_complete_system.py frontend
```

## Available Test Scripts

### 🚀 Deployment Scripts

#### `deploy_frontend_s3_cloudfront.py`
**Purpose**: Complete frontend deployment to AWS S3 + CloudFront
- **Task 10.1**: Configure S3 bucket for static hosting (private access)
- **Task 10.2**: Set up CloudFront distribution with Origin Access Control
- **Task 10.3**: Deploy React application to S3

**Usage**:
```bash
python tests/deploy_frontend_s3_cloudfront.py
```

**Requirements**:
- AWS CLI configured with appropriate permissions
- `.env` file with AWS configuration (run `infrastructure/setup_aws.py` first)
- Frontend built or will be built automatically

**Output**:
- Creates `deployment_info.json` with deployment details
- Deploys frontend with secure CloudFront + S3 setup
- No public S3 access (security requirement met)

#### `run_frontend_deployment.py`
**Purpose**: Simple interface for frontend deployment and testing

**Usage**:
```bash
python tests/run_frontend_deployment.py [action]

# Actions:
python tests/run_frontend_deployment.py deploy    # Deploy only
python tests/run_frontend_deployment.py test     # Test existing deployment
python tests/run_frontend_deployment.py both     # Deploy and test
```

### 🧪 Test Scripts

#### `test_frontend_deployment.py`
**Purpose**: Validate frontend deployment security and functionality

**Tests**:
- ✅ S3 bucket security (public access blocked)
- ✅ CloudFront distribution configuration
- ✅ Origin Access Control (OAC) setup
- ✅ Frontend accessibility via HTTPS
- ✅ SPA routing (404 → index.html)
- ✅ Performance and caching

**Usage**:
```bash
python tests/test_frontend_deployment.py
```

**Requirements**:
- `deployment_info.json` (created by deployment script)

#### `test_complete_system.py`
**Purpose**: Comprehensive system test suite

**Test Components**:
- 🏗️ **Infrastructure**: AWS resources validation
- 🗄️ **Database**: Schema and connectivity tests
- 🤖 **Agents**: AgentCore agents and MCP communication
- 🔌 **API**: Backend Lambda functions and API Gateway
- 🌐 **Frontend**: Deployment and accessibility
- 🔄 **Integration**: End-to-end workflows

**Usage**:
```bash
# Run all tests
python tests/test_complete_system.py

# Run specific component tests
python tests/test_complete_system.py infrastructure
python tests/test_complete_system.py database
python tests/test_complete_system.py agents
python tests/test_complete_system.py api
python tests/test_complete_system.py frontend
python tests/test_complete_system.py integration
```

**Output**:
- Detailed console output with test results
- `system_test_report.json` with comprehensive results

## Test Dependencies

### Required Files
- `.env` - AWS configuration (created by `infrastructure/setup_aws.py`)
- `deployment_info.json` - Frontend deployment info (created by deployment script)

### Required AWS Permissions
The test scripts require AWS credentials with permissions for:
- S3 (bucket operations, object upload/download)
- CloudFront (distribution management, cache invalidation)
- RDS Data API (database operations)
- Secrets Manager (credential access)
- AgentCore (agent operations)

### Python Dependencies
```bash
pip install boto3 requests
```

## Security Features Tested

### S3 Security
- ✅ Public access completely blocked
- ✅ Bucket policy allows only CloudFront service principal
- ✅ Direct S3 access returns 403 Forbidden
- ✅ Origin Access Control (OAC) configured

### CloudFront Security
- ✅ HTTPS redirect enforced
- ✅ Origin Access Control prevents direct S3 access
- ✅ Custom error pages for SPA routing
- ✅ Proper cache headers and compression

## Troubleshooting

### Common Issues

#### "deployment_info.json not found"
**Solution**: Run the deployment script first:
```bash
python tests/deploy_frontend_s3_cloudfront.py
```

#### "AWS credentials not configured"
**Solution**: Configure AWS CLI or set environment variables:
```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

#### "Frontend build failed"
**Solution**: Ensure Node.js and npm are installed, then:
```bash
cd frontend
npm install
npm run build
```

#### "CloudFront distribution still deploying"
**Note**: CloudFront distributions take 10-15 minutes to fully deploy globally. The tests will indicate if the distribution is still deploying.

### Test Timeouts
- Individual tests have a 5-minute timeout
- CloudFront operations may take longer during initial deployment
- Re-run tests after CloudFront deployment completes

## Integration with Task List

These scripts directly implement and validate:

- ✅ **Task 10.1**: S3 bucket configuration (`deploy_frontend_s3_cloudfront.py`)
- ✅ **Task 10.2**: CloudFront distribution setup (`deploy_frontend_s3_cloudfront.py`)
- ✅ **Task 10.3**: React application deployment (`deploy_frontend_s3_cloudfront.py`)
- ✅ **Task 11**: Integration testing (`test_complete_system.py`)
- ✅ **Task 12**: Final system validation (`test_complete_system.py`)

## Output Files

### `deployment_info.json`
Contains deployment details:
```json
{
  "bucket_name": "ticket-system-frontend-123456789",
  "distribution_id": "E1234567890ABC",
  "domain_name": "d1234567890abc.cloudfront.net",
  "oac_id": "E1234567890DEF",
  "frontend_url": "https://d1234567890abc.cloudfront.net"
}
```

### `system_test_report.json`
Contains comprehensive test results with statistics and detailed logs.

## Next Steps After Deployment

1. **Verify deployment**: Run `python tests/test_frontend_deployment.py`
2. **Test complete system**: Run `python tests/test_complete_system.py`
3. **Access frontend**: Use the URL from `deployment_info.json`
4. **Monitor**: Check CloudWatch logs for any issues
5. **Update DNS**: Point your domain to the CloudFront distribution (optional)

## Support

For issues with the test scripts:
1. Check the console output for specific error messages
2. Review the generated JSON reports for detailed information
3. Ensure all prerequisites are met (AWS credentials, .env file, etc.)
4. Verify AWS service limits and permissions