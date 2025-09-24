#!/bin/bash

# AWS Athena Workgroup CloudFormation Deployment Script
# This script helps deploy the Athena workgroup template with different configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is installed and configured"
}

# Function to validate template
validate_template() {
    local template_file=$1
    print_status "Validating CloudFormation template..."
    
    if aws cloudformation validate-template --template-body file://$template_file &> /dev/null; then
        print_success "Template validation successful"
    else
        print_error "Template validation failed"
        exit 1
    fi
}

# Function to deploy stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local parameters_file=$3
    local environment=$4
    
    print_status "Deploying stack: $stack_name"
    
    if [ -f "$parameters_file" ]; then
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body file://"$template_file" \
            --parameters file://"$parameters_file" \
            --capabilities CAPABILITY_NAMED_IAM \
            --tags Key=Environment,Value="$environment" Key=Project,Value=AthenaWorkgroup
    else
        print_error "Parameters file not found: $parameters_file"
        exit 1
    fi
    
    print_status "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    
    if [ $? -eq 0 ]; then
        print_success "Stack $stack_name created successfully"
        show_outputs "$stack_name"
    else
        print_error "Stack creation failed"
        exit 1
    fi
}

# Function to show stack outputs
show_outputs() {
    local stack_name=$1
    print_status "Stack outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
}

# Function to create parameters file for environment
create_parameters_file() {
    local environment=$1
    local parameters_file="parameters-${environment}.json"
    
    case $environment in
        "dev")
            cat > "$parameters_file" << EOF
{
  "Parameters": {
    "Environment": "dev",
    "WorkgroupName": "analytics-workgroup",
    "QueryResultsBucketName": "athena-query-results",
    "SpillBucketName": "athena-spill-data",
    "DataCatalogBucketName": "athena-data-catalog",
    "EnableQueryResultEncryption": "SSE_S3",
    "EnableSpillEncryption": "SSE_S3",
    "KMSKeyId": "",
    "MaxQueryExecutionTime": "30",
    "BytesScannedCutoffPerQuery": "1000000000",
    "RequesterPays": "false"
  }
}
EOF
            ;;
        "staging")
            cat > "$parameters_file" << EOF
{
  "Parameters": {
    "Environment": "staging",
    "WorkgroupName": "analytics-workgroup",
    "QueryResultsBucketName": "athena-query-results",
    "SpillBucketName": "athena-spill-data",
    "DataCatalogBucketName": "athena-data-catalog",
    "EnableQueryResultEncryption": "SSE_S3",
    "EnableSpillEncryption": "SSE_S3",
    "KMSKeyId": "",
    "MaxQueryExecutionTime": "45",
    "BytesScannedCutoffPerQuery": "2000000000",
    "RequesterPays": "false"
  }
}
EOF
            ;;
        "prod")
            cat > "$parameters_file" << EOF
{
  "Parameters": {
    "Environment": "prod",
    "WorkgroupName": "analytics-workgroup",
    "QueryResultsBucketName": "athena-query-results",
    "SpillBucketName": "athena-spill-data",
    "DataCatalogBucketName": "athena-data-catalog",
    "EnableQueryResultEncryption": "SSE_KMS",
    "EnableSpillEncryption": "SSE_KMS",
    "KMSKeyId": "alias/athena-encryption-key",
    "MaxQueryExecutionTime": "60",
    "BytesScannedCutoffPerQuery": "5000000000",
    "RequesterPays": "false"
  }
}
EOF
            ;;
        *)
            print_error "Invalid environment: $environment. Use dev, staging, or prod"
            exit 1
            ;;
    esac
    
    print_success "Created parameters file: $parameters_file"
}

# Function to delete stack
delete_stack() {
    local stack_name=$1
    
    print_warning "This will delete the stack: $stack_name"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deleting stack: $stack_name"
        aws cloudformation delete-stack --stack-name "$stack_name"
        
        print_status "Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name"
        
        if [ $? -eq 0 ]; then
            print_success "Stack $stack_name deleted successfully"
        else
            print_error "Stack deletion failed"
            exit 1
        fi
    else
        print_status "Stack deletion cancelled"
    fi
}

# Function to show help
show_help() {
    echo "AWS Athena Workgroup CloudFormation Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  deploy [ENVIRONMENT]    Deploy stack for environment (dev/staging/prod)"
    echo "  delete [STACK_NAME]     Delete the specified stack"
    echo "  validate                Validate the CloudFormation template"
    echo "  outputs [STACK_NAME]    Show stack outputs"
    echo "  help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy dev           Deploy development environment"
    echo "  $0 deploy prod          Deploy production environment"
    echo "  $0 delete athena-workgroup-dev"
    echo "  $0 outputs athena-workgroup-prod"
    echo ""
}

# Main script logic
main() {
    local command=$1
    local argument=$2
    
    # Check AWS CLI
    check_aws_cli
    
    case $command in
        "deploy")
            if [ -z "$argument" ]; then
                print_error "Environment not specified. Use: dev, staging, or prod"
                exit 1
            fi
            
            local template_file="athena-workgroup-template.yaml"
            local stack_name="athena-workgroup-${argument}"
            local parameters_file="parameters-${argument}.json"
            
            # Create parameters file if it doesn't exist
            if [ ! -f "$parameters_file" ]; then
                create_parameters_file "$argument"
            fi
            
            validate_template "$template_file"
            deploy_stack "$stack_name" "$template_file" "$parameters_file" "$argument"
            ;;
        "delete")
            if [ -z "$argument" ]; then
                print_error "Stack name not specified"
                exit 1
            fi
            delete_stack "$argument"
            ;;
        "validate")
            validate_template "athena-workgroup-template.yaml"
            ;;
        "outputs")
            if [ -z "$argument" ]; then
                print_error "Stack name not specified"
                exit 1
            fi
            show_outputs "$argument"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"