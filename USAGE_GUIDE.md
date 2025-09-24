# Trivy Security Verification Automation - Usage Guide

## 🎯 Understanding the Jira Story

Your Jira story requires building an automated approach to verify Trivy security scanning configuration across all repositories in the CCM GitLab group. Here's how this solution addresses each requirement:

### ✅ Story Requirements Addressed

1. **Automated Trivy Verification**: ✅
   - Automatically scans all repositories in CCM GitLab group
   - Checks for proper Trivy configuration
   - Validates security jobs references

2. **Exclude Archived Repositories**: ✅
   - Built-in filtering to exclude archived repositories
   - Configurable repository ignore list

3. **GitLab API Integration**: ✅
   - Uses GitLab REST API for all operations
   - Supports authentication via access tokens
   - Handles rate limiting and error scenarios

4. **Environment-based Token Management**: ✅
   - Uses `GITLAB_TOKEN` environment variable
   - Supports `.env` file configuration
   - Secure token handling

5. **Local Testing with Virtual Environment**: ✅
   - Complete `.venv` setup script
   - Local testing capabilities
   - Production-ready deployment

## 🏗️ Architecture Overview

### Centralized Library Repository Structure
```
ccm/library/
├── .gitlab-ci.d/
│   ├── security-jobs.yml          # Main security jobs configuration
│   └── security-jobs/
│       └── trivy-scan.yml         # Trivy-specific configuration
```

### Repository Reference Pattern
Other repositories reference the library using:
```yaml
include:
  - project: "ccm/library"
    ref: "main"
    file:
      - "/.gitlab-ci.d/security-jobs.yml"
```

### Verification Logic
The automation checks each repository for:

1. **GitLab CI Configuration**: Presence of `.gitlab-ci.yml` or `.gitlab-ci.yaml`
2. **Security Jobs Reference**: Proper reference to `ccm/library` security jobs
3. **Trivy Configuration**: Either direct Trivy config or reference in CI files
4. **File Structure**: Valid security job file organization

## 🚀 Getting Started

### Step 1: Environment Setup

```bash
# Clone or download the automation files
# Run the setup script
python3 setup.py

# This will:
# - Create virtual environment (.venv)
# - Install all dependencies
# - Create configuration files
# - Set up convenience scripts
```

### Step 2: Configure GitLab Access

```bash
# Option 1: Environment variable
export GITLAB_TOKEN="your_gitlab_access_token_here"

# Option 2: .env file
cp .env .env.local
# Edit .env.local with your token
```

### Step 3: Configure Repository Ignore List

Edit `ignore_repositories.txt`:
```
# Add repositories that don't need Trivy scanning
ccm/legacy-project
ccm/documentation-only
.*-docs$          # Pattern for documentation repos
.*-templates$     # Pattern for template repos
```

### Step 4: Run Verification

```bash
# Basic verification
python3 trivy_verification_automation.py --group-id ccm --token $GITLAB_TOKEN

# With custom configuration
python3 trivy_verification_automation.py \
  --group-id ccm \
  --config custom_config.yaml \
  --output-dir /path/to/reports \
  --verbose

# Dry run (test without API calls)
python3 trivy_verification_automation.py \
  --group-id ccm \
  --dry-run \
  --verbose
```

## 📊 Understanding the Output

### Status Definitions

- **PASS** ✅: Repository has both Trivy config and security jobs reference
- **WARNING** ⚠️: Repository has either Trivy config OR security jobs reference
- **FAIL** ❌: Repository lacks both Trivy config and security jobs reference

### Report Formats

#### 1. Console Output
Immediate feedback with color-coded status:
```
================================================================================
TRIVY SECURITY VERIFICATION REPORT
================================================================================
Generated: 2024-01-15T10:30:00
Total Repositories: 45
Passed: 38 (84.4%)
Warnings: 5
Failed: 2
================================================================================

❌ FAILED REPOSITORIES (2):
--------------------------------------------------
  • ccm/old-service
    - No Trivy security scanning configuration found
    - No reference to security-jobs.yml found in GitLab CI configuration

⚠️  WARNING REPOSITORIES (5):
--------------------------------------------------
  • ccm/api-gateway
    - No reference to security-jobs.yml found in GitLab CI configuration

✅ PASSED REPOSITORIES (38):
--------------------------------------------------
  • ccm/user-service
  • ccm/payment-service
  • ccm/notification-service
  ...
```

#### 2. JSON Report
Structured data for programmatic processing:
```json
{
  "summary": {
    "timestamp": "2024-01-15T10:30:00.123456",
    "total_repositories": 45,
    "passed": 38,
    "warnings": 5,
    "failed": 2,
    "success_rate": 84.4
  },
  "results": [
    {
      "repository": {
        "id": 123,
        "name": "user-service",
        "path": "ccm/user-service",
        "web_url": "https://gitlab.com/ccm/user-service",
        "archived": false,
        "default_branch": "main"
      },
      "verification": {
        "has_trivy_config": true,
        "has_security_jobs_ref": true,
        "trivy_file_path": "Referenced in CI configuration",
        "security_jobs_ref": "project: \"ccm/library\"",
        "issues": [],
        "status": "PASS"
      }
    }
  ]
}
```

#### 3. HTML Report
Visual report with charts and detailed tables for stakeholders.

## 🔧 Configuration Options

### Main Configuration (`config.yaml`)

```yaml
# GitLab Configuration
gitlab:
  base_url: "https://gitlab.com"
  default_group_id: "ccm"

# Library Repository Settings
library:
  repository_path: "ccm/library"
  security_jobs_path: ".gitlab-ci.d/security-jobs.yml"
  trivy_scan_path: ".gitlab-ci.d/security-jobs/trivy-scan.yml"

# Security Tools
security_tools:
  required_tools: ["trivy", "checkov", "semgrep"]

# Verification Rules
verification:
  require_trivy: true
  require_security_jobs_ref: true
  check_direct_trivy_file: true
```

### Repository Ignore List (`ignore_repositories.txt`)

```
# Specific repositories
ccm/legacy-project
ccm/documentation-only

# Pattern-based exclusions
.*-docs$          # Documentation repositories
.*-templates$     # Template repositories
.*-examples$      # Example repositories
```

## 🛠️ Advanced Usage

### Custom Security Tools

To add support for additional security tools:

1. **Update configuration**:
```yaml
security_tools:
  required_tools: ["trivy", "checkov", "semgrep", "bandit", "safety"]
```

2. **Extend verification logic** in the main script

### Integration with CI/CD

Add to your GitLab CI pipeline:

```yaml
verify-security-config:
  stage: security
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - python trivy_verification_automation.py --group-id ccm --token $GITLAB_TOKEN
  artifacts:
    reports:
      junit: reports/verification_report.xml
    paths:
      - reports/
  only:
    - schedules
    - main
```

### Automated Scheduling

Set up a scheduled pipeline to run verification daily:

```yaml
# In your GitLab CI configuration
scheduled-security-check:
  stage: security
  script:
    - python trivy_verification_automation.py --group-id ccm --token $GITLAB_TOKEN
  only:
    variables:
      - $CI_PIPELINE_SOURCE == "schedule"
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: GitLab access token is required
```
**Solution**: 
```bash
export GITLAB_TOKEN="your_token_here"
# Or use --token parameter
```

#### 2. Group Not Found
```
Error: Group 'ccm' not found
```
**Solution**: Verify group ID and access permissions

#### 3. API Rate Limiting
```
Error: 429 Too Many Requests
```
**Solution**: Reduce concurrent requests in configuration

#### 4. Repository Access Issues
```
Error: 403 Forbidden
```
**Solution**: Ensure token has appropriate permissions

### Debug Mode

```bash
# Enable verbose logging
python3 trivy_verification_automation.py \
  --group-id ccm \
  --token $GITLAB_TOKEN \
  --verbose

# Dry run to test configuration
python3 trivy_verification_automation.py \
  --group-id ccm \
  --dry-run \
  --verbose
```

## 📈 Performance Optimization

### Configuration Tuning

```yaml
# Performance settings
performance:
  max_concurrent_requests: 5    # Reduce if hitting rate limits
  request_delay: 0.1           # Add delay between requests
  enable_caching: true         # Cache API responses
  cache_ttl: 3600             # Cache for 1 hour
```

### Expected Performance

- **Small groups** (< 50 repos): 1-2 minutes
- **Medium groups** (50-200 repos): 3-5 minutes  
- **Large groups** (200+ repos): 5-10 minutes

## 🔒 Security Best Practices

### Token Management
- Use environment variables for tokens
- Never commit tokens to version control
- Use GitLab tokens with minimal required permissions
- Rotate tokens regularly

### Access Control
- Limit token scope to required groups only
- Use project-specific tokens when possible
- Monitor token usage and access logs

### Data Privacy
- No sensitive data is stored permanently
- Reports can exclude file contents
- Logs can be configured for appropriate detail levels

## 📋 Maintenance

### Regular Tasks

1. **Update ignore list** as repositories are added/removed
2. **Review verification results** and address failures
3. **Update configuration** for new security tools
4. **Monitor performance** and adjust settings as needed

### Monitoring

Set up alerts for:
- High failure rates
- API rate limit issues
- Authentication problems
- Performance degradation

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section
2. Review configuration options
3. Enable verbose logging for detailed information
4. Test with dry run mode first
5. Create an issue with detailed error information

---

This automation tool provides a comprehensive solution for your Jira story requirements, ensuring consistent Trivy security configuration across all CCM repositories while maintaining flexibility and ease of use.