"""App CDK do CapiWatt na AWS (issue #106, ADR-0002).

``build_app`` monta todos os stacks num ``App`` - usado pelo ``app.py``
(``cdk synth``/``deploy``) e pelos testes, para que os testes verifiquem
exatamente o que vai para a conta. Regiao fixa em us-west-2 (unico
bootstrap ``hnb659fds`` do workshop); a conta nunca e fixada: o template
usa ``AWS::AccountId`` e a conta vem das credenciais no deploy.
"""

import subprocess
from dataclasses import dataclass

from aws_cdk import App, Environment, Stack

from capiwatt_infra.compute_stack import ComputeStack
from capiwatt_infra.data_stack import DataStack
from capiwatt_infra.network_stack import NetworkStack

REGION = "us-west-2"
DEFAULT_SEARCH_INSTANCE_TYPE = "t3.small.search"


@dataclass(frozen=True)
class CapiwattStacks:
    network: NetworkStack
    data: DataStack
    compute: ComputeStack

    @property
    def all(self) -> tuple[Stack, ...]:
        return (self.network, self.data, self.compute)


def _git_code_reference() -> str:
    """Commit atual, gravado em ``SearchExecution`` via ``CODE_REFERENCE``
    (i7-reproducibility): a imagem nao leva ``.git``."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_app(app: App) -> CapiwattStacks:
    env = Environment(region=REGION)
    search_instance_type = (
        app.node.try_get_context("search_instance_type") or DEFAULT_SEARCH_INSTANCE_TYPE
    )
    network = NetworkStack(app, "CapiwattNetwork", env=env)
    data = DataStack(
        app,
        "CapiwattData",
        network=network,
        search_instance_type=search_instance_type,
        create_search_service_linked_role=(
            app.node.try_get_context("opensearch_service_linked_role") != "existing"
        ),
        env=env,
    )
    compute = ComputeStack(
        app,
        "CapiwattCompute",
        network=network,
        data=data,
        code_reference=app.node.try_get_context("code_reference") or _git_code_reference(),
        env=env,
    )
    return CapiwattStacks(network=network, data=data, compute=compute)
