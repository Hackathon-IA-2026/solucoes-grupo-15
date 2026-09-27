"""Stack de dados do CapiWatt na AWS (issue #106, topic-catalog-db-hosting,
topic-vector-index-hosting, i4-storage).

- RDS Postgres 16 ``db.t4g.micro``, 20 GB gp3, uma AZ, sem backup, senha
  gerenciada pelo RDS (``ManageMasterUserPassword``, segredo no Secrets
  Manager com as chaves ``username``/``password``). L1 de proposito: o L2
  gera o proprio segredo, e a decisao e a senha gerenciada pelo RDS.
- OpenSearch 2.19, um no (``search_instance_type``, padrao
  ``t3.small.search``), 10 GB gp3, sem FGAC; access policy aberta ao
  principal ``*`` e restrita pelo ``search-sg`` (o cliente do ``ai`` nao
  assina requisicoes). Engine ``nmslib`` exige 2.x - nao subir para 3.x
  sem revisar o codigo do ``ai``.
- EFS para ``/data/documents`` (mesmo contrato do volume do Compose).
- Tabela DynamoDB da #83 (``tipo_processo`` + GSI ``GSI_Tema``).

Todo recurso usa ``RemovalPolicy.DESTROY``: a conta do workshop dura 72 h
e o seed (``POST /v1/ingestions``) recria catalogo e indice.
"""

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs
from aws_cdk import aws_opensearchservice as opensearch
from aws_cdk import aws_rds as rds
from constructs import Construct

from capiwatt_infra.network_stack import NetworkStack

DB_NAME = "capiwatt"
DB_USER = "capiwatt"
SEARCH_DOMAIN_NAME = "capiwatt-search"


class DataStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        network: NetworkStack,
        search_instance_type: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = network.vpc
        isolated = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)

        # --- RDS Postgres (catalogo) ---
        subnet_group = rds.CfnDBSubnetGroup(
            self,
            "DbSubnets",
            db_subnet_group_description="CapiWatt: subnets isoladas do catalogo",
            subnet_ids=isolated.subnet_ids,
        )
        subnet_group.apply_removal_policy(RemovalPolicy.DESTROY)
        self.db = rds.CfnDBInstance(
            self,
            "Catalog",
            engine="postgres",
            engine_version="16",
            db_instance_class="db.t4g.micro",
            allocated_storage="20",
            storage_type="gp3",
            storage_encrypted=True,
            multi_az=False,
            publicly_accessible=False,
            backup_retention_period=0,
            delete_automated_backups=True,
            deletion_protection=False,
            db_name=DB_NAME,
            master_username=DB_USER,
            manage_master_user_password=True,
            db_subnet_group_name=subnet_group.ref,
            vpc_security_groups=[network.db_sg.security_group_id],
        )
        self.db.apply_removal_policy(RemovalPolicy.DESTROY)
        self.db_secret_arn = self.db.attr_master_user_secret_secret_arn

        # --- OpenSearch (indice vetorial do ai) ---
        self.search = opensearch.Domain(
            self,
            "Search",
            domain_name=SEARCH_DOMAIN_NAME,
            version=opensearch.EngineVersion.OPENSEARCH_2_19,
            capacity=opensearch.CapacityConfig(
                data_nodes=1,
                data_node_instance_type=search_instance_type,
                multi_az_with_standby_enabled=False,
            ),
            ebs=opensearch.EbsOptions(volume_size=10, volume_type=ec2.EbsDeviceVolumeType.GP3),
            zone_awareness=opensearch.ZoneAwarenessConfig(enabled=False),
            vpc=vpc,
            vpc_subnets=[ec2.SubnetSelection(subnets=[isolated.subnets[0]])],
            security_groups=[network.search_sg],
            enforce_https=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # Access policy direto no L1: a prop ``access_policies`` do L2 cria
        # um custom resource (Lambda) so para isso.
        domain_arn = self.format_arn(
            service="es", resource="domain", resource_name=SEARCH_DOMAIN_NAME
        )
        self.search.node.default_child.access_policies = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "es:ESHttp*",
                    "Resource": f"{domain_arn}/*",
                }
            ],
        }

        # --- EFS (/data/documents compartilhado por backend e ai) ---
        self.documents_fs = efs.FileSystem(
            self,
            "Documents",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_group=network.efs_sg,
            encrypted=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- DynamoDB (classificacao processo -> tema, #83) ---
        self.process_themes = dynamodb.Table(
            self,
            "ProcessThemes",
            partition_key=dynamodb.Attribute(
                name="tipo_processo", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.process_themes.add_global_secondary_index(
            index_name="GSI_Tema",
            partition_key=dynamodb.Attribute(name="tema_id", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
