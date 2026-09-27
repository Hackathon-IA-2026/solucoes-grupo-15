"""Stack de computacao do CapiWatt na AWS (issue #106, topic-backend-entry,
topic-aws-observability, ADR-0002).

- Cluster ECS com dois servicos Fargate a partir dos Dockerfiles existentes
  (imagens publicadas pelo ``cdk deploy``): backend 0,5 vCPU/1 GB e ``ai``
  1 vCPU/2 GB, tasks nas subnets publicas com IP publico so para saida.
- backend -> ``ai`` por ECS Service Connect (``AI_BASE_URL=http://ai:8000``,
  igual ao Compose). EFS em ``/data/documents`` nas duas tasks.
- ``ai`` com ``EMBEDDER=bedrock``: a task role so pode ``bedrock:InvokeModel``
  no Titan Embed V2 de us-east-1 (``ai/app/embeddings.py`` fixa a regiao) e
  le a tabela DynamoDB da #83.
- ALB HTTP:80 (so a prefix list de origem do CloudFront entra, ver
  ``alb-sg``) -> backend, health check em ``/v1/health``. ECS Exec
  habilitado no backend (ingestao e port forwarding ao RDS/OpenSearch).
- Logs: driver ``awslogs`` em ``/capiwatt/backend`` e ``/capiwatt/ai``,
  retencao de 3 dias.
- CloudFront: uma distribuicao, entrada publica unica. ``/v1/*`` -> ALB
  sem cache (CachingDisabled) e com AllViewerExceptHostHeader (repassa
  ``Authorization``, query string e corpo). O comportamento padrao aponta
  provisoriamente para o mesmo ALB; o ticket do frontend o troca pelo S3.
- Neste ticket o backend roda com ``AUTH_MODE=none`` (login Cognito e outro
  ticket): nao deixar o ambiente de pe entre sessoes.
"""

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from capiwatt_infra.data_stack import DB_NAME, DataStack
from capiwatt_infra.network_stack import APP_PORT, NetworkStack

HACKATHON_DIR = Path(__file__).resolve().parents[2]
DOCUMENTS_MOUNT = "/data/documents"
DOCUMENTS_VOLUME = "documents-data"
# Titan Embed V2 em us-east-1: a regiao vem de ai/app/embeddings.py (REGION).
TITAN_V2_ARN = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        network: NetworkStack,
        data: DataStack,
        code_reference: str = "unknown",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = network.vpc
        public = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            default_cloud_map_namespace=ecs.CloudMapNamespaceOptions(
                name="capiwatt.local", use_for_service_connect=True
            ),
        )

        def log_group(service: str) -> logs.LogGroup:
            return logs.LogGroup(
                self,
                f"{service}-logs",
                log_group_name=f"/capiwatt/{service}",
                retention=logs.RetentionDays.THREE_DAYS,
                removal_policy=RemovalPolicy.DESTROY,
            )

        def task_definition(service: str, cpu: int, memory: int) -> ecs.FargateTaskDefinition:
            task = ecs.FargateTaskDefinition(
                self,
                f"{service}-task",
                cpu=cpu,
                memory_limit_mib=memory,
                runtime_platform=ecs.RuntimePlatform(
                    cpu_architecture=ecs.CpuArchitecture.X86_64,
                    operating_system_family=ecs.OperatingSystemFamily.LINUX,
                ),
            )
            task.add_volume(
                name=DOCUMENTS_VOLUME,
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=data.documents_fs.file_system_id,
                    transit_encryption="ENABLED",
                    authorization_config=ecs.AuthorizationConfig(iam="ENABLED"),
                ),
            )
            data.documents_fs.grant_root_access(task.task_role)
            return task

        def add_container(
            task: ecs.FargateTaskDefinition,
            service: str,
            environment: dict[str, str],
            secrets: dict[str, ecs.Secret] | None = None,
        ) -> ecs.ContainerDefinition:
            container = task.add_container(
                service,
                image=ecs.ContainerImage.from_asset(
                    str(HACKATHON_DIR / service), platform=ecr_assets.Platform.LINUX_AMD64
                ),
                port_mappings=[ecs.PortMapping(container_port=APP_PORT, name=service)],
                environment=environment,
                secrets=secrets,
                logging=ecs.LogDriver.aws_logs(stream_prefix=service, log_group=log_group(service)),
            )
            container.add_mount_points(
                ecs.MountPoint(
                    source_volume=DOCUMENTS_VOLUME,
                    container_path=DOCUMENTS_MOUNT,
                    read_only=False,
                )
            )
            return container

        # --- ai ---
        ai_task = task_definition("ai", cpu=1024, memory=2048)
        add_container(
            ai_task,
            "ai",
            {
                "EMBEDDER": "bedrock",
                "OPENSEARCH_URL": f"https://{data.search.domain_endpoint}:443",
                "DOCUMENTS_DIR": DOCUMENTS_MOUNT,
                "DYNAMODB_TABLE_PROCESS_THEMES": data.process_themes.table_name,
                "AWS_REGION": self.region,
            },
        )
        ai_task.task_role.add_to_principal_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=[TITAN_V2_ARN])
        )
        data.process_themes.grant_read_data(ai_task.task_role)
        self.ai_service = ecs.FargateService(
            self,
            "ai-service",
            cluster=cluster,
            task_definition=ai_task,
            desired_count=1,
            min_healthy_percent=0,
            assign_public_ip=True,
            vpc_subnets=public,
            security_groups=[network.ai_sg],
            circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True),
            service_connect_configuration=ecs.ServiceConnectProps(
                services=[
                    ecs.ServiceConnectService(port_mapping_name="ai", dns_name="ai", port=APP_PORT)
                ]
            ),
        )

        # --- backend ---
        db_secret = secretsmanager.Secret.from_secret_complete_arn(
            self, "CatalogSecret", data.db_secret_arn
        )
        backend_task = task_definition("backend", cpu=512, memory=1024)
        add_container(
            backend_task,
            "backend",
            {
                "AI_BASE_URL": f"http://ai:{APP_PORT}",
                "EMBEDDER": "bedrock",
                "MAILER": "preview",
                "AUTH_MODE": "none",
                "DB_HOST": data.db.attr_endpoint_address,
                "DB_PORT": data.db.attr_endpoint_port,
                "DB_NAME": DB_NAME,
                "CODE_REFERENCE": code_reference,
            },
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(db_secret, "username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password"),
            },
        )
        self.backend_service = ecs.FargateService(
            self,
            "backend-service",
            cluster=cluster,
            task_definition=backend_task,
            desired_count=1,
            min_healthy_percent=0,
            assign_public_ip=True,
            vpc_subnets=public,
            security_groups=[network.backend_sg],
            enable_execute_command=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True),
            service_connect_configuration=ecs.ServiceConnectProps(),
        )
        # O backend so resolve ``ai`` depois que o servico ``ai`` existe no namespace.
        self.backend_service.node.add_dependency(self.ai_service)

        # --- ALB ---
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=public,
            security_group=network.alb_sg,
        )
        listener = self.alb.add_listener(
            "Http", port=80, protocol=elbv2.ApplicationProtocol.HTTP, open=False
        )
        listener.add_targets(
            "Backend",
            port=APP_PORT,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[
                self.backend_service.load_balancer_target(
                    container_name="backend", container_port=APP_PORT
                )
            ],
            health_check=elbv2.HealthCheck(path="/v1/health", healthy_http_codes="200"),
            deregistration_delay=Duration.seconds(10),
        )

        # --- CloudFront ---
        alb_origin = origins.LoadBalancerV2Origin(
            self.alb, protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY
        )
        api_behavior = cloudfront.BehaviorOptions(
            origin=alb_origin,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        )
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment="CapiWatt TB1 (issue #106)",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            # Provisorio: o ticket do frontend troca o padrao pelo S3 (OAC).
            default_behavior=api_behavior,
            additional_behaviors={"/v1/*": api_behavior},
        )
        CfnOutput(self, "CloudFrontUrl", value=f"https://{self.distribution.domain_name}")
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)
        CfnOutput(self, "BackendServiceName", value=self.backend_service.service_name)
