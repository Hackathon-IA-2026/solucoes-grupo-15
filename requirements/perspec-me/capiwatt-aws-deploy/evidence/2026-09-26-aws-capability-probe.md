# Sondagem de capacidades AWS — 2026-09-26

Delegated work `dw-aws-capability-probe`. Credenciais: `.env` (WSParticipantRole, conta nova do workshop — o ID difere do registrado em 2026-09-18, ou seja, **a conta muda entre sessões do workshop**). Todos os recursos `capiwatt-probe-*` / `capiwatt-tfprobe-*` foram criados e destruídos.

## A. Chamada direta com WSParticipantRole (o que o Terraform faria)

| Recurso | Resultado |
|---|---|
| VPC padrão (describe) | existe em us-east-1 e us-west-2, subnets públicas em todas as AZs |
| ec2 CreateVpc / CreateSubnet / CreateSecurityGroup / Authorize ingress / IGW / VPC endpoint / ENI / RunInstances | **negado** |
| ec2 DescribeSecurityGroups / DescribeVpcAttribute | **negado** (quebra até `data "aws_vpc"` do Terraform) |
| S3 bucket + website + policy pública | ok |
| IAM CreateRole / AttachRolePolicy / PutRolePolicy | ok |
| iam:PassRole | só `WSParticipantRole`, ou qualquer papel para `ecs`/`ec2`/`bedrock`/`bedrock-agentcore`/`elasticfilesystem` — **não** para `ecs-tasks` nem `lambda` |
| ECS CreateCluster | ok; RegisterTaskDefinition com papel → **negado** (PassRole para `ecs-tasks`) |
| Lambda com WSParticipantRole | **inviável** — "role cannot be assumed by Lambda"; com papel próprio → negado |
| ECR CreateRepository | ok; GetAuthorizationToken → **negado** (sem `docker push` direto) |
| EFS CreateFileSystem | ok |
| Cognito User Pool + client SRP + domínio + AdminCreateUser | ok |
| OpenSearch domain (es:*) | autorizado (validação) |
| RDS CreateDBInstance, ELBv2, CloudFront, API Gateway v2, App Runner, Secrets Manager | **negado** |
| SSM PutParameter, CloudWatch Logs | ok |
| `terraform apply`/`destroy` S3 + Cognito (us-west-2) | ok |
| `terraform apply` com `data "aws_vpc" default` | **falha** (DescribeVpcAttribute 403) |

## B. CloudFormation via bootstrap do CDK (us-west-2)

- Bootstrap `cdk-hnb659fds-*` existe **só em us-west-2** (não há `CDKToolkit` em us-east-1).
- `cdk-hnb659fds-cfn-exec-role` = **AdministratorAccess**; `deploy-role` assumível pelo participante (`DenyRoleChaining` exclui `cdk-*`).
- Stack `capiwatt-probe` (assume deploy-role → `create-stack --role-arn cfn-exec-role`): **CREATE_COMPLETE** com VPC própria + 2 subnets, security group na VPC padrão, RDS DBSubnetGroup, **ALB internet-facing**, **CloudFront OriginAccessControl**, papel IAM + **Lambda + Function URL (HTTP 200)**, papel `ecs-tasks` + **ECS TaskDefinition Fargate**.
- Stack `capiwatt-probe-rds`: VPC + 2 subnets privadas + **RDS Postgres 16 db.t4g.micro** (`ManageMasterUserPassword`, sem acesso público) → **CREATE_COMPLETE**, depois apagado.

## Conclusão

O inventário descreve as permissões **diretas** do participante. Pelo caminho que ele próprio indica ("via CloudFormation ou CDK"), a execução roda como administrador em us-west-2, e VPC, SG, RDS, ALB, CloudFront, Lambda e ECS com papéis funcionam. Nenhum SCP bloqueou esses serviços no teste.
