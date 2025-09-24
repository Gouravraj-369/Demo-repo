#!/bin/bash

# AWS CloudFormation deployment script for Athena workgroups
# Usage: ./deploy.sh <environment> [aws-profile] [aws-region]

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
TEMPLATE_FILE="athena-workgroups-cloudformation.yaml"
PARAMETERS_FILE="parameters-${ENVIRONMENT}.json"

echo "Deploying Athena workgroups CloudFormation stack..."
echo "Environment: ${ENVIRONMENT}"
echo "Stack Name: ${STACK_NAME}"
echo "AWS Profile: ${AWS_PROFILE}"
echo "AWS Region: ${AWS_REGION}"
echo "Parameters File: ${PARAMETERS_FILE}"

# Check if files exist
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: Template file $TEMPLATE_FILE not found"
    exit 1
fi

if [[ ! -f "$PARAMETERS_FILE" ]]; then
    echo "Error: Parameters file $PARAMETERS_FILE not found"
    exit 1
fi

# Set AWS profile and region
export AWS_PROFILE=$AWS_PROFILE
export AWS_DEFAULT_REGION=$AWS_REGION

# Validate the template
echo "Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body file://$TEMPLATE_FILE

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
    echo "Stack exists. Updating..."
    OPERATION="update-stack"
    WAIT_CONDITION="stack-update-complete"
else
    echo "Stack does not exist. Creating..."
    OPERATION="create-stack"
    WAIT_CONDITION="stack-create-complete"
fi

# Deploy the stack
echo "Deploying stack..."
aws cloudformation $OPERATION \
    --stack-name $STACK_NAME \
    --template-body file://$TEMPLATE_FILE \
    --parameters file://$PARAMETERS_FILE \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags \
        Key=Environment,Value=$ENVIRONMENT \
        Key=ManagedBy,Value=CloudFormation \
        Key=Purpose,Value=AthenaWorkgroups

# Wait for completion
echo "Waiting for stack operation to complete..."
aws cloudformation wait $WAIT_CONDITION --stack-name $STACK_NAME

# Get stack outputs
echo "Stack operation completed successfully!"
echo ""
echo "Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' \
    --output table

echo ""
echo "Deployment completed successfully!"
echo "You can now use the Athena workgroups in the AWS console or programmatically."