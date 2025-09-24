# Trivy Security Verification Automation

A sophisticated Python automation tool to verify Trivy security scanning configuration across all repositories in a GitLab group, excluding archived repositories.

## 🎯 Overview

This automation tool addresses the Jira story requirement to:
- Set up an automated approach to verify Trivy is correctly configured in each repository within CCM GitLab group
- Create an ignore list of repositories that might not need Trivy setup
- Use GitLab APIs for automation with environment-based access tokens
- Support local testing with virtual environment before production deployment

## 🏗️ Architecture

The solution consists of several key components:

### Core Components

1. **Main Script** (`trivy_verification_automation.py`)
   - Orchestrates the entire verification process
   - Handles command-line arguments and configuration
   - Generates comprehensive reports

2. **GitLab API Client** (`GitLabAPIClient` class)
   - Manages all GitLab API interactions
   - Handles authentication and rate limiting
   - Fetches repository information and file contents

3. **Verification Engine** (`TrivyVerificationEngine` class)
   - Performs security configuration verification
   - Checks for Trivy and security jobs configuration
   - Generates detailed reports

4. **Configuration Management**
   - `config.yaml`: Main configuration file
   - `ignore_repositories.txt`: Repository ignore list
   - `.env`: Environment variables template

## 📋 Features

### ✅ Core Features
- **Automated Repository Discovery**: Fetches all repositories from GitLab group
- **Trivy Configuration Verification**: Checks for proper Trivy setup
- **Security Jobs Reference Validation**: Verifies security-jobs.yml references
- **Repository Filtering**: Excludes archived and ignored repositories
- **Comprehensive Reporting**: Generates JSON, HTML, and console reports
- **Configurable Ignore Lists**: Flexible repository exclusion patterns

### 🔧 Advanced Features
- **Multiple Output Formats**: JSON, HTML, and console reports
- **Detailed Issue Tracking**: Identifies specific configuration problems
- **Performance Optimization**: Concurrent API requests with rate limiting
- **Extensible Architecture**: Easy to add new security tools
- **Environment-based Configuration**: Secure token management
- **Dry Run Mode**: Test configuration without making API calls

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- GitLab access token with appropriate permissions
- Access to the CCM GitLab group

### Installation

1. **Clone or download the automation files**
2. **Run the setup script**:
   ```bash
   python setup.py
   ```

3. **Configure environment variables**:
   ```bash
   cp .env .env.local
   # Edit .env.local with your GitLab token and settings
   ```

4. **Run verification**:
   ```bash
   # Using the convenience script
   ./run_verification.sh --group-id ccm --token YOUR_TOKEN
   
   # Or directly with Python
   .venv/bin/python trivy_verification_automation.py --group-id ccm --token YOUR_TOKEN
   ```

## 📖 Detailed Usage

### Command Line Options

```bash
python trivy_verification_automation.py [OPTIONS]

Required:
  --group-id GROUP_ID    GitLab group ID or path (e.g., "ccm" or "123")

Optional:
  --token TOKEN          GitLab access token (or use GITLAB_TOKEN env var)
  --base-url URL         GitLab instance URL (default: https://gitlab.com)
  --config FILE          Configuration file path (default: config.yaml)
  --output-dir DIR       Output directory for reports (default: reports)
  --verbose, -v          Enable verbose logging
  --dry-run              Perform dry run without API calls
  --help                 Show help message
```

### Examples

#### Basic Verification
```bash
python trivy_verification_automation.py --group-id ccm --token $GITLAB_TOKEN
```

#### Custom Configuration
```bash
python trivy_verification_automation.py \
  --group-id ccm \
  --config custom_config.yaml \
  --output-dir /path/to/reports \
  --verbose
```

#### Dry Run (Test Configuration)
```bash
python trivy_verification_automation.py \
  --group-id ccm \
  --dry-run \
  --verbose
```

## 🔧 Configuration

### Main Configuration (`config.yaml`)

The configuration file contains all settings for the automation:

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

Add repository patterns to exclude from verification:

```
# Specific repositories
ccm/legacy-project
ccm/documentation-only

# Pattern-based exclusions
.*-docs$          # Documentation repositories
.*-templates$     # Template repositories
.*-examples$      # Example repositories
```

### Environment Variables (`.env`)

```bash
# Required
GITLAB_TOKEN=your_gitlab_access_token_here
GITLAB_GROUP_ID=ccm

# Optional
GITLAB_BASE_URL=https://gitlab.com
LOG_LEVEL=INFO
```

## 📊 Report Formats

### JSON Report
Structured data for programmatic processing:
```json
{
  "summary": {
    "timestamp": "2024-01-15T10:30:00",
    "total_repositories": 45,
    "passed": 38,
    "warnings": 5,
    "failed": 2,
    "success_rate": 84.4
  },
  "results": [...]
}
```

### HTML Report
Visual report with charts and detailed tables for stakeholders.

### Console Report
Immediate feedback with color-coded status indicators.

## 🔍 Verification Logic

The automation checks each repository for:

1. **GitLab CI Configuration**: Presence of `.gitlab-ci.yml` or `.gitlab-ci.yaml`
2. **Security Jobs Reference**: Reference to `security-jobs.yml` from library repository
3. **Trivy Configuration**: Direct Trivy configuration or reference in CI files
4. **File Structure**: Proper security job file organization

### Status Definitions

- **PASS**: Repository has both Trivy config and security jobs reference
- **WARNING**: Repository has either Trivy config OR security jobs reference
- **FAIL**: Repository lacks both Trivy config and security jobs reference

## 🛠️ Development

### Project Structure
```
.
├── trivy_verification_automation.py  # Main automation script
├── config.yaml                       # Configuration file
├── ignore_repositories.txt           # Repository ignore list
├── requirements.txt                  # Python dependencies
├── setup.py                         # Setup script
├── .env                             # Environment variables template
├── .gitignore                       # Git ignore file
├── run_verification.sh              # Convenience run script
└── README.md                        # This documentation
```

### Adding New Security Tools

1. **Update configuration** in `config.yaml`:
   ```yaml
   security_tools:
     required_tools: ["trivy", "checkov", "semgrep", "new_tool"]
   ```

2. **Add verification logic** in `TrivyVerificationEngine.verify_repository_security_config()`

3. **Update file patterns** in configuration

### Extending Reports

1. **Add new output format** in `config.yaml`
2. **Implement generator method** in `TrivyVerificationEngine`
3. **Update report generation** in `generate_report()`

## 🔒 Security Considerations

### Token Management
- Use environment variables for sensitive tokens
- Never commit tokens to version control
- Use GitLab token with minimal required permissions

### API Rate Limiting
- Built-in rate limiting to respect GitLab API limits
- Configurable concurrent request limits
- Automatic retry with exponential backoff

### Data Privacy
- No sensitive repository data is stored permanently
- Reports can be configured to exclude file contents
- Logs can be configured for appropriate detail levels

## 🐛 Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: GitLab access token is required
```
**Solution**: Set `GITLAB_TOKEN` environment variable or use `--token` parameter

#### API Rate Limiting
```
Error: 429 Too Many Requests
```
**Solution**: Reduce `max_concurrent_requests` in configuration

#### Repository Not Found
```
Error: Group 'ccm' not found
```
**Solution**: Verify group ID and access permissions

### Debug Mode
```bash
python trivy_verification_automation.py --group-id ccm --verbose --dry-run
```

## 📈 Performance

### Optimization Features
- Concurrent API requests (configurable limit)
- Request caching (configurable TTL)
- Pagination for large repository lists
- Progress indicators for long operations

### Typical Performance
- **Small groups** (< 50 repos): 1-2 minutes
- **Medium groups** (50-200 repos): 3-5 minutes
- **Large groups** (200+ repos): 5-10 minutes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the configuration options
3. Enable verbose logging for detailed information
4. Create an issue with detailed error information

## 🔄 Version History

- **v1.0.0**: Initial release with core Trivy verification functionality
- **v1.1.0**: Added HTML reports and improved error handling
- **v1.2.0**: Added concurrent processing and performance optimizations

---

**Note**: This automation tool is designed specifically for the CCM GitLab group structure and may require customization for other environments.