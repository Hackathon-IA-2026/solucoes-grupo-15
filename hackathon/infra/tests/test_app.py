"""Testes do app CDK inteiro (issue #106) com ``aws_cdk.assertions``.

O app e sintetizado uma vez por modulo, exatamente como o ``cdk synth``
faz (``build_app``), e cada teste le o template de um stack.
"""

import re

import pytest
from aws_cdk import App
from aws_cdk.assertions import Match, Template

from capiwatt_infra import build_app


@pytest.fixture(scope="module")
def stacks():
    app = App()
    return build_app(app)


@pytest.fixture(scope="module")
def network(stacks):
    return Template.from_stack(stacks.network)


@pytest.fixture(scope="module")
def data(stacks):
    return Template.from_stack(stacks.data)


def _isolated_subnet_logical_ids(network: Template) -> set[str]:
    subnets = network.find_resources(
        "AWS::EC2::Subnet",
        {
            "Properties": {
                "Tags": Match.array_with([{"Key": "aws-cdk:subnet-type", "Value": "Isolated"}])
            }
        },
    )
    return set(subnets)


def _referenced_subnets(value, stacks) -> set[str]:
    """Resolve Fn::ImportValue de subnets exportadas pelo stack de rede."""
    found = set()
    if isinstance(value, dict):
        if "Fn::ImportValue" in value:
            found.add(str(value["Fn::ImportValue"]))
        for v in value.values():
            found |= _referenced_subnets(v, stacks)
    elif isinstance(value, list):
        for v in value:
            found |= _referenced_subnets(v, stacks)
    return found


def _exports_for(network: Template, logical_ids: set[str]) -> set[str]:
    outputs = network.to_json().get("Outputs", {})
    names = set()
    for out in outputs.values():
        ref = out.get("Value", {}).get("Ref")
        if ref in logical_ids:
            names.add(out["Export"]["Name"])
    return names


def test_rds_lives_in_isolated_subnets_and_is_not_public(stacks, network, data):
    isolated_exports = _exports_for(network, _isolated_subnet_logical_ids(network))
    assert isolated_exports, "o stack de rede precisa exportar as subnets isoladas"

    data.has_resource_properties(
        "AWS::RDS::DBInstance",
        {"PubliclyAccessible": False, "Engine": "postgres", "DBInstanceClass": "db.t4g.micro"},
    )
    groups = data.find_resources("AWS::RDS::DBSubnetGroup")
    assert len(groups) == 1
    (group,) = groups.values()
    used = _referenced_subnets(group["Properties"]["SubnetIds"], stacks)
    assert used and used <= isolated_exports


def test_opensearch_lives_in_isolated_subnet_without_public_endpoint(stacks, network, data):
    isolated_exports = _exports_for(network, _isolated_subnet_logical_ids(network))
    domains = data.find_resources("AWS::OpenSearchService::Domain")
    assert len(domains) == 1
    (domain,) = domains.values()
    vpc_options = domain["Properties"].get("VPCOptions")
    assert vpc_options, "domínio sem VPCOptions teria endpoint público"
    used = _referenced_subnets(vpc_options["SubnetIds"], stacks)
    assert used and used <= isolated_exports
    assert domain["Properties"]["EngineVersion"] == "OpenSearch_2.19"
    assert domain["Properties"]["ClusterConfig"]["InstanceType"] == "t3.small.search"
    assert domain["Properties"]["ClusterConfig"]["InstanceCount"] == 1


@pytest.fixture(scope="module")
def compute(stacks):
    return Template.from_stack(stacks.compute)


# Prefix list gerenciada com.amazonaws.global.cloudfront.origin-facing em us-west-2.
_CLOUDFRONT_ORIGIN_FACING_US_WEST_2 = "pl-82a045eb"


def _security_group_logical_id(network: Template, name: str) -> str:
    groups = network.find_resources("AWS::EC2::SecurityGroup", {"Properties": {"GroupName": name}})
    assert len(groups) == 1, name
    return next(iter(groups))


def test_alb_accepts_ingress_only_from_the_cloudfront_prefix_list(network, compute):
    alb_sg = _security_group_logical_id(network, "capiwatt-alb-sg")
    ingress = network.to_json()["Resources"][alb_sg]["Properties"].get("SecurityGroupIngress", [])
    standalone = [
        {k: v for k, v in r["Properties"].items() if k != "GroupId"}
        for r in network.find_resources("AWS::EC2::SecurityGroupIngress").values()
        if r["Properties"]["GroupId"] == {"Fn::GetAtt": [alb_sg, "GroupId"]}
    ]
    rules = ingress + standalone
    assert rules == [
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "SourcePrefixListId": _CLOUDFRONT_ORIGIN_FACING_US_WEST_2,
            "Description": "so a origem do CloudFront",
        }
    ]

    lbs = compute.find_resources("AWS::ElasticLoadBalancingV2::LoadBalancer")
    assert len(lbs) == 1
    (lb,) = lbs.values()
    assert lb["Properties"]["Scheme"] == "internet-facing"
    # O ALB so usa o alb-sg (importado do stack de rede).
    assert len(lb["Properties"]["SecurityGroups"]) == 1
    compute.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener", {"Port": 80, "Protocol": "HTTP"}
    )
    # Nenhum SG criado no stack de computacao abre porta para a internet.
    assert not compute.find_resources("AWS::EC2::SecurityGroup")


def _container(compute: Template, name: str) -> dict:
    for td in compute.find_resources("AWS::ECS::TaskDefinition").values():
        for c in td["Properties"]["ContainerDefinitions"]:
            if c["Name"] == name:
                return c
    raise AssertionError(f"container {name} nao encontrado")


def _env(container: dict) -> dict:
    return {e["Name"]: e["Value"] for e in container.get("Environment", [])}


def test_rds_credentials_reach_the_backend_as_ecs_secrets_not_env(data, compute):
    backend = _container(compute, "backend")
    env = _env(backend)
    assert "DB_USER" not in env and "DB_PASSWORD" not in env and "DATABASE_URL" not in env
    assert {"DB_HOST", "DB_PORT", "DB_NAME"} <= env.keys()
    assert env["AUTH_MODE"] == "none"

    secrets = {s["Name"]: s["ValueFrom"] for s in backend["Secrets"]}
    assert set(secrets) == {"DB_USER", "DB_PASSWORD"}
    (db_logical_id,) = data.find_resources("AWS::RDS::DBInstance")
    for key, value_from in (("DB_USER", "username"), ("DB_PASSWORD", "password")):
        joined = str(secrets[key])
        # ValueFrom = <ARN do segredo gerenciado pelo RDS>:<chave>:: (importado do stack de dados)
        assert "Fn::ImportValue" in joined
        assert f":{value_from}::" in joined
    exported = [
        o["Value"]
        for o in data.to_json()["Outputs"].values()
        if o["Value"] == {"Fn::GetAtt": [db_logical_id, "MasterUserSecret.SecretArn"]}
    ]
    assert exported, "o ARN do segredo do RDS precisa vir do atributo MasterUserSecret"


def _policy_statements(template: Template) -> list[dict]:
    statements = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        statements += policy["Properties"]["PolicyDocument"]["Statement"]
    return statements


def _actions(statement: dict) -> list[str]:
    action = statement["Action"]
    return action if isinstance(action, list) else [action]


def test_bedrock_invoke_is_allowed_only_on_titan_v2_in_us_east_1(stacks):
    bedrock = []
    for stack in stacks.all:
        for st in _policy_statements(Template.from_stack(stack)):
            if any(a.startswith("bedrock:") or a == "*" for a in _actions(st)):
                bedrock.append(st)
    assert bedrock == [
        {
            "Action": "bedrock:InvokeModel",
            "Effect": "Allow",
            "Resource": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
        }
    ]


def test_service_log_groups_keep_three_days(compute):
    groups = {
        g["Properties"]["LogGroupName"]: g["Properties"].get("RetentionInDays")
        for g in compute.find_resources("AWS::Logs::LogGroup").values()
    }
    assert groups == {"/capiwatt/backend": 3, "/capiwatt/ai": 3}


def _all_templates(stacks) -> list[tuple[str, Template]]:
    return [(s.stack_name, Template.from_stack(s)) for s in stacks.all]


def test_no_resource_is_retained_on_destroy(stacks):
    retained = []
    for name, template in _all_templates(stacks):
        for logical_id, resource in template.to_json()["Resources"].items():
            for policy in ("DeletionPolicy", "UpdateReplacePolicy"):
                if resource.get(policy, "Delete") != "Delete":
                    retained.append((name, logical_id, policy, resource[policy]))
    assert retained == []
    # Todo log group do app tem retencao (nenhum "nunca expira").
    for _, template in _all_templates(stacks):
        for group in template.find_resources("AWS::Logs::LogGroup").values():
            assert group["Properties"].get("RetentionInDays"), group


def test_no_literal_account_id_in_any_template(stacks):
    import json
    import re

    for name, template in _all_templates(stacks):
        body = json.dumps(template.to_json())
        assert not re.search(r"(?<![0-9A-Za-z])\d{12}(?![0-9A-Za-z])", body), name
        assert stacks.network.account.startswith("${Token"), "a conta nao pode ser fixada no app"


# IDs das managed policies da AWS (globais, documentados pela AWS).
_CACHING_DISABLED = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
_ALL_VIEWER_EXCEPT_HOST_HEADER = "b689b0a8-53d0-40ab-baf2-68738e2966ac"


def test_cloudfront_routes_v1_to_the_alb_without_cache(compute):
    distributions = compute.find_resources("AWS::CloudFront::Distribution")
    assert len(distributions) == 1
    (dist,) = distributions.values()
    config = dist["Properties"]["DistributionConfig"]
    (v1,) = (b for b in config["CacheBehaviors"] if b["PathPattern"] == "/v1/*")
    assert v1["CachePolicyId"] == _CACHING_DISABLED
    assert v1["OriginRequestPolicyId"] == _ALL_VIEWER_EXCEPT_HOST_HEADER
    assert set(v1["AllowedMethods"]) >= {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}

    (alb_logical_id,) = compute.find_resources("AWS::ElasticLoadBalancingV2::LoadBalancer")
    (origin,) = (o for o in config["Origins"] if o["Id"] == v1["TargetOriginId"])
    assert origin["DomainName"] == {"Fn::GetAtt": [alb_logical_id, "DNSName"]}
    assert origin["CustomOriginConfig"]["OriginProtocolPolicy"] == "http-only"


def test_search_instance_type_can_be_raised_by_context_without_code_change():
    # Plano B da i4: se o k-NN (nmslib) nao rodar no t3.small.search,
    # ``cdk deploy -c search_instance_type=m6g.large.search``.
    app = App(context={"search_instance_type": "m6g.large.search"})
    data = Template.from_stack(build_app(app).data)
    data.has_resource_properties(
        "AWS::OpenSearchService::Domain",
        {"ClusterConfig": Match.object_like({"InstanceType": "m6g.large.search"})},
    )


# Conjunto aceito pela EC2 para descricao de regra e de security group
# (erro real do primeiro ``cdk deploy``: "Invalid rule description").
_EC2_DESCRIPTION = re.compile(r"^[a-zA-Z0-9. _\-:/()#,@\[\]+=&;{}!$*]{0,255}$")


def _security_group_descriptions(template: dict):
    for logical_id, resource in template.get("Resources", {}).items():
        props = resource.get("Properties", {})
        kind = resource["Type"]
        if kind == "AWS::EC2::SecurityGroup":
            yield logical_id, props.get("GroupDescription")
            rules = props.get("SecurityGroupIngress", []) + props.get("SecurityGroupEgress", [])
            for rule in rules:
                yield logical_id, rule.get("Description")
        elif kind in ("AWS::EC2::SecurityGroupIngress", "AWS::EC2::SecurityGroupEgress"):
            yield logical_id, props.get("Description")


def test_security_group_descriptions_use_only_characters_ec2_accepts(stacks):
    invalid = [
        (stack.stack_name, logical_id, description)
        for stack in stacks.all
        for logical_id, description in _security_group_descriptions(
            Template.from_stack(stack).to_json()
        )
        if isinstance(description, str) and not _EC2_DESCRIPTION.match(description)
    ]
    assert invalid == []


def test_opensearch_domain_waits_for_its_service_linked_role(data):
    # Erro real do segundo ``cdk deploy`` numa conta nova do workshop:
    # "you must enable a service-linked role" para dominio em VPC.
    roles = data.find_resources(
        "AWS::IAM::ServiceLinkedRole",
        {"Properties": {"AWSServiceName": "opensearchservice.amazonaws.com"}},
    )
    assert len(roles) == 1
    (role_id,) = roles
    assert roles[role_id].get("DeletionPolicy") == "Delete"
    (domain,) = data.find_resources("AWS::OpenSearchService::Domain").values()
    assert role_id in domain.get("DependsOn", [])


def test_existing_opensearch_service_linked_role_can_be_reused_by_context():
    # Conta que ja tem o role (outro dominio em VPC): nao recriar.
    app = App(context={"opensearch_service_linked_role": "existing"})
    data = Template.from_stack(build_app(app).data)
    data.resource_count_is("AWS::IAM::ServiceLinkedRole", 0)
