#!/usr/bin/env python3
"""
AWS CDK Stack for MCP Server Infrastructure

Deploys all necessary infrastructure for MCP server deployment to AgentCore Runtime:
- S3 bucket for deployment packages
- ECR repository for Docker images
- IAM execution role
- CloudWatch log group
- SNS notifications
- SSM parameters for configuration

Usage:
    cdk deploy --context environment=dev --context project=mcp-server
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as logs,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_ssm as ssm,
)
from constructs import Construct


class McpInfrastructureStack(Stack):
    """
    CDK Stack for MCP Server Infrastructure.
    
    Creates all resources needed to deploy an MCP server to AgentCore Runtime.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        project_name: str = "mcp-server",
        environment: str = "dev",
        deployment_method: str = "s3",
        enable_oauth: bool = False,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.project_name = project_name
        self.environment = environment
        self.deployment_method = deployment_method

        # Create S3 bucket for deployment packages
        self.deployment_bucket = self._create_deployment_bucket()

        # Create ECR repository if using Docker deployment
        self.ecr_repository = None
        if deployment_method == "docker":
            self.ecr_repository = self._create_ecr_repository()

        # Create IAM execution role
        self.execution_role = self._create_execution_role()

        # Create CloudWatch log group
        self.log_group = self._create_log_group()

        # Create SNS topic for notifications
        self.notification_topic = self._create_notification_topic()

        # Create CloudWatch alarms
        self._create_alarms()

        # Create SSM parameters
        self._create_ssm_parameters()

        # Output important values
        self._create_outputs()

    def _create_deployment_bucket(self) -> s3.Bucket:
        """Create S3 bucket for deployment packages."""
        bucket = s3.Bucket(
            self,
            "DeploymentBucket",
            bucket_name=f"{self.project_name}-{self.environment}-deployments-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30),
                    enabled=True,
                ),
                s3.LifecycleRule(
                    id="DeleteOldDeployments",
                    expiration=Duration.days(90),
                    prefix="mcp-server/",
                    enabled=True,
                ),
            ],
        )

        return bucket

    def _create_ecr_repository(self) -> ecr.Repository:
        """Create ECR repository for Docker images."""
        repository = ecr.Repository(
            self,
            "ContainerRepository",
            repository_name=f"{self.project_name}-{self.environment}",
            image_scan_on_push=True,
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            encryption=ecr.RepositoryEncryption.AES_256,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10,
                    rule_priority=1,
                )
            ],
        )

        return repository

    def _create_execution_role(self) -> iam.Role:
        """Create IAM execution role for AgentCore Runtime."""
        role = iam.Role(
            self,
            "AgentCoreExecutionRole",
            role_name=f"{self.project_name}-{self.environment}-agentcore-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="Execution role for AgentCore Runtime",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
        )

        # Grant S3 access to deployment bucket
        self.deployment_bucket.grant_read(role)

        # Grant ECR access if using Docker
        if self.ecr_repository:
            self.ecr_repository.grant_pull(role)

        # Add Bedrock access
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/*"
                ],
            )
        )

        # Add Secrets Manager access
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{self.project_name}/{self.environment}/*"
                ],
            )
        )

        return role

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group."""
        log_group = logs.LogGroup(
            self,
            "AgentCoreLogGroup",
            log_group_name=f"/aws/bedrock-agentcore/{self.project_name}-{self.environment}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN,
        )

        return log_group

    def _create_notification_topic(self) -> sns.Topic:
        """Create SNS topic for deployment notifications."""
        topic = sns.Topic(
            self,
            "DeploymentNotificationTopic",
            topic_name=f"{self.project_name}-{self.environment}-deployments",
            display_name="MCP Server Deployment Notifications",
        )

        return topic

    def _create_alarms(self):
        """Create CloudWatch alarms."""
        # Error alarm
        error_alarm = cloudwatch.Alarm(
            self,
            "AgentCoreErrorAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-errors",
            alarm_description="Alert when AgentCore runtime has errors",
            metric=cloudwatch.Metric(
                namespace="AWS/BedrockAgentCore",
                metric_name="Errors",
                dimensions_map={
                    "RuntimeName": f"{self.project_name}-{self.environment}"
                },
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            evaluation_periods=1,
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Add alarm action
        error_alarm.add_alarm_action(
            cw_actions.SnsAction(self.notification_topic)
        )

    def _create_ssm_parameters(self):
        """Create SSM parameters for configuration."""
        # Runtime ARN (placeholder, updated after deployment)
        ssm.StringParameter(
            self,
            "RuntimeArnParameter",
            parameter_name=f"/{self.project_name}/{self.environment}/runtime-arn",
            string_value="pending-deployment",
            description="AgentCore Runtime ARN (updated after deployment)",
        )

        # Deployment bucket
        ssm.StringParameter(
            self,
            "DeploymentBucketParameter",
            parameter_name=f"/{self.project_name}/{self.environment}/deployment-bucket",
            string_value=self.deployment_bucket.bucket_name,
            description="S3 bucket for deployment packages",
        )

        # Execution role ARN
        ssm.StringParameter(
            self,
            "ExecutionRoleArnParameter",
            parameter_name=f"/{self.project_name}/{self.environment}/execution-role-arn",
            string_value=self.execution_role.role_arn,
            description="IAM execution role ARN for AgentCore",
        )

    def _create_outputs(self):
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "DeploymentBucketName",
            value=self.deployment_bucket.bucket_name,
            description="S3 bucket for deployment packages",
            export_name=f"{self.project_name}-{self.environment}-deployment-bucket",
        )

        CfnOutput(
            self,
            "DeploymentBucketArn",
            value=self.deployment_bucket.bucket_arn,
            description="S3 bucket ARN",
            export_name=f"{self.project_name}-{self.environment}-deployment-bucket-arn",
        )

        if self.ecr_repository:
            CfnOutput(
                self,
                "ContainerRepositoryUri",
                value=self.ecr_repository.repository_uri,
                description="ECR repository URI for Docker images",
                export_name=f"{self.project_name}-{self.environment}-ecr-uri",
            )

        CfnOutput(
            self,
            "ExecutionRoleArn",
            value=self.execution_role.role_arn,
            description="IAM execution role ARN for AgentCore Runtime",
            export_name=f"{self.project_name}-{self.environment}-execution-role-arn",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch log group for AgentCore Runtime",
            export_name=f"{self.project_name}-{self.environment}-log-group",
        )

        CfnOutput(
            self,
            "NotificationTopicArn",
            value=self.notification_topic.topic_arn,
            description="SNS topic for deployment notifications",
            export_name=f"{self.project_name}-{self.environment}-notification-topic",
        )

        # Deployment command example
        deployment_command = f"""
# For S3 deployment:
python deployment/s3-direct/deploy_s3.py \\
  --bucket {self.deployment_bucket.bucket_name} \\
  --role-arn {self.execution_role.role_arn} \\
  --runtime-name {self.project_name}-{self.environment} \\
  --region {self.region}
"""

        CfnOutput(
            self,
            "DeploymentCommand",
            value=deployment_command.strip(),
            description="Example deployment command",
        )
