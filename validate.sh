#!/bin/bash

# Validation script for Athena workgroups CloudFormation deployment
# Usage: ./validate.sh <environment> [aws-profile] [aws-region]

set -e

# Default values
ENVIRONMENT=${1:-dev}
AWS_PROFILE=${2:-default}
AWS_REGION=${3:-us-east-1}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Environment must be one of: dev, staging, prod"
    exit 1
fi

# Set variables
STACK_NAME="athena-workgroups-${ENVIRONMENT}"

echo "Validating Athena workgroups deployment for environment: ${ENVIRONMENT}"
echo "Stack Name: ${STACK_NAME}"
echo "AWS Profile: ${AWS_PROFILE}"
echo "AWS Region: ${AWS_REGION}"
echo ""

# Set AWS profile and region
export AWS_PROFILE=$AWS_PROFILE
export AWS_DEFAULT_REGION=$AWS_REGION

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
        return 0
    else
        echo -e "${RED}✗ $1${NC}"
        return 1
    fi
}

check_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "1. Checking CloudFormation stack status..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text 2>/dev/null)
if [ "$STACK_STATUS" = "CREATE_COMPLETE" ] || [ "$STACK_STATUS" = "UPDATE_COMPLETE" ]; then
    check_success "CloudFormation stack is in a healthy state: $STACK_STATUS"
else
    echo -e "${RED}✗ CloudFormation stack is not healthy: $STACK_STATUS${NC}"
    exit 1
fi

echo ""
echo "2. Retrieving stack outputs..."

# Get stack outputs
OUTPUTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs')

QUERY_RESULTS_BUCKET=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AthenaQueryResultsBucketName") | .OutputValue')
SPILL_BUCKET=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AthenaSpillBucketName") | .OutputValue')
SERVICE_ROLE_ARN=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AthenaServiceRoleArn") | .OutputValue')
USERS_POLICY_ARN=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AthenaUsersPolicyArn") | .OutputValue')
ANALYTICS_WORKGROUP=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AnalyticsWorkgroupName") | .OutputValue')
REPORTING_WORKGROUP=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="ReportingWorkgroupName") | .OutputValue')
ADHOC_WORKGROUP=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AdhocWorkgroupName") | .OutputValue')

echo "Query Results Bucket: $QUERY_RESULTS_BUCKET"
echo "Spill Bucket: $SPILL_BUCKET"
echo "Analytics Workgroup: $ANALYTICS_WORKGROUP"
echo "Reporting Workgroup: $REPORTING_WORKGROUP"
echo "Ad-hoc Workgroup: $ADHOC_WORKGROUP"

echo ""
echo "3. Validating S3 buckets..."

# Check if S3 buckets exist and are accessible
aws s3 ls s3://$QUERY_RESULTS_BUCKET >/dev/null 2>&1
check_success "Query results bucket is accessible: $QUERY_RESULTS_BUCKET"

aws s3 ls s3://$SPILL_BUCKET >/dev/null 2>&1
check_success "Spill bucket is accessible: $SPILL_BUCKET"

# Check bucket encryption
QUERY_ENCRYPTION=$(aws s3api get-bucket-encryption --bucket $QUERY_RESULTS_BUCKET --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm' --output text 2>/dev/null)
if [ "$QUERY_ENCRYPTION" = "AES256" ]; then
    check_success "Query results bucket has encryption enabled"
else
    check_warning "Query results bucket encryption status unclear: $QUERY_ENCRYPTION"
fi

SPILL_ENCRYPTION=$(aws s3api get-bucket-encryption --bucket $SPILL_BUCKET --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm' --output text 2>/dev/null)
if [ "$SPILL_ENCRYPTION" = "AES256" ]; then
    check_success "Spill bucket has encryption enabled"
else
    check_warning "Spill bucket encryption status unclear: $SPILL_ENCRYPTION"
fi

# Check bucket lifecycle configuration
QUERY_LIFECYCLE=$(aws s3api get-bucket-lifecycle-configuration --bucket $QUERY_RESULTS_BUCKET --query 'Rules[0].Status' --output text 2>/dev/null)
if [ "$QUERY_LIFECYCLE" = "Enabled" ]; then
    check_success "Query results bucket has lifecycle policy enabled"
else
    check_warning "Query results bucket lifecycle policy status unclear"
fi

echo ""
echo "4. Validating IAM resources..."

# Check if IAM role exists
aws iam get-role --role-name "$(basename $SERVICE_ROLE_ARN)" >/dev/null 2>&1
check_success "Athena service role exists"

# Check if managed policy exists
aws iam get-policy --policy-arn $USERS_POLICY_ARN >/dev/null 2>&1
check_success "Athena users policy exists"

echo ""
echo "5. Validating Athena workgroups..."

# Check each workgroup
for workgroup in "$ANALYTICS_WORKGROUP" "$REPORTING_WORKGROUP" "$ADHOC_WORKGROUP"; do
    WORKGROUP_STATE=$(aws athena get-work-group --work-group $workgroup --query 'WorkGroup.State' --output text 2>/dev/null)
    if [ "$WORKGROUP_STATE" = "ENABLED" ]; then
        check_success "Workgroup $workgroup is enabled"
        
        # Check workgroup configuration
        OUTPUT_LOCATION=$(aws athena get-work-group --work-group $workgroup --query 'WorkGroup.Configuration.ResultConfiguration.OutputLocation' --output text 2>/dev/null)
        if [[ "$OUTPUT_LOCATION" == s3://$QUERY_RESULTS_BUCKET/* ]]; then
            check_success "Workgroup $workgroup has correct output location"
        else
            check_warning "Workgroup $workgroup output location: $OUTPUT_LOCATION"
        fi
        
        ENFORCE_CONFIG=$(aws athena get-work-group --work-group $workgroup --query 'WorkGroup.Configuration.EnforceWorkGroupConfiguration' --output text 2>/dev/null)
        if [ "$ENFORCE_CONFIG" = "True" ]; then
            check_success "Workgroup $workgroup has enforced configuration"
        else
            check_warning "Workgroup $workgroup does not enforce configuration"
        fi
    else
        echo -e "${RED}✗ Workgroup $workgroup is not enabled: $WORKGROUP_STATE${NC}"
    fi
done

echo ""
echo "6. Testing basic Athena functionality..."

# Test query execution in analytics workgroup
echo "Testing query execution in $ANALYTICS_WORKGROUP..."
QUERY_ID=$(aws athena start-query-execution \
    --query-string "SELECT 1 as test_query, current_timestamp as execution_time" \
    --work-group $ANALYTICS_WORKGROUP \
    --query 'QueryExecutionId' \
    --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$QUERY_ID" != "None" ]; then
    check_success "Successfully started test query: $QUERY_ID"
    
    # Wait a moment and check query status
    sleep 5
    QUERY_STATUS=$(aws athena get-query-execution --query-execution-id $QUERY_ID --query 'QueryExecution.Status.State' --output text 2>/dev/null)
    
    case $QUERY_STATUS in
        "SUCCEEDED")
            check_success "Test query completed successfully"
            ;;
        "RUNNING"|"QUEUED")
            check_warning "Test query is still running: $QUERY_STATUS"
            ;;
        "FAILED"|"CANCELLED")
            echo -e "${RED}✗ Test query failed: $QUERY_STATUS${NC}"
            FAILURE_REASON=$(aws athena get-query-execution --query-execution-id $QUERY_ID --query 'QueryExecution.Status.StateChangeReason' --output text 2>/dev/null)
            echo "Failure reason: $FAILURE_REASON"
            ;;
        *)
            check_warning "Test query status unknown: $QUERY_STATUS"
            ;;
    esac
else
    echo -e "${RED}✗ Failed to start test query${NC}"
fi

echo ""
echo "7. Checking query result storage..."

# Check if query results are being stored in the right location
if [ "$QUERY_ID" != "None" ] && [ ! -z "$QUERY_ID" ]; then
    sleep 5  # Give some time for results to be stored
    
    # List objects in the analytics folder
    RESULT_COUNT=$(aws s3 ls s3://$QUERY_RESULTS_BUCKET/analytics/ --recursive | wc -l)
    if [ $RESULT_COUNT -gt 0 ]; then
        check_success "Query results are being stored in S3"
    else
        check_warning "No query results found in S3 yet (may take time to appear)"
    fi
fi

echo ""
echo "8. Summary..."

# Final summary
echo -e "${GREEN}Validation completed!${NC}"
echo ""
echo "Stack Resources:"
echo "  - Query Results Bucket: $QUERY_RESULTS_BUCKET"
echo "  - Spill Bucket: $SPILL_BUCKET"
echo "  - Service Role: $SERVICE_ROLE_ARN"
echo "  - Users Policy: $USERS_POLICY_ARN"
echo ""
echo "Workgroups:"
echo "  - Analytics: $ANALYTICS_WORKGROUP"
echo "  - Reporting: $REPORTING_WORKGROUP"
echo "  - Ad-hoc: $ADHOC_WORKGROUP"
echo ""
echo "Next steps:"
echo "1. Attach the users policy to appropriate IAM users/groups"
echo "2. Configure your data sources in AWS Glue Data Catalog"
echo "3. Start running queries in the Athena console or programmatically"
echo ""
echo "For programmatic access, see athena_example.py"