# AWS Athena Workgroup CloudFormation Template

This CloudFormation template creates a complete AWS Athena setup with proper S3 bucket configuration for query results and spill data management.

## Features

- **Athena Workgroup**: Configured with proper settings for query execution
- **S3 Buckets**: Separate buckets for query results, spill data, and data catalog
- **IAM Roles**: Service and user roles with appropriate permissions
- **Encryption**: Configurable encryption options (SSE-S3, SSE-KMS, CSE-KMS)
- **Lifecycle Management**: Automatic cleanup of old query results and spill data
- **CloudWatch Integration**: Query execution logging and monitoring
- **Glue Data Catalog**: Database for organizing your data

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Athena        │    │   S3 Buckets     │    │   IAM Roles     │
│   Workgroup     │◄──►│                  │◄──►│                 │
│                 │    │ • Query Results  │    │ • Service Role  │
│ • Query Config  │    │ • Spill Data     │    │ • User Role     │
│ • Result Config │    │ • Data Catalog   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   CloudWatch     │
                    │                  │
                    │ • Query Logs     │
                    │ • Metrics        │
                    └──────────────────┘
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- CloudFormation deployment permissions
- S3 bucket creation permissions
- IAM role creation permissions

## Deployment

### 1. Basic Deployment

```bash
aws cloudformation create-stack \
  --stack-name athena-workgroup-dev \
  --template-body file://athena-workgroup-template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=dev \
               ParameterKey=WorkgroupName,ParameterValue=analytics-workgroup \
               ParameterKey=QueryResultsBucketName,ParameterValue=athena-query-results \
               ParameterKey=SpillBucketName,ParameterValue=athena-spill-data \
  --capabilities CAPABILITY_NAMED_IAM
```

### 2. Production Deployment with KMS Encryption

```bash
aws cloudformation create-stack \
  --stack-name athena-workgroup-prod \
  --template-body file://athena-workgroup-template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=prod \
               ParameterKey=WorkgroupName,ParameterValue=analytics-workgroup \
               ParameterKey=EnableQueryResultEncryption,ParameterValue=SSE_KMS \
               ParameterKey=EnableSpillEncryption,ParameterValue=SSE_KMS \
               ParameterKey=KMSKeyId,ParameterValue=alias/athena-encryption-key \
               ParameterKey=MaxQueryExecutionTime,ParameterValue=60 \
               ParameterKey=BytesScannedCutoffPerQuery,ParameterValue=5000000000 \
  --capabilities CAPABILITY_NAMED_IAM
```

### 3. Using AWS Console

1. Go to AWS CloudFormation console
2. Click "Create stack" → "With new resources"
3. Upload the template file
4. Configure parameters as needed
5. Review and create the stack

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Environment | String | dev | Environment name (dev/staging/prod) |
| WorkgroupName | String | analytics-workgroup | Name of the Athena workgroup |
| QueryResultsBucketName | String | athena-query-results | S3 bucket name for query results |
| SpillBucketName | String | athena-spill-data | S3 bucket name for spill data |
| DataCatalogBucketName | String | athena-data-catalog | S3 bucket name for data catalog |
| EnableQueryResultEncryption | String | SSE_S3 | Encryption type for query results |
| EnableSpillEncryption | String | SSE_S3 | Encryption type for spill data |
| KMSKeyId | String | '' | KMS Key ID for encryption |
| MaxQueryExecutionTime | Number | 30 | Max query execution time (minutes) |
| BytesScannedCutoffPerQuery | Number | 1000000000 | Max bytes scanned per query |
| RequesterPays | String | false | Use requester pays for S3 access |

## Usage Examples

### 1. Querying Data with Athena

```sql
-- Use the workgroup
USE workgroup analytics-workgroup-dev;

-- Query data from your S3 bucket
SELECT 
    column1,
    column2,
    COUNT(*) as record_count
FROM your_table_name
WHERE date_column >= '2024-01-01'
GROUP BY column1, column2
ORDER BY record_count DESC;
```

### 2. Creating Tables in Glue Data Catalog

```sql
-- Create external table pointing to your S3 data
CREATE EXTERNAL TABLE IF NOT EXISTS sales_data (
    order_id string,
    customer_id string,
    product_id string,
    order_date date,
    amount decimal(10,2)
)
PARTITIONED BY (
    year string,
    month string
)
STORED AS PARQUET
LOCATION 's3://your-data-catalog-bucket/sales-data/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');
```

### 3. Using AWS CLI with the Workgroup

```bash
# Start a query execution
aws athena start-query-execution \
  --query-string "SELECT * FROM your_table LIMIT 10" \
  --work-group analytics-workgroup-dev \
  --result-configuration OutputLocation=s3://athena-query-results-dev-123456789012/query-results/

# Get query execution status
aws athena get-query-execution \
  --query-execution-id 12345678-1234-1234-1234-123456789012

# Get query results
aws athena get-query-results \
  --query-execution-id 12345678-1234-1234-1234-123456789012
```

### 4. Using boto3 (Python)

```python
import boto3

# Initialize Athena client
athena_client = boto3.client('athena')

# Start query execution
response = athena_client.start_query_execution(
    QueryString='SELECT * FROM your_table LIMIT 10',
    WorkGroup='analytics-workgroup-dev',
    ResultConfiguration={
        'OutputLocation': 's3://athena-query-results-dev-123456789012/query-results/'
    }
)

query_execution_id = response['QueryExecutionId']

# Wait for query to complete
import time
while True:
    response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
    status = response['QueryExecution']['Status']['State']
    
    if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
        break
    
    time.sleep(5)

# Get results if successful
if status == 'SUCCEEDED':
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    for row in results['ResultSet']['Rows']:
        print(row)
```

## Monitoring and Troubleshooting

### CloudWatch Metrics

The template enables CloudWatch metrics for the workgroup. Monitor:

- `DataScannedInBytes`: Amount of data scanned
- `EngineExecutionTimeInMillis`: Query execution time
- `QueryQueueTimeInMillis`: Time queries wait in queue
- `TotalExecutionTimeInMillis`: Total time including queue time

### Common Issues

1. **Access Denied Errors**
   - Verify IAM roles have correct S3 permissions
   - Check bucket policies allow Athena access
   - Ensure workgroup is using correct result location

2. **Query Timeouts**
   - Increase `MaxQueryExecutionTime` parameter
   - Optimize queries to scan less data
   - Consider partitioning your data

3. **High Costs**
   - Monitor `BytesScannedCutoffPerQuery` setting
   - Use columnar formats (Parquet, ORC)
   - Implement data partitioning

### Cost Optimization

1. **Use Columnar Formats**: Parquet and ORC reduce data scanned
2. **Implement Partitioning**: Partition by date, region, etc.
3. **Set Query Limits**: Use `BytesScannedCutoffPerQuery`
4. **Lifecycle Policies**: Automatically delete old results
5. **Compression**: Use Snappy or Gzip compression

## Security Best Practices

1. **Encryption**: Use KMS encryption for sensitive data
2. **Access Control**: Limit IAM permissions to minimum required
3. **VPC Endpoints**: Use VPC endpoints for private access
4. **Audit Logging**: Enable CloudTrail for API calls
5. **Data Classification**: Tag resources appropriately

## Cleanup

To delete all resources:

```bash
aws cloudformation delete-stack --stack-name athena-workgroup-dev
```

**Note**: This will delete all S3 buckets and their contents. Ensure you have backups of important data.

## Support

For issues or questions:
1. Check CloudFormation stack events
2. Review CloudWatch logs
3. Verify IAM permissions
4. Check S3 bucket policies

## License

This template is provided as-is for educational and production use.