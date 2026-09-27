"""Stack de rede do CapiWatt na AWS (issue #106, topic-network, i9-integration).

VPC propria em 2 AZs, sem NAT:

- subnets publicas: ALB e tasks Fargate (IP publico usado so para saida:
  Bedrock, JWKS do Cognito, SSM/ECS Exec, ECR, CloudWatch Logs);
- subnets privadas isoladas, sem rota para a internet: RDS Postgres,
  dominio OpenSearch e mount targets do EFS.

Security groups encadeados (quem fala com quem):
internet (so a prefix list de origem do CloudFront) -> ``alb-sg`` ->
``backend-sg`` -> (``db-sg``:5432, ``ai-sg``:8000); ``ai-sg`` ->
``search-sg``:443; backend e ``ai`` -> ``efs-sg``:2049. Nenhuma task aceita
trafego que nao venha do SG da camada anterior. Acesso administrativo por
ECS Exec/SSM, sem porta de entrada e sem chave SSH.

POSTURA DE SEGURANCA - ECONOMIA CONSCIENTE, NAO DESCONHECIMENTO
(Eduardo, 2026-09-26, i9-integration). As escolhas de rede abaixo foram
feitas para economizar num ambiente de hackathon de 72 h e nao devem ser
lidas como desconhecimento de seguranca. O time sabe o que um sistema
seguro exigiria e optou por nao pagar por isso aqui. Numa implantacao
real, o minimo seria:

- computacao (backend, ``ai``) em subnets privadas, com saida por NAT
  Gateway ou VPC endpoints (``bedrock-runtime``, ``s3``, ``ecr``, ``logs``,
  ``ssm``), sem IP publico em nenhuma task;
- HTTPS com dominio e certificado ACM proprios, CloudFront e WAF na frente;
- RDS Multi-AZ, com backups e retencao, criptografia com chave KMS
  gerenciada pelo cliente e credenciais rotacionadas no Secrets Manager;
- VPC Flow Logs, CloudTrail com retencao, GuardDuty e alarmes;
- OpenSearch com fine-grained access control e sem acesso fora da VPC.

O trecho CloudFront -> ALB e HTTP:80, dentro desta mesma postura.
"""

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

APP_PORT = 8000

# Managed prefix list ``com.amazonaws.global.cloudfront.origin-facing``: o ID
# e fixo por regiao (nao por conta). Se o app mudar de regiao, adicionar aqui
# (``aws ec2 describe-managed-prefix-lists --filters
# Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing``).
CLOUDFRONT_ORIGIN_FACING_PREFIX_LIST = {
    "us-west-2": "pl-82a045eb",
    "us-east-1": "pl-3b927c52",
}


class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
                ),
            ],
        )

        def sg(name: str, description: str, allow_all_outbound: bool) -> ec2.SecurityGroup:
            return ec2.SecurityGroup(
                self,
                name,
                vpc=self.vpc,
                security_group_name=f"capiwatt-{name}",
                description=description,
                allow_all_outbound=allow_all_outbound,
            )

        self.alb_sg = sg("alb-sg", "ALB publico: so a origem do CloudFront entra", False)
        self.backend_sg = sg("backend-sg", "Tasks do backend: so o ALB entra", True)
        self.ai_sg = sg("ai-sg", "Tasks do ai: so o backend entra", True)
        self.db_sg = sg("db-sg", "RDS Postgres: so o backend entra", False)
        self.search_sg = sg("search-sg", "OpenSearch: so o ai entra", False)
        self.efs_sg = sg("efs-sg", "EFS /data/documents: so backend e ai entram", False)

        self.alb_sg.add_ingress_rule(
            ec2.Peer.prefix_list(CLOUDFRONT_ORIGIN_FACING_PREFIX_LIST[self.region]),
            ec2.Port.tcp(80),
            "so a origem do CloudFront",
        )

        app_port = ec2.Port.tcp(APP_PORT)
        self.alb_sg.add_egress_rule(self.backend_sg, app_port, "ALB -> backend")
        self.backend_sg.add_ingress_rule(self.alb_sg, app_port, "ALB -> backend")
        self.ai_sg.add_ingress_rule(self.backend_sg, app_port, "backend -> ai")
        self.db_sg.add_ingress_rule(self.backend_sg, ec2.Port.tcp(5432), "backend -> Postgres")
        self.search_sg.add_ingress_rule(self.ai_sg, ec2.Port.tcp(443), "ai -> OpenSearch")
        for peer, label in ((self.backend_sg, "backend"), (self.ai_sg, "ai")):
            self.efs_sg.add_ingress_rule(peer, ec2.Port.tcp(2049), f"{label} -> EFS")
