# Ticket Auto-Processing System

An automated multi-agent system for ticket upgrade processing, deployed on AWS with Amazon AgentCore.

## Architecture Overview

- **Frontend**: React + TypeScript deployed on CloudFront + S3
- **Backend**: Python Lambda functions with API Gateway
- **Agents**: Two AI agents (Ticket Agent + Data Agent) deployed on AgentCore Runtime
- **Database**: Aurora PostgreSQL Serverless with Data API
- **Authentication**: Amazon Cognito
- **Payment**: Dummy payment gateway for testing

## Project Structure

```
├── infrastructure/          # AWS infrastructure setup scripts
├── backend/                # Python Lambda functions and agents
│   ├── agents/             # AgentCore agents
│   ├── lambda/             # Lambda function handlers
│   └── shared/             # Shared utilities and models
├── frontend/               # React application
├── database/               # Database schema and migrations
└── tests/                  # Test suites
```

## Development Setup

1. **Prerequisites**
   - Python 3.10+
   - Node.js 18+
   - AWS CLI configured
   - AgentCore CLI installed

2. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Configure AWS credentials and region
   - Set database and service endpoints

3. **Local Development**
   - Run agents locally with AgentCore dev server
   - Use Aurora PostgreSQL with Data API
   - Test with dummy payment gateway

## Deployment

The system deploys to AWS us-west-2 region with the following services:
- Aurora PostgreSQL Serverless
- Lambda functions
- API Gateway
- AgentCore Runtime
- CloudFront + S3
- Cognito User Pool

## Testing

- **Unit Tests**: Specific examples and edge cases
- **Property Tests**: Universal correctness properties using Hypothesis
- **Integration Tests**: Multi-agent workflows and end-to-end scenarios