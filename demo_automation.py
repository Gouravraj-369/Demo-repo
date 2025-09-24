#!/usr/bin/env python3
"""
Demo version of Trivy Security Verification Automation
This demonstrates the functionality without external dependencies
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path


def mock_gitlab_api_call(group_id, token):
    """Mock GitLab API call to simulate repository fetching"""
    print(f"🔗 Connecting to GitLab API for group: {group_id}")
    print(f"🔑 Using token: {token[:10]}...{token[-4:] if len(token) > 14 else '****'}")
    
    # Mock repository data
    mock_repositories = [
        {
            'id': 1,
            'name': 'user-service',
            'path_with_namespace': 'ccm/user-service',
            'web_url': 'https://gitlab.com/ccm/user-service',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-15T10:30:00Z'
        },
        {
            'id': 2,
            'name': 'payment-service',
            'path_with_namespace': 'ccm/payment-service',
            'web_url': 'https://gitlab.com/ccm/payment-service',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-14T15:45:00Z'
        },
        {
            'id': 3,
            'name': 'notification-service',
            'path_with_namespace': 'ccm/notification-service',
            'web_url': 'https://gitlab.com/ccm/notification-service',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-13T09:20:00Z'
        },
        {
            'id': 4,
            'name': 'api-gateway',
            'path_with_namespace': 'ccm/api-gateway',
            'web_url': 'https://gitlab.com/ccm/api-gateway',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-12T14:10:00Z'
        },
        {
            'id': 5,
            'name': 'legacy-system',
            'path_with_namespace': 'ccm/legacy-system',
            'web_url': 'https://gitlab.com/ccm/legacy-system',
            'archived': True,
            'default_branch': 'master',
            'last_activity_at': '2023-12-01T16:30:00Z'
        },
        {
            'id': 6,
            'name': 'documentation',
            'path_with_namespace': 'ccm/documentation',
            'web_url': 'https://gitlab.com/ccm/documentation',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-10T11:15:00Z'
        },
        {
            'id': 7,
            'name': 'old-service',
            'path_with_namespace': 'ccm/old-service',
            'web_url': 'https://gitlab.com/ccm/old-service',
            'archived': False,
            'default_branch': 'main',
            'last_activity_at': '2024-01-08T13:45:00Z'
        }
    ]
    
    print(f"📊 Found {len(mock_repositories)} repositories")
    return mock_repositories


def mock_file_content_check(project_id, file_path, repo_name):
    """Mock file content check to simulate GitLab API file retrieval"""
    print(f"📁 Checking file {file_path} in {repo_name}")
    
    # Mock different scenarios based on repository name
    if 'user-service' in repo_name:
        if 'gitlab-ci.yml' in file_path:
            return '''
stages:
  - build
  - test
  - security
  - deploy

include:
  - project: "ccm/library"
    ref: "main"
    file:
      - "/.gitlab-ci.d/security-jobs.yml"

build:
  stage: build
  script:
    - echo "Building user service"

security:
  stage: security
  extends: .trivy-scan
'''
        elif 'trivy-scan.yml' in file_path:
            return None  # File doesn't exist directly
    
    elif 'payment-service' in repo_name:
        if 'gitlab-ci.yml' in file_path:
            return '''
stages:
  - build
  - test
  - security

include:
  - project: "ccm/library"
    ref: "main"
    file:
      - "/.gitlab-ci.d/security-jobs.yml"

build:
  stage: build
  script:
    - echo "Building payment service"

security:
  stage: security
  extends: .trivy-scan
'''
    
    elif 'notification-service' in repo_name:
        if 'gitlab-ci.yml' in file_path:
            return '''
stages:
  - build
  - test
  - security

include:
  - project: "ccm/library"
    ref: "main"
    file:
      - "/.gitlab-ci.d/security-jobs.yml"

build:
  stage: build
  script:
    - echo "Building notification service"

security:
  stage: security
  extends: .trivy-scan
'''
    
    elif 'api-gateway' in repo_name:
        if 'gitlab-ci.yml' in file_path:
            return '''
stages:
  - build
  - test
  - security

build:
  stage: build
  script:
    - echo "Building API gateway"

trivy-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - trivy fs --format table --exit-code 1 .
'''
        elif 'trivy-scan.yml' in file_path:
            return '''
trivy-scan:
  image: aquasec/trivy:latest
  script:
    - trivy fs --format table --exit-code 1 .
'''
    
    elif 'old-service' in repo_name:
        if 'gitlab-ci.yml' in file_path:
            return '''
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - echo "Building old service"

test:
  stage: test
  script:
    - echo "Running tests"
'''
    
    # Default: file not found
    return None


def verify_repository_security(repo, ignore_list):
    """Verify security configuration for a single repository"""
    repo_path = repo['path_with_namespace']
    
    # Check if repository should be ignored
    for ignore_pattern in ignore_list:
        if ignore_pattern in repo_path or repo_path.endswith(ignore_pattern.replace('*', '')):
            return None  # Skip this repository
    
    # Skip archived repositories
    if repo.get('archived', False):
        return None
    
    print(f"🔍 Verifying: {repo_path}")
    
    # Check for GitLab CI configuration
    ci_content = mock_file_content_check(repo['id'], '.gitlab-ci.yml', repo['name'])
    
    if not ci_content:
        return {
            'repository': repo,
            'verification': {
                'has_trivy_config': False,
                'has_security_jobs_ref': False,
                'trivy_file_path': None,
                'security_jobs_ref': None,
                'issues': ['No GitLab CI configuration file found'],
                'status': 'FAIL'
            }
        }
    
    # Check for security jobs reference
    has_security_jobs_ref = 'security-jobs.yml' in ci_content and 'ccm/library' in ci_content
    security_jobs_ref = None
    
    if has_security_jobs_ref:
        # Extract the reference
        lines = ci_content.split('\n')
        for i, line in enumerate(lines):
            if 'project:' in line and 'library' in line:
                security_jobs_ref = line.strip()
                break
    
    # Check for Trivy configuration
    has_trivy_config = 'trivy' in ci_content.lower()
    trivy_file_path = None
    
    if has_trivy_config:
        trivy_file_path = "Referenced in CI configuration"
    else:
        # Check for direct Trivy file
        trivy_content = mock_file_content_check(repo['id'], '.gitlab-ci.d/security-jobs/trivy-scan.yml', repo['name'])
        if trivy_content:
            has_trivy_config = True
            trivy_file_path = '.gitlab-ci.d/security-jobs/trivy-scan.yml'
    
    # Determine issues and status
    issues = []
    
    if not has_trivy_config:
        issues.append("No Trivy security scanning configuration found")
    
    if not has_security_jobs_ref:
        issues.append("No reference to security-jobs.yml found in GitLab CI configuration")
    
    # Determine status
    if has_trivy_config and has_security_jobs_ref:
        status = 'PASS'
    elif has_trivy_config or has_security_jobs_ref:
        status = 'WARNING'
    else:
        status = 'FAIL'
    
    return {
        'repository': repo,
        'verification': {
            'has_trivy_config': has_trivy_config,
            'has_security_jobs_ref': has_security_jobs_ref,
            'trivy_file_path': trivy_file_path,
            'security_jobs_ref': security_jobs_ref,
            'issues': issues,
            'status': status
        }
    }


def generate_console_report(results):
    """Generate console report"""
    if not results:
        print("No repositories to report on.")
        return
    
    # Calculate summary
    total_repos = len(results)
    passed = sum(1 for r in results if r['verification']['status'] == 'PASS')
    warnings = sum(1 for r in results if r['verification']['status'] == 'WARNING')
    failed = sum(1 for r in results if r['verification']['status'] == 'FAIL')
    success_rate = (passed / total_repos * 100) if total_repos > 0 else 0
    
    print("\n" + "=" * 80)
    print("TRIVY SECURITY VERIFICATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Total Repositories: {total_repos}")
    print(f"Passed: {passed} ({success_rate:.1f}%)")
    print(f"Warnings: {warnings}")
    print(f"Failed: {failed}")
    print("=" * 80)
    
    # Group results by status
    failed_repos = [r for r in results if r['verification']['status'] == 'FAIL']
    warning_repos = [r for r in results if r['verification']['status'] == 'WARNING']
    passed_repos = [r for r in results if r['verification']['status'] == 'PASS']
    
    if failed_repos:
        print(f"\n❌ FAILED REPOSITORIES ({len(failed_repos)}):")
        print("-" * 50)
        for repo in failed_repos:
            print(f"  • {repo['repository']['path_with_namespace']}")
            for issue in repo['verification']['issues']:
                print(f"    - {issue}")
    
    if warning_repos:
        print(f"\n⚠️  WARNING REPOSITORIES ({len(warning_repos)}):")
        print("-" * 50)
        for repo in warning_repos:
            print(f"  • {repo['repository']['path_with_namespace']}")
            for issue in repo['verification']['issues']:
                print(f"    - {issue}")
    
    if passed_repos:
        print(f"\n✅ PASSED REPOSITORIES ({len(passed_repos)}):")
        print("-" * 50)
        for repo in passed_repos:
            print(f"  • {repo['repository']['path_with_namespace']}")
    
    print("\n" + "=" * 80)


def generate_json_report(results, output_dir):
    """Generate JSON report"""
    if not results:
        return None
    
    # Calculate summary
    total_repos = len(results)
    passed = sum(1 for r in results if r['verification']['status'] == 'PASS')
    warnings = sum(1 for r in results if r['verification']['status'] == 'WARNING')
    failed = sum(1 for r in results if r['verification']['status'] == 'FAIL')
    success_rate = (passed / total_repos * 100) if total_repos > 0 else 0
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_repositories': total_repos,
        'passed': passed,
        'warnings': warnings,
        'failed': failed,
        'success_rate': success_rate
    }
    
    json_report = {
        'summary': summary,
        'results': results
    }
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Save JSON report
    json_file = f"{output_dir}/trivy_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(json_report, f, indent=2)
    
    print(f"📄 JSON report saved: {json_file}")
    return json_file


def main():
    """Main function to demonstrate the automation"""
    parser = argparse.ArgumentParser(
        description='Demo Trivy Security Configuration Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run verification for CCM group
  python demo_automation.py --group-id ccm --token demo_token
  
  # Run with verbose output
  python demo_automation.py --group-id ccm --token demo_token --verbose
  
  # Run with custom output directory
  python demo_automation.py --group-id ccm --token demo_token --output-dir reports
        """
    )
    
    parser.add_argument('--group-id', required=True, help='GitLab group ID or path')
    parser.add_argument('--token', help='GitLab access token (demo mode)')
    parser.add_argument('--output-dir', default='reports', help='Output directory for reports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run')
    
    args = parser.parse_args()
    
    # Use demo token if not provided
    token = args.token or 'demo_token_12345'
    
    print("🚀 Trivy Security Verification Automation - DEMO MODE")
    print("=" * 60)
    print(f"Group ID: {args.group_id}")
    print(f"Token: {token[:10]}...{token[-4:] if len(token) > 14 else '****'}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Verbose: {args.verbose}")
    print(f"Dry Run: {args.dry_run}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No actual API calls will be made")
        print("✅ Configuration validated")
        print("✅ Ready to process repositories")
        return
    
    # Load ignore list
    ignore_list = ['ccm/legacy-system', 'ccm/documentation', '.*-docs$']
    print(f"\n📋 Ignore list loaded: {len(ignore_list)} patterns")
    
    # Fetch repositories
    print(f"\n🔗 Fetching repositories from group: {args.group_id}")
    repositories = mock_gitlab_api_call(args.group_id, token)
    
    # Filter repositories
    print(f"\n🔍 Processing {len(repositories)} repositories...")
    results = []
    
    for i, repo in enumerate(repositories, 1):
        if args.verbose:
            print(f"Processing {i}/{len(repositories)}: {repo['name']}")
        
        result = verify_repository_security(repo, ignore_list)
        if result:
            results.append(result)
    
    print(f"\n📊 Verification completed: {len(results)} repositories processed")
    
    # Generate reports
    print(f"\n📄 Generating reports...")
    generate_console_report(results)
    
    json_file = generate_json_report(results, args.output_dir)
    
    # Summary
    if results:
        total = len(results)
        passed = sum(1 for r in results if r['verification']['status'] == 'PASS')
        warnings = sum(1 for r in results if r['verification']['status'] == 'WARNING')
        failed = sum(1 for r in results if r['verification']['status'] == 'FAIL')
        
        print(f"\n🎉 Verification completed!")
        print(f"📈 Success rate: {(passed/total*100):.1f}%")
        print(f"📊 Results: {passed} passed, {warnings} warnings, {failed} failed")
        
        if failed > 0:
            print(f"⚠️  {failed} repositories need attention")
            sys.exit(1)
        elif warnings > 0:
            print(f"⚠️  {warnings} repositories have warnings")
            sys.exit(2)
        else:
            print(f"✅ All repositories passed verification!")
            sys.exit(0)
    else:
        print("❌ No repositories to verify")
        sys.exit(1)


if __name__ == '__main__':
    main()