# AWS Athena Workgroups CloudFormation Template

This CloudFormation template creates AWS Athena workgroups with properly configured S3 buckets for storing query results and spill data, along with the necessary IAM roles and policies.

## Architecture Overview

The template creates:

### S3 Buckets
- **Query Results Bucket**: Stores Athena query results with configurable lifecycle policies
- **Spill Bucket**: Stores intermediate spill data during large query processing

### Athena Workgroups
- **Analytics Workgroup**: For business intelligence and analytics queries
- **Reporting Workgroup**: For scheduled reports and automated queries
- **Ad-hoc Workgroup**: For exploratory queries with query size limits

### IAM Resources
- **Service Role**: For Athena service to access S3 buckets and Glue catalog
- **User Policy**: Managed policy that can be attached to users/groups for Athena access

### Security Features
- S3 buckets with encryption at rest (AES-256)
- Public access blocked on all buckets
- Proper IAM policies with least privilege access
- Versioning enabled on buckets

## Files Included

- `athena-workgroups-cloudformation.yaml` - Main CloudFormation template
- `parameters-dev.json` - Parameters for development environment
- `parameters-prod.json` - Parameters for production environment
- `deploy.sh` - Deployment script
- `README.md` - This documentation

## Parameters

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|--------------|
| `Environment` | Environment name | `dev` | `dev`, `staging`, `prod` |
| `ProjectName` | Project name for resource naming | `my-project` | Any string |
| `WorkgroupNames` | Comma-delimited list of workgroups | `analytics,reporting,adhoc` | Comma-separated strings |
| `QueryResultsRetentionDays` | Days to retain query results | `30` | Number |
| `SpillDataRetentionDays` | Days to retain spill data | `7` | Number |
| `EnableCloudWatchLogs` | Enable CloudWatch logging | `true` | `true`, `false` |

## Deployment

### Prerequisites

1. AWS CLI installed and configured
2. Appropriate AWS permissions to create:
   - S3 buckets
   - IAM roles and policies
   - Athena workgroups
   - CloudWatch log groups

### Quick Deployment

```bash
# Deploy to development environment
./deploy.sh dev

# Deploy to production environment with specific profile and region
./deploy.sh prod my-aws-profile us-west-2
```

### Manual Deployment

```bash
# Validate template
aws cloudformation validate-template \
    --template-body file://athena-workgroups-cloudformation.yaml

# Create stack
aws cloudformation create-stack \
    --stack-name athena-workgroups-dev \
    --template-body file://athena-workgroups-cloudformation.yaml \
    --parameters file://parameters-dev.json \
    --capabilities CAPABILITY_NAMED_IAM

# Update existing stack
aws cloudformation update-stack \
    --stack-name athena-workgroups-dev \
    --template-body file://athena-workgroups-cloudformation.yaml \
    --parameters file://parameters-dev.json \
    --capabilities CAPABILITY_NAMED_IAM
```

## Usage

### Using Workgroups

After deployment, you can use the workgroups in several ways:

#### AWS Console
1. Navigate to Athena in the AWS Console
2. Select the appropriate workgroup from the dropdown
3. Run your queries

#### AWS CLI
```bash
# Run query in analytics workgroup
aws athena start-query-execution \
    --query-string "SELECT * FROM your_table LIMIT 10" \
    --work-group "my-project-analytics-dev"
```

#### Python (boto3)
```python
import boto3

client = boto3.client('athena')

response = client.start_query_execution(
    QueryString='SELECT * FROM your_table LIMIT 10',
    WorkGroup='my-project-analytics-dev'
)
```

### Attaching User Policies

To grant users access to the Athena workgroups:

```bash
# Get the policy ARN from stack outputs
POLICY_ARN=$(aws cloudformation describe-stacks \
    --stack-name athena-workgroups-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`AthenaUsersPolicyArn`].OutputValue' \
    --output text)

# Attach to user
aws iam attach-user-policy \
    --user-name your-username \
    --policy-arn $POLICY_ARN

# Or attach to group
aws iam attach-group-policy \
    --group-name your-group-name \
    --policy-arn $POLICY_ARN
```

## Workgroup Configuration Details

### Analytics Workgroup
- **Purpose**: Business intelligence and analytics queries
- **Result Location**: `s3://bucket/analytics/`
- **Spill Location**: `s3://spill-bucket/analytics-spill/`
- **Features**: CloudWatch metrics enabled, enforced configuration

### Reporting Workgroup
- **Purpose**: Scheduled reports and automated queries
- **Result Location**: `s3://bucket/reporting/`
- **Spill Location**: `s3://spill-bucket/reporting-spill/`
- **Features**: CloudWatch metrics enabled, enforced configuration

### Ad-hoc Workgroup
- **Purpose**: Exploratory queries and development
- **Result Location**: `s3://bucket/adhoc/`
- **Spill Location**: `s3://spill-bucket/adhoc-spill/`
- **Features**: 1GB query limit, CloudWatch metrics enabled

## Cost Optimization

### S3 Lifecycle Policies
- Query results are automatically deleted after the configured retention period
- Spill data is deleted more frequently (default: 7 days)
- Incomplete multipart uploads are cleaned up after 1 day

### Query Limits
- Ad-hoc workgroup has a 1GB scan limit to prevent costly queries
- Consider implementing additional query limits based on your needs

## Monitoring

### CloudWatch Metrics
All workgroups publish metrics to CloudWatch:
- Query execution time
- Data scanned
- Query success/failure rates

### CloudWatch Logs
Optional CloudWatch log group for additional logging (configurable via parameter)

## Security Best Practices

1. **S3 Bucket Security**
   - Public access blocked
   - Encryption at rest
   - Versioning enabled
   - Lifecycle policies for cost optimization

2. **IAM Security**
   - Least privilege access
   - Separate service and user policies
   - No wildcard permissions on sensitive actions

3. **Workgroup Security**
   - Enforced configurations prevent users from overriding settings
   - Separate workgroups for different use cases
   - Query result encryption enabled

## Customization

### Adding New Workgroups
To add additional workgroups, copy one of the existing workgroup resources in the template and modify:
- Name and description
- Result and spill locations
- Any specific configuration requirements

### Modifying Retention Policies
Adjust the `QueryResultsRetentionDays` and `SpillDataRetentionDays` parameters based on your compliance and cost requirements.

### Additional Security
Consider adding:
- KMS encryption instead of S3-managed encryption
- VPC endpoints for enhanced security
- Additional IAM conditions for more granular access control

## Troubleshooting

### Common Issues

1. **Bucket Name Conflicts**
   - S3 bucket names must be globally unique
   - The template uses account ID to help ensure uniqueness
   - Modify the `ProjectName` parameter if conflicts occur

2. **Permission Errors**
   - Ensure your AWS credentials have the necessary permissions
   - Check that the IAM role/user has CloudFormation permissions

3. **Query Failures**
   - Verify the workgroup configuration
   - Check S3 bucket permissions
   - Ensure Glue catalog access is properly configured

### Stack Outputs

The template provides several outputs that you can reference:
- S3 bucket names
- IAM role and policy ARNs
- Workgroup names
- CloudWatch log group name

## Cleanup

To delete the stack and all resources:

```bash
aws cloudformation delete-stack --stack-name athena-workgroups-dev
```

**Note**: S3 buckets must be empty before the stack can be deleted. You may need to manually empty the buckets if they contain data.