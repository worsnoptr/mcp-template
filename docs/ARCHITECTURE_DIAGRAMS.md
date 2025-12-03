# Architecture Diagrams

Visual architecture diagrams for MCP server deployment patterns, showing both development and production scenarios.

## Table of Contents

- [Overview](#overview)
- [Deployment Flow Diagrams](#deployment-flow-diagrams)
- [Runtime Architecture](#runtime-architecture)
- [Network Architecture](#network-architecture)
- [Multi-Environment Architecture](#multi-environment-architecture)
- [CI/CD Pipeline Architecture](#cicd-pipeline-architecture)

## Overview

This document provides architecture diagrams for various MCP server deployment scenarios using Amazon Bedrock AgentCore Runtime.

## Deployment Flow Diagrams

### S3 Direct File Reference Deployment

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        S3 Direct Deployment Flow                        │
└─────────────────────────────────────────────────────────────────────────┘

Developer            Local Files          S3 Bucket         AgentCore Runtime
    │                    │                    │                    │
    │  1. Make changes   │                    │                    │
    │ ───────────────▶   │                    │                    │
    │                    │                    │                    │
    │  2. Run deploy.py  │                    │                    │
    │ ────────────────────────────────────────────────────────────│
    │                    │                    │                    │
    │                    │  3. Package ZIP    │                    │
    │                    │ ─────────────────▶ │                    │
    │                    │    (src/, reqs)    │                    │
    │                    │                    │                    │
    │                    │  4. Upload to S3   │                    │
    │                    │    (encrypted)     │                    │
    │                    │ ─────────────────▶ │                    │
    │                    │                    │                    │
    │                    │                    │  5. Create/Update  │
    │                    │                    │     Runtime        │
    │                    │                    │ ─────────────────▶ │
    │                    │                    │                    │
    │                    │                    │  6. Download ZIP   │
    │                    │                    │ ◀───────────────── │
    │                    │                    │                    │
    │                    │                    │  7. Extract & Run  │
    │                    │                    │      Python        │
    │                    │                    │ ─────────────────▶ │
    │                    │                    │                    │
    │  8. Deployment     │                    │  9. Status: ACTIVE │
    │     Complete       │                    │ ◀───────────────── │
    │ ◀──────────────────────────────────────────────────────────────────│
    │                    │                    │                    │
    │  10. Validate      │                    │                    │
    │      deployment    │                    │                    │
    │ ─────────────────────────────────────────────────────────────▶│
    │                    │                    │                    │
    │  11. Validation    │                    │                    │
    │      results       │                    │                    │
    │ ◀──────────────────────────────────────────────────────────────────│
    │                    │                    │                    │

Timeline: ~30 seconds total
```

### Docker-Based Deployment

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Docker Deployment Flow                            │
└─────────────────────────────────────────────────────────────────────────┘

Developer     Local Docker     ECR Registry     AgentCore Runtime
    │              │                 │                  │
    │  1. Build    │                 │                  │
    │  ARM64 image │                 │                  │
    │ ──────────▶  │                 │                  │
    │              │                 │                  │
    │              │  2. Build       │                  │
    │              │  complete       │                  │
    │ ◀────────────│  (~2-5 min)     │                  │
    │              │                 │                  │
    │  3. Push to  │                 │                  │
    │     ECR      │                 │                  │
    │ ─────────────────────────────▶ │                  │
    │              │    (~30 sec)    │                  │
    │              │                 │                  │
    │  4. Push     │                 │                  │
    │  complete    │                 │                  │
    │ ◀─────────────────────────────│                  │
    │              │                 │                  │
    │  5. Create/  │                 │                  │
    │     Update   │                 │                  │
    │     Runtime  │                 │                  │
    │ ─────────────────────────────────────────────────▶│
    │              │                 │                  │
    │              │                 │  6. Pull image   │
    │              │                 │ ◀────────────────│
    │              │                 │                  │
    │              │                 │  7. Start        │
    │              │                 │     container    │
    │              │                 │ ─────────────────▶│
    │              │                 │                  │
    │  8. Status   │                 │                  │
    │     ACTIVE   │                 │                  │
    │ ◀─────────────────────────────────────────────────│
    │              │                 │                  │

Timeline: ~3-6 minutes total
```

## Runtime Architecture

### AgentCore Runtime Components

```
┌──────────────────────────────────────────────────────────────────────┐
│                      AgentCore Runtime (ARM64)                       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Network Layer (PUBLIC)                      │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │           API Gateway (HTTPS)                            │  │ │
│  │  │           Port: 443                                      │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   OAuth Authentication                         │ │
│  │          (Optional - Cognito or Auth0)                         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    MCP Server Runtime                          │ │
│  │                                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  FastMCP Server (0.0.0.0:8000)                           │ │ │
│  │  │  - Endpoint: /mcp                                        │ │ │
│  │  │  - Transport: streamable-http                            │ │ │
│  │  │  - Stateless: true                                       │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │                         │                                      │ │
│  │                         ▼                                      │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  Tool Registry                                           │ │ │
│  │  │  - Direct tools (Python functions)                       │ │ │
│  │  │  - OpenAPI tools (auto-generated)                        │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │                         │                                      │ │
│  │                         ▼                                      │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  Business Logic                                          │ │ │
│  │  │  - Tool implementations                                  │ │ │
│  │  │  - External API calls                                    │ │ │
│  │  │  - Data processing                                       │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  Observability Layer                           │ │
│  │  - AWS Distro for OpenTelemetry (ADOT)                         │ │
│  │  - Traces, Metrics, Logs                                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │     Amazon CloudWatch          │
              │  - Logs                        │
              │  - Metrics                     │
              │  - Traces                      │
              │  - Alarms                      │
              └────────────────────────────────┘
```

### Request Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        MCP Request Flow                              │
└──────────────────────────────────────────────────────────────────────┘

Client            AgentCore           MCP Server           Tools
(boto3)            Runtime           (FastMCP)          (Python)
   │                  │                  │                  │
   │  1. invoke_agent_runtime           │                  │
   │  ────────────▶   │                  │                  │
   │  {jsonrpc:2.0,   │                  │                  │
   │   method:        │                  │                  │
   │   tools/call}    │                  │                  │
   │                  │                  │                  │
   │                  │  2. Route to     │                  │
   │                  │     /mcp         │                  │
   │                  │  ──────────────▶ │                  │
   │                  │                  │                  │
   │                  │                  │  3. Parse        │
   │                  │                  │     JSON-RPC     │
   │                  │                  │  ──────────────▶ │
   │                  │                  │                  │
   │                  │                  │  4. Validate     │
   │                  │                  │     params       │
   │                  │                  │ ◀────────────────│
   │                  │                  │                  │
   │                  │                  │  5. Execute      │
   │                  │                  │     tool         │
   │                  │                  │  ──────────────▶ │
   │                  │                  │                  │
   │                  │                  │  6. Result       │
   │                  │                  │ ◀────────────────│
   │                  │                  │                  │
   │                  │  7. JSON-RPC     │                  │
   │                  │     response     │                  │
   │                  │ ◀────────────────│                  │
   │                  │                  │                  │
   │  8. Response     │                  │                  │
   │     stream       │                  │                  │
   │ ◀────────────────│                  │                  │
   │                  │                  │                  │

Total latency: 50-500ms (typical)
```

## Network Architecture

### Public Network Mode

```
┌──────────────────────────────────────────────────────────────────────┐
│                       AWS Cloud (us-west-2)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  VPC (AgentCore Managed)                       │ │
│  │                                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │              Public Subnet (ARM64)                       │ │ │
│  │  │                                                          │ │ │
│  │  │  ┌────────────────────────────────────────────────────┐ │ │ │
│  │  │  │    AgentCore Runtime Container                     │ │ │ │
│  │  │  │    - MCP Server (Port 8000)                        │ │ │ │
│  │  │  │    - Health Check (/ping)                          │ │ │ │
│  │  │  └────────────────────────────────────────────────────┘ │ │ │
│  │  │                       │                                  │ │ │
│  │  └───────────────────────┼──────────────────────────────────┘ │ │
│  │                          │                                    │ │
│  │                          │ Outbound Access                    │ │
│  │                          ▼                                    │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │              Internet Gateway                            │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │      External Services               │
        │  - Bedrock Models                    │
        │  - Third-party APIs                  │
        │  - DynamoDB                          │
        │  - S3                                │
        └─────────────────────────────────────┘
```

### Private Network Mode (VPC)

```
┌──────────────────────────────────────────────────────────────────────┐
│                       AWS Cloud (us-west-2)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Your VPC                                  │ │
│  │                                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │            Private Subnet                                │ │ │
│  │  │                                                          │ │ │
│  │  │  ┌────────────────────────────────────────────────────┐ │ │ │
│  │  │  │    AgentCore Runtime                               │ │ │ │
│  │  │  │    (No direct internet access)                     │ │ │ │
│  │  │  └────────────────────────────────────────────────────┘ │ │ │
│  │  │                       │                                  │ │ │
│  │  └───────────────────────┼──────────────────────────────────┘ │ │
│  │                          │                                    │ │
│  │                          ▼                                    │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │              VPC Endpoints                               │ │ │
│  │  │  - S3 Gateway Endpoint                                   │ │ │
│  │  │  - DynamoDB Gateway Endpoint                             │ │ │
│  │  │  - Bedrock Interface Endpoint                            │ │ │
│  │  │  - Secrets Manager Interface Endpoint                    │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## Multi-Environment Architecture

### Development, Staging, Production

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Multi-Environment Setup                             │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐  ┌─────────────────────────────┐
│       DEVELOPMENT           │  │        STAGING              │
│                             │  │                             │
│  S3 Bucket (Deployments)    │  │  ECR Repository             │
│  ├─ mcp-server/             │  │  ├─ mcp-staging:v1.0       │
│  └─ Quick iterations        │  │  └─ Pre-production testing  │
│            │                │  │            │                │
│            ▼                │  │            ▼                │
│  ┌─────────────────────┐   │  │  ┌─────────────────────┐   │
│  │ AgentCore Runtime   │   │  │  │ AgentCore Runtime   │   │
│  │ - No OAuth          │   │  │  │ - OAuth enabled     │   │
│  │ - Debug logging     │   │  │  │ - Production-like   │   │
│  │ - Rapid deploy      │   │  │  │ - Integration tests │   │
│  └─────────────────────┘   │  │  └─────────────────────┘   │
│                             │  │                             │
│  CloudWatch Logs (7 days)   │  │  CloudWatch Logs (30 days)  │
└─────────────────────────────┘  └─────────────────────────────┘

                    ┌─────────────────────────────┐
                    │       PRODUCTION            │
                    │                             │
                    │  ECR Repository             │
                    │  ├─ mcp-prod:v1.0          │
                    │  ├─ mcp-prod:v1.1          │
                    │  └─ Immutable tags          │
                    │            │                │
                    │            ▼                │
                    │  ┌─────────────────────┐   │
                    │  │ AgentCore Runtime   │   │
                    │  │ - OAuth required    │   │
                    │  │ - WAF protection    │   │
                    │  │ - Auto-scaling      │   │
                    │  │ - Canary deploy     │   │
                    │  └─────────────────────┘   │
                    │                             │
                    │  CloudWatch Logs (90 days)  │
                    │  SNS Alerts                 │
                    │  Blue/Green Deployment      │
                    └─────────────────────────────┘
```

## CI/CD Pipeline Architecture

### Complete Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     CI/CD Pipeline Architecture                          │
└──────────────────────────────────────────────────────────────────────────┘

Developer ──▶ Git Push ──▶ GitHub/GitLab
                                │
                                ▼
                    ┌─────────────────────┐
                    │   Source Control    │
                    │   - Code review     │
                    │   - Branch policy   │
                    └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │   Build Stage       │
                    │   - Install deps    │
                    │   - Compile check   │
                    └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │   Test Stage        │
                    │   - Unit tests      │
                    │   - Lint checks     │
                    │   - Coverage        │
                    └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  Security Scan      │
                    │  - Trivy            │
                    │  - Dependency check │
                    └─────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
    ┌─────────────────────┐       ┌─────────────────────┐
    │  Deploy to Dev      │       │  Build Docker       │
    │  (S3 method)        │       │  (ARM64)            │
    │  - Automatic        │       │  - Multi-stage      │
    └─────────────────────┘       └─────────────────────┘
                │                               │
                ▼                               ▼
    ┌─────────────────────┐       ┌─────────────────────┐
    │  Validate Dev       │       │  Push to ECR        │
    │  - Health checks    │       │  - Staging repo     │
    │  - Smoke tests      │       └─────────────────────┘
    └─────────────────────┘                   │
                                               ▼
                                   ┌─────────────────────┐
                                   │  Deploy Staging     │
                                   │  - Automatic        │
                                   └─────────────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────┐
                                   │  Integration Tests  │
                                   │  - End-to-end       │
                                   │  - Load tests       │
                                   └─────────────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────┐
                                   │  Manual Approval    │
                                   │  (Production gate)  │
                                   └─────────────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────┐
                                   │  Deploy Production  │
                                   │  - Canary deploy    │
                                   │  - Monitor metrics  │
                                   └─────────────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────┐
                                   │  Post-Deploy        │
                                   │  - Validation       │
                                   │  - SNS notification │
                                   │  - Create tag       │
                                   └─────────────────────┘
```

### Deployment Strategies

#### Blue/Green Deployment

```
┌──────────────────────────────────────────────────────────────┐
│              Blue/Green Deployment Strategy                  │
└──────────────────────────────────────────────────────────────┘

Phase 1: Current State
┌────────────────────────┐          ┌────────────────────────┐
│   Blue Environment     │          │   Green Environment    │
│   (v1.0 - ACTIVE)     │          │   (Empty)              │
│   100% Traffic ████   │          │   0% Traffic           │
└────────────────────────┘          └────────────────────────┘

Phase 2: Deploy New Version
┌────────────────────────┐          ┌────────────────────────┐
│   Blue Environment     │          │   Green Environment    │
│   (v1.0 - ACTIVE)     │          │   (v1.1 - TESTING)     │
│   100% Traffic ████   │          │   0% Traffic           │
└────────────────────────┘          └────────────────────────┘
                                              │
                                              ▼
                                    Run validation tests

Phase 3: Switch Traffic
┌────────────────────────┐          ┌────────────────────────┐
│   Blue Environment     │          │   Green Environment    │
│   (v1.0 - STANDBY)    │          │   (v1.1 - ACTIVE)      │
│   0% Traffic           │          │   100% Traffic ████   │
└────────────────────────┘          └────────────────────────┘

Phase 4: Rollback if Needed
┌────────────────────────┐          ┌────────────────────────┐
│   Blue Environment     │          │   Green Environment    │
│   (v1.0 - ACTIVE)     │          │   (v1.1 - FAILED)      │
│   100% Traffic ████   │◀─────────│   0% Traffic           │
└────────────────────────┘  Quick   └────────────────────────┘
                            Switch
```

#### Canary Deployment

```
┌──────────────────────────────────────────────────────────────┐
│               Canary Deployment Strategy                     │
└──────────────────────────────────────────────────────────────┘

Stage 1: Deploy Canary (10%)
┌───────────────────────────────────────────────────┐
│  Production (v1.0)     90% ████████████████████░  │
│  Canary (v1.1)         10% ██░░░░░░░░░░░░░░░░░░  │
└───────────────────────────────────────────────────┘
         │
         ▼ Monitor for 15 minutes
         │ Check: Error rate, latency, success rate

Stage 2: Increase to 25%
┌───────────────────────────────────────────────────┐
│  Production (v1.0)     75% ███████████████░░░░░░  │
│  Canary (v1.1)         25% █████░░░░░░░░░░░░░░░  │
└───────────────────────────────────────────────────┘
         │
         ▼ Monitor for 10 minutes

Stage 3: Increase to 50%
┌───────────────────────────────────────────────────┐
│  Production (v1.0)     50% ██████████░░░░░░░░░░░  │
│  Canary (v1.1)         50% ██████████░░░░░░░░░░░  │
└───────────────────────────────────────────────────┘
         │
         ▼ Monitor for 10 minutes

Stage 4: Full Deployment
┌───────────────────────────────────────────────────┐
│  Production (v1.1)    100% ████████████████████████│
└───────────────────────────────────────────────────┘

If any stage fails: Automatic rollback to 100% v1.0
```

## Data Flow Diagrams

### Tool Invocation with External Services

```
┌──────────────────────────────────────────────────────────────┐
│              Tool with External API Integration              │
└──────────────────────────────────────────────────────────────┘

   Client              AgentCore          MCP Server        External
  (Agent)              Runtime           (Your Tool)         API
     │                    │                   │               │
     │  1. Call tool      │                   │               │
     │ ──────────────────▶│                   │               │
     │                    │                   │               │
     │                    │  2. Route         │               │
     │                    │ ─────────────────▶│               │
     │                    │                   │               │
     │                    │                   │  3. API call  │
     │                    │                   │ ─────────────▶│
     │                    │                   │               │
     │                    │                   │  4. Response  │
     │                    │                   │ ◀─────────────│
     │                    │                   │               │
     │                    │                   │  5. Process   │
     │                    │                   │     data      │
     │                    │                   │ ──────────▶   │
     │                    │                   │               │
     │                    │  6. Return result │               │
     │                    │ ◀─────────────────│               │
     │                    │                   │               │
     │  7. Result         │                   │               │
     │ ◀──────────────────│                   │               │
     │                    │                   │               │

All communication logged in CloudWatch
```

## Summary

These diagrams provide a visual guide to:

1. **Deployment flows** - S3 vs Docker approaches
2. **Runtime architecture** - Internal components
3. **Network topology** - Public vs private modes
4. **Multi-environment** - Dev, staging, production setup
5. **CI/CD pipelines** - Automated deployment flows
6. **Deployment strategies** - Blue/green and canary patterns

Use these diagrams to:
- Plan your deployment architecture
- Communicate with stakeholders
- Train team members
- Document your infrastructure
- Troubleshoot issues

## Related Documentation

- [AgentCore Deployment Guide](./AGENTCORE_DEPLOYMENT_GUIDE.md)
- [Enterprise CI/CD Guide](./ENTERPRISE_CICD_GUIDE.md)
- [S3 Deployment README](../deployment/s3-direct/README.md)
- [CloudFormation Templates](../deployment/cloudformation/)
- [CDK Templates](../deployment/cdk/)
