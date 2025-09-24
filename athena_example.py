#!/usr/bin/env python3
"""
Example Python script demonstrating how to use AWS Athena workgroups
created by the CloudFormation template.
"""

import boto3
import time
import sys
from typing import Dict, List, Optional
import json


class AthenaQueryRunner:
    """Helper class to run Athena queries using the configured workgroups."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize the Athena client."""
        self.athena_client = boto3.client('athena', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
    
    def list_workgroups(self, project_name: str, environment: str) -> List[str]:
        """List all workgroups for the project."""
        try:
            response = self.athena_client.list_work_groups()
            workgroups = []
            
            prefix = f"{project_name}-"
            suffix = f"-{environment}"
            
            for workgroup in response['WorkGroups']:
                name = workgroup['Name']
                if name.startswith(prefix) and name.endswith(suffix):
                    workgroups.append(name)
            
            return workgroups
        except Exception as e:
            print(f"Error listing workgroups: {e}")
            return []
    
    def get_workgroup_info(self, workgroup_name: str) -> Optional[Dict]:
        """Get detailed information about a workgroup."""
        try:
            response = self.athena_client.get_work_group(WorkGroup=workgroup_name)
            return response['WorkGroup']
        except Exception as e:
            print(f"Error getting workgroup info for {workgroup_name}: {e}")
            return None
    
    def run_query(self, 
                  query: str, 
                  workgroup: str, 
                  database: str = 'default',
                  wait_for_completion: bool = True) -> Optional[str]:
        """
        Execute a query in the specified workgroup.
        
        Args:
            query: SQL query to execute
            workgroup: Name of the workgroup to use
            database: Database name (default: 'default')
            wait_for_completion: Whether to wait for query completion
            
        Returns:
            Query execution ID if successful, None otherwise
        """
        try:
            # Start query execution
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database},
                WorkGroup=workgroup
            )
            
            execution_id = response['QueryExecutionId']
            print(f"Started query execution: {execution_id}")
            
            if wait_for_completion:
                self._wait_for_query_completion(execution_id)
            
            return execution_id
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def _wait_for_query_completion(self, execution_id: str, max_wait_time: int = 300):
        """Wait for query completion with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=execution_id
                )
                
                status = response['QueryExecution']['Status']['State']
                
                if status == 'SUCCEEDED':
                    print(f"Query {execution_id} completed successfully")
                    return True
                elif status in ['FAILED', 'CANCELLED']:
                    reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                    print(f"Query {execution_id} failed: {reason}")
                    return False
                
                print(f"Query {execution_id} status: {status}")
                time.sleep(5)
                
            except Exception as e:
                print(f"Error checking query status: {e}")
                return False
        
        print(f"Query {execution_id} timed out after {max_wait_time} seconds")
        return False
    
    def get_query_results(self, execution_id: str, max_results: int = 100) -> Optional[List[Dict]]:
        """Get query results."""
        try:
            response = self.athena_client.get_query_results(
                QueryExecutionId=execution_id,
                MaxResults=max_results
            )
            
            # Extract column names
            columns = [col['Name'] for col in response['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            
            # Extract rows
            rows = []
            for row in response['ResultSet']['Rows'][1:]:  # Skip header row
                row_data = {}
                for i, col in enumerate(columns):
                    row_data[col] = row['Data'][i].get('VarCharValue', '')
                rows.append(row_data)
            
            return rows
            
        except Exception as e:
            print(f"Error getting query results: {e}")
            return None
    
    def show_workgroup_stats(self, workgroup_name: str):
        """Display workgroup statistics and configuration."""
        workgroup_info = self.get_workgroup_info(workgroup_name)
        if not workgroup_info:
            return
        
        print(f"\n=== Workgroup: {workgroup_name} ===")
        print(f"Description: {workgroup_info.get('Description', 'N/A')}")
        print(f"State: {workgroup_info.get('State', 'N/A')}")
        
        config = workgroup_info.get('Configuration', {})
        if config:
            print(f"Result Location: {config.get('ResultConfiguration', {}).get('OutputLocation', 'N/A')}")
            print(f"Enforce Configuration: {config.get('EnforceWorkGroupConfiguration', False)}")
            print(f"Publish CloudWatch Metrics: {config.get('PublishCloudWatchMetrics', False)}")
            
            if 'BytesScannedCutoffPerQuery' in config:
                cutoff_gb = config['BytesScannedCutoffPerQuery'] / (1024**3)
                print(f"Query Size Limit: {cutoff_gb:.1f} GB")


def main():
    """Main function demonstrating Athena workgroup usage."""
    # Configuration - update these values based on your deployment
    PROJECT_NAME = "my-analytics-project"
    ENVIRONMENT = "dev"
    REGION = "us-east-1"
    
    # Initialize Athena runner
    runner = AthenaQueryRunner(region_name=REGION)
    
    # List available workgroups
    print("Available Athena Workgroups:")
    workgroups = runner.list_workgroups(PROJECT_NAME, ENVIRONMENT)
    
    if not workgroups:
        print("No workgroups found. Make sure the CloudFormation stack is deployed.")
        return
    
    for workgroup in workgroups:
        runner.show_workgroup_stats(workgroup)
    
    # Example queries for different workgroups
    sample_queries = {
        f"{PROJECT_NAME}-analytics-{ENVIRONMENT}": [
            "SHOW DATABASES",
            "SELECT current_timestamp as query_time, 'analytics' as workgroup_type"
        ],
        f"{PROJECT_NAME}-reporting-{ENVIRONMENT}": [
            "SHOW DATABASES",
            "SELECT current_timestamp as query_time, 'reporting' as workgroup_type"
        ],
        f"{PROJECT_NAME}-adhoc-{ENVIRONMENT}": [
            "SHOW DATABASES",
            "SELECT current_timestamp as query_time, 'adhoc' as workgroup_type"
        ]
    }
    
    # Run sample queries
    print("\n" + "="*60)
    print("Running Sample Queries")
    print("="*60)
    
    for workgroup, queries in sample_queries.items():
        if workgroup in workgroups:
            print(f"\n--- Testing workgroup: {workgroup} ---")
            
            for query in queries:
                print(f"Executing: {query}")
                execution_id = runner.run_query(
                    query=query,
                    workgroup=workgroup,
                    wait_for_completion=True
                )
                
                if execution_id:
                    results = runner.get_query_results(execution_id)
                    if results:
                        print(f"Results ({len(results)} rows):")
                        for row in results[:5]:  # Show first 5 rows
                            print(f"  {row}")
                        if len(results) > 5:
                            print(f"  ... and {len(results) - 5} more rows")
                    else:
                        print("No results returned")
                print()


if __name__ == "__main__":
    main()