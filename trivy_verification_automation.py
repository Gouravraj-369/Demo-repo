#!/usr/bin/env python3
"""
Trivy Security Verification Automation Script

This script automates the verification of Trivy security scanning configuration
across all repositories in the CCM GitLab group, excluding archived repositories.

Author: DevSecOps Engineer
Version: 1.0.0
"""

import os
import sys
import json
import logging
import argparse
import requests
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import yaml
from pathlib import Path


@dataclass
class RepositoryInfo:
    """Data class to store repository information"""
    id: int
    name: str
    path: str
    web_url: str
    archived: bool
    default_branch: str
    last_activity_at: str


@dataclass
class VerificationResult:
    """Data class to store verification results for each repository"""
    repository: RepositoryInfo
    has_trivy_config: bool
    has_security_jobs_ref: bool
    trivy_file_path: Optional[str]
    security_jobs_ref: Optional[str]
    issues: List[str]
    status: str  # 'PASS', 'FAIL', 'WARNING'


class GitLabAPIClient:
    """
    GitLab API client for interacting with GitLab REST API
    
    This class handles all GitLab API interactions including:
    - Authentication using access tokens
    - Fetching group repositories
    - Retrieving file contents
    - Checking repository configurations
    """
    
    def __init__(self, base_url: str, access_token: str):
        """
        Initialize GitLab API client
        
        Args:
            base_url (str): GitLab instance base URL (e.g., 'https://gitlab.com')
            access_token (str): GitLab access token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })
        
        # Configure logging for API requests
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_group_repositories(self, group_id: str, exclude_archived: bool = True) -> List[RepositoryInfo]:
        """
        Fetch all repositories from a GitLab group
        
        Args:
            group_id (str): GitLab group ID or path
            exclude_archived (bool): Whether to exclude archived repositories
            
        Returns:
            List[RepositoryInfo]: List of repository information objects
        """
        repositories = []
        page = 1
        per_page = 100
        
        self.logger.info(f"Fetching repositories from group: {group_id}")
        
        while True:
            # Construct API endpoint for group projects
            url = f"{self.base_url}/api/v4/groups/{group_id}/projects"
            params = {
                'page': page,
                'per_page': per_page,
                'include_subgroups': True,
                'with_issues_enabled': False,
                'with_merge_requests_enabled': False,
                'with_wiki_enabled': False,
                'simple': False
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                projects = response.json()
                
                if not projects:
                    break
                
                for project in projects:
                    # Skip archived repositories if requested
                    if exclude_archived and project.get('archived', False):
                        self.logger.debug(f"Skipping archived repository: {project['name']}")
                        continue
                    
                    repo_info = RepositoryInfo(
                        id=project['id'],
                        name=project['name'],
                        path=project['path_with_namespace'],
                        web_url=project['web_url'],
                        archived=project.get('archived', False),
                        default_branch=project.get('default_branch', 'main'),
                        last_activity_at=project.get('last_activity_at', '')
                    )
                    repositories.append(repo_info)
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching repositories: {e}")
                break
        
        self.logger.info(f"Found {len(repositories)} repositories")
        return repositories
    
    def get_file_content(self, project_id: int, file_path: str, ref: str = 'main') -> Optional[str]:
        """
        Retrieve file content from a GitLab repository
        
        Args:
            project_id (int): GitLab project ID
            file_path (str): Path to the file in the repository
            ref (str): Git reference (branch, tag, or commit)
            
        Returns:
            Optional[str]: File content if found, None otherwise
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/files/{file_path.replace('/', '%2F')}"
        params = {'ref': ref}
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            
            file_data = response.json()
            # Decode base64 content
            import base64
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return content
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching file {file_path} from project {project_id}: {e}")
            return None
    
    def check_file_exists(self, project_id: int, file_path: str, ref: str = 'main') -> bool:
        """
        Check if a file exists in the repository
        
        Args:
            project_id (int): GitLab project ID
            file_path (str): Path to the file
            ref (str): Git reference
            
        Returns:
            bool: True if file exists, False otherwise
        """
        return self.get_file_content(project_id, file_path, ref) is not None


class TrivyVerificationEngine:
    """
    Main verification engine for Trivy security configuration
    
    This class orchestrates the verification process by:
    - Loading configuration and ignore lists
    - Coordinating with GitLab API client
    - Performing security configuration checks
    - Generating comprehensive reports
    """
    
    def __init__(self, gitlab_client: GitLabAPIClient, config_file: str = 'config.yaml'):
        """
        Initialize the verification engine
        
        Args:
            gitlab_client (GitLabAPIClient): Initialized GitLab API client
            config_file (str): Path to configuration file
        """
        self.gitlab_client = gitlab_client
        self.config = self._load_config(config_file)
        self.ignore_list = self._load_ignore_list()
        self.logger = logging.getLogger(__name__)
        
        # Security configuration patterns to check
        self.security_patterns = {
            'trivy_scan_yml': '.gitlab-ci.d/security-jobs/trivy-scan.yml',
            'security_jobs_yml': '.gitlab-ci.d/security-jobs.yml',
            'gitlab_ci_yml': '.gitlab-ci.yml',
            'gitlab_ci_yaml': '.gitlab-ci.yaml'
        }
    
    def _load_config(self, config_file: str) -> Dict:
        """
        Load configuration from YAML file
        
        Args:
            config_file (str): Path to configuration file
            
        Returns:
            Dict: Configuration dictionary
        """
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from {config_file}")
            return config
        except FileNotFoundError:
            self.logger.warning(f"Configuration file {config_file} not found, using defaults")
            return self._get_default_config()
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """
        Get default configuration values
        
        Returns:
            Dict: Default configuration
        """
        return {
            'library_repo': 'ccm/library',
            'security_jobs_path': '.gitlab-ci.d/security-jobs.yml',
            'trivy_scan_path': '.gitlab-ci.d/security-jobs/trivy-scan.yml',
            'required_security_tools': ['trivy', 'checkov'],
            'output_formats': ['json', 'html', 'console']
        }
    
    def _load_ignore_list(self) -> Set[str]:
        """
        Load repository ignore list from file
        
        Returns:
            Set[str]: Set of repository paths to ignore
        """
        ignore_file = 'ignore_repositories.txt'
        ignore_list = set()
        
        try:
            with open(ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_list.add(line)
            self.logger.info(f"Loaded {len(ignore_list)} repositories to ignore")
        except FileNotFoundError:
            self.logger.info("No ignore list file found, creating default one")
            self._create_default_ignore_list()
        
        return ignore_list
    
    def _create_default_ignore_list(self):
        """
        Create a default ignore list file with common patterns
        """
        default_ignores = [
            '# Ignore repositories that do not need Trivy security scanning',
            '# Add repository paths here (one per line)',
            '# Example: ccm/legacy-project',
            '# Example: ccm/documentation-only',
            '',
            '# Common patterns to ignore:',
            'ccm/.*-docs$',  # Documentation repositories
            'ccm/.*-templates$',  # Template repositories
            'ccm/.*-examples$',  # Example repositories
        ]
        
        with open('ignore_repositories.txt', 'w') as f:
            f.write('\n'.join(default_ignores))
    
    def should_ignore_repository(self, repo_path: str) -> bool:
        """
        Check if a repository should be ignored based on ignore list
        
        Args:
            repo_path (str): Repository path to check
            
        Returns:
            bool: True if repository should be ignored
        """
        import re
        
        for pattern in self.ignore_list:
            if re.match(pattern, repo_path):
                return True
        return False
    
    def verify_repository_security_config(self, repo: RepositoryInfo) -> VerificationResult:
        """
        Verify security configuration for a single repository
        
        Args:
            repo (RepositoryInfo): Repository information
            
        Returns:
            VerificationResult: Verification results for the repository
        """
        self.logger.info(f"Verifying security configuration for: {repo.path}")
        
        issues = []
        has_trivy_config = False
        has_security_jobs_ref = False
        trivy_file_path = None
        security_jobs_ref = None
        
        # Check for GitLab CI configuration files
        ci_files = ['.gitlab-ci.yml', '.gitlab-ci.yaml']
        ci_content = None
        ci_file_found = None
        
        for ci_file in ci_files:
            content = self.gitlab_client.get_file_content(repo.id, ci_file, repo.default_branch)
            if content:
                ci_content = content
                ci_file_found = ci_file
                break
        
        if not ci_content:
            issues.append(f"No GitLab CI configuration file found (.gitlab-ci.yml or .gitlab-ci.yaml)")
            return VerificationResult(
                repository=repo,
                has_trivy_config=False,
                has_security_jobs_ref=False,
                trivy_file_path=None,
                security_jobs_ref=None,
                issues=issues,
                status='FAIL'
            )
        
        # Check for security jobs reference
        if 'security-jobs.yml' in ci_content:
            has_security_jobs_ref = True
            # Extract the reference details
            lines = ci_content.split('\n')
            for i, line in enumerate(lines):
                if 'security-jobs.yml' in line:
                    # Look for project reference in nearby lines
                    for j in range(max(0, i-5), min(len(lines), i+5)):
                        if 'project:' in lines[j] and 'library' in lines[j]:
                            security_jobs_ref = lines[j].strip()
                            break
                    break
        
        if not has_security_jobs_ref:
            issues.append("No reference to security-jobs.yml found in GitLab CI configuration")
        
        # Check for direct Trivy configuration
        trivy_content = self.gitlab_client.get_file_content(
            repo.id, 
            self.config['trivy_scan_path'], 
            repo.default_branch
        )
        
        if trivy_content:
            has_trivy_config = True
            trivy_file_path = self.config['trivy_scan_path']
        else:
            # Check if Trivy is referenced in the CI configuration
            if 'trivy' in ci_content.lower():
                has_trivy_config = True
                trivy_file_path = "Referenced in CI configuration"
        
        if not has_trivy_config:
            issues.append("No Trivy security scanning configuration found")
        
        # Determine overall status
        if has_trivy_config and has_security_jobs_ref:
            status = 'PASS'
        elif has_trivy_config or has_security_jobs_ref:
            status = 'WARNING'
        else:
            status = 'FAIL'
        
        return VerificationResult(
            repository=repo,
            has_trivy_config=has_trivy_config,
            has_security_jobs_ref=has_security_jobs_ref,
            trivy_file_path=trivy_file_path,
            security_jobs_ref=security_jobs_ref,
            issues=issues,
            status=status
        )
    
    def run_verification(self, group_id: str) -> List[VerificationResult]:
        """
        Run verification for all repositories in the group
        
        Args:
            group_id (str): GitLab group ID
            
        Returns:
            List[VerificationResult]: List of verification results
        """
        self.logger.info(f"Starting verification for group: {group_id}")
        
        # Get all repositories from the group
        repositories = self.gitlab_client.get_group_repositories(group_id)
        
        # Filter out ignored repositories
        filtered_repos = []
        for repo in repositories:
            if not self.should_ignore_repository(repo.path):
                filtered_repos.append(repo)
            else:
                self.logger.info(f"Ignoring repository: {repo.path}")
        
        self.logger.info(f"Verifying {len(filtered_repos)} repositories (excluded {len(repositories) - len(filtered_repos)} ignored)")
        
        # Verify each repository
        results = []
        for i, repo in enumerate(filtered_repos, 1):
            self.logger.info(f"Processing repository {i}/{len(filtered_repos)}: {repo.path}")
            result = self.verify_repository_security_config(repo)
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[VerificationResult], output_dir: str = 'reports') -> Dict:
        """
        Generate comprehensive verification report
        
        Args:
            results (List[VerificationResult]): Verification results
            output_dir (str): Output directory for reports
            
        Returns:
            Dict: Report summary
        """
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate summary statistics
        total_repos = len(results)
        passed = sum(1 for r in results if r.status == 'PASS')
        warnings = sum(1 for r in results if r.status == 'WARNING')
        failed = sum(1 for r in results if r.status == 'FAIL')
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_repositories': total_repos,
            'passed': passed,
            'warnings': warnings,
            'failed': failed,
            'success_rate': (passed / total_repos * 100) if total_repos > 0 else 0
        }
        
        # Generate JSON report
        json_report = {
            'summary': summary,
            'results': [
                {
                    'repository': {
                        'id': r.repository.id,
                        'name': r.repository.name,
                        'path': r.repository.path,
                        'web_url': r.repository.web_url,
                        'archived': r.repository.archived,
                        'default_branch': r.repository.default_branch
                    },
                    'verification': {
                        'has_trivy_config': r.has_trivy_config,
                        'has_security_jobs_ref': r.has_security_jobs_ref,
                        'trivy_file_path': r.trivy_file_path,
                        'security_jobs_ref': r.security_jobs_ref,
                        'issues': r.issues,
                        'status': r.status
                    }
                }
                for r in results
            ]
        }
        
        # Save JSON report
        json_file = f"{output_dir}/trivy_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        # Generate HTML report
        html_file = f"{output_dir}/trivy_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        self._generate_html_report(json_report, html_file)
        
        # Generate console report
        self._generate_console_report(summary, results)
        
        self.logger.info(f"Reports generated in {output_dir}/")
        self.logger.info(f"JSON report: {json_file}")
        self.logger.info(f"HTML report: {html_file}")
        
        return summary
    
    def _generate_html_report(self, report_data: Dict, output_file: str):
        """
        Generate HTML report for better visualization
        
        Args:
            report_data (Dict): Report data
            output_file (str): Output HTML file path
        """
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trivy Security Verification Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; }
        .summary-card .number { font-size: 2em; font-weight: bold; }
        .passed { color: #28a745; }
        .warning { color: #ffc107; }
        .failed { color: #dc3545; }
        .results-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .results-table th, .results-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .results-table th { background-color: #f8f9fa; font-weight: bold; }
        .status-pass { color: #28a745; font-weight: bold; }
        .status-warning { color: #ffc107; font-weight: bold; }
        .status-fail { color: #dc3545; font-weight: bold; }
        .issues { max-width: 300px; word-wrap: break-word; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trivy Security Verification Report</h1>
            <p class="timestamp">Generated on: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Repositories</h3>
                <div class="number">{total_repositories}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="number passed">{passed}</div>
            </div>
            <div class="summary-card">
                <h3>Warnings</h3>
                <div class="number warning">{warnings}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="number failed">{failed}</div>
            </div>
            <div class="summary-card">
                <h3>Success Rate</h3>
                <div class="number">{success_rate:.1f}%</div>
            </div>
        </div>
        
        <h2>Repository Details</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Status</th>
                    <th>Trivy Config</th>
                    <th>Security Jobs Ref</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        # Generate table rows
        table_rows = ""
        for result in report_data['results']:
            status_class = f"status-{result['verification']['status'].lower()}"
            issues_text = "<br>".join(result['verification']['issues']) if result['verification']['issues'] else "None"
            
            table_rows += f"""
                <tr>
                    <td>
                        <a href="{result['repository']['web_url']}" target="_blank">
                            {result['repository']['path']}
                        </a>
                    </td>
                    <td class="{status_class}">{result['verification']['status']}</td>
                    <td>{'✓' if result['verification']['has_trivy_config'] else '✗'}</td>
                    <td>{'✓' if result['verification']['has_security_jobs_ref'] else '✗'}</td>
                    <td class="issues">{issues_text}</td>
                </tr>
            """
        
        # Format the HTML
        html_content = html_template.format(
            timestamp=report_data['summary']['timestamp'],
            total_repositories=report_data['summary']['total_repositories'],
            passed=report_data['summary']['passed'],
            warnings=report_data['summary']['warnings'],
            failed=report_data['summary']['failed'],
            success_rate=report_data['summary']['success_rate'],
            table_rows=table_rows
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    def _generate_console_report(self, summary: Dict, results: List[VerificationResult]):
        """
        Generate console report for immediate feedback
        
        Args:
            summary (Dict): Report summary
            results (List[VerificationResult]): Verification results
        """
        print("\n" + "="*80)
        print("TRIVY SECURITY VERIFICATION REPORT")
        print("="*80)
        print(f"Generated: {summary['timestamp']}")
        print(f"Total Repositories: {summary['total_repositories']}")
        print(f"Passed: {summary['passed']} ({summary['success_rate']:.1f}%)")
        print(f"Warnings: {summary['warnings']}")
        print(f"Failed: {summary['failed']}")
        print("="*80)
        
        # Group results by status
        passed_repos = [r for r in results if r.status == 'PASS']
        warning_repos = [r for r in results if r.status == 'WARNING']
        failed_repos = [r for r in results if r.status == 'FAIL']
        
        if failed_repos:
            print(f"\n❌ FAILED REPOSITORIES ({len(failed_repos)}):")
            print("-" * 50)
            for repo in failed_repos:
                print(f"  • {repo.repository.path}")
                for issue in repo.issues:
                    print(f"    - {issue}")
        
        if warning_repos:
            print(f"\n⚠️  WARNING REPOSITORIES ({len(warning_repos)}):")
            print("-" * 50)
            for repo in warning_repos:
                print(f"  • {repo.repository.path}")
                for issue in repo.issues:
                    print(f"    - {issue}")
        
        if passed_repos:
            print(f"\n✅ PASSED REPOSITORIES ({len(passed_repos)}):")
            print("-" * 50)
            for repo in passed_repos:
                print(f"  • {repo.repository.path}")
        
        print("\n" + "="*80)


def main():
    """
    Main function to orchestrate the Trivy verification process
    
    This function:
    1. Parses command line arguments
    2. Initializes GitLab API client
    3. Creates verification engine
    4. Runs verification process
    5. Generates comprehensive reports
    """
    parser = argparse.ArgumentParser(
        description='Automated Trivy Security Configuration Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run verification for CCM group
  python trivy_verification_automation.py --group-id ccm --token $GITLAB_TOKEN
  
  # Run with custom configuration
  python trivy_verification_automation.py --group-id ccm --config custom_config.yaml
  
  # Run in verbose mode
  python trivy_verification_automation.py --group-id ccm --verbose
        """
    )
    
    parser.add_argument(
        '--group-id', 
        required=True, 
        help='GitLab group ID or path (e.g., "ccm" or "123")'
    )
    parser.add_argument(
        '--token', 
        help='GitLab access token (can also use GITLAB_TOKEN environment variable)'
    )
    parser.add_argument(
        '--base-url', 
        default='https://gitlab.com',
        help='GitLab instance base URL (default: https://gitlab.com)'
    )
    parser.add_argument(
        '--config', 
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    parser.add_argument(
        '--output-dir', 
        default='reports',
        help='Output directory for reports (default: reports)'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Perform a dry run without making API calls'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get GitLab access token
    access_token = args.token or os.getenv('GITLAB_TOKEN')
    if not access_token:
        print("Error: GitLab access token is required. Use --token or set GITLAB_TOKEN environment variable.")
        sys.exit(1)
    
    try:
        # Initialize GitLab API client
        print("Initializing GitLab API client...")
        gitlab_client = GitLabAPIClient(args.base_url, access_token)
        
        # Initialize verification engine
        print("Initializing verification engine...")
        verification_engine = TrivyVerificationEngine(gitlab_client, args.config)
        
        if args.dry_run:
            print("Dry run mode: Would verify repositories in group:", args.group_id)
            print("Configuration loaded successfully.")
            return
        
        # Run verification
        print(f"Starting verification for group: {args.group_id}")
        results = verification_engine.run_verification(args.group_id)
        
        # Generate reports
        print("Generating reports...")
        summary = verification_engine.generate_report(results, args.output_dir)
        
        # Exit with appropriate code
        if summary['failed'] > 0:
            print(f"\nVerification completed with {summary['failed']} failures.")
            sys.exit(1)
        elif summary['warnings'] > 0:
            print(f"\nVerification completed with {summary['warnings']} warnings.")
            sys.exit(2)
        else:
            print(f"\nVerification completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nVerification interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"Error during verification: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()