"""Frontend estatico na mesma distribuicao CloudFront da API (issue #107,
topic-frontend-hosting, i9-integration).

- Bucket S3 privado (bloqueio de acesso publico total), lido so pela
  distribuicao via OAC no comportamento padrao. ``/v1/*`` continua no ALB.
- Fallback de SPA por CloudFront Function (``spa_rewrite.js``) no
  viewer-request do comportamento padrao, e nao por error responses
  globais da distribuicao: essas trocariam tambem os 403/404 da API pelo
  ``index.html``.
- Publicacao pelo ``cdk deploy``: o asset do frontend roda ``npm run build``
  (bundling local; Docker ``node`` so se nao houver ``npm``) e dois
  ``BucketDeployment`` publicam ``dist/``: JS/CSS com hash do Vite
  (``assets/*.js|css``) com cache longo, e o resto (``index.html``, imagens
  de ``public/`` sem hash e o ``config.json``) com ``no-cache`` e invalidacao
  da distribuicao.
- ``cdk destroy`` sem sobras: o bucket e esvaziado no delete
  (``auto_delete_objects``) e as duas Lambdas de custom resource (publicacao
  e esvaziamento) logam num log group do stack com retencao de 3 dias, em
  vez do ``/aws/lambda/*`` que a Lambda criaria sem retencao e que
  sobraria depois do destroy.
- ``config.json`` gerado aqui. Sem os campos de Cognito (login e outro
  ticket), o app abre no modo demo.
"""

import shutil
import subprocess
from pathlib import Path

import jsii
from aws_cdk import BundlingOptions, DockerImage, ILocalBundling, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

SPA_REWRITE_JS = Path(__file__).with_name("spa_rewrite.js")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
# Saida do Vite com hash no nome; as imagens de public/assets nao tem hash.
HASHED_ASSETS = ["assets/*.js", "assets/*.css"]
LONG_CACHE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"


@jsii.implements(ILocalBundling)
class _NpmBuild:
    """``npm ci`` (se faltar ``node_modules``) e ``npm run build`` direto no
    diretorio de saida do asset."""

    def try_bundle(self, output_dir: str, *args, **kwargs) -> bool:
        npm = shutil.which("npm")
        if npm is None:
            return False
        if not (FRONTEND_DIR / "node_modules").is_dir():
            subprocess.run([npm, "ci"], cwd=FRONTEND_DIR, check=True)
        subprocess.run(
            [npm, "run", "build", "--", "--outDir", output_dir, "--emptyOutDir"],
            cwd=FRONTEND_DIR,
            check=True,
        )
        return True


def frontend_build() -> s3deploy.ISource:
    return s3deploy.Source.asset(
        str(FRONTEND_DIR),
        exclude=["node_modules", "dist", "coverage", "*.tsbuildinfo"],
        bundling=BundlingOptions(
            image=DockerImage.from_registry("node:22-alpine"),
            command=[
                "sh",
                "-c",
                "npm ci --cache /tmp/npm && npm run build -- --outDir /asset-output --emptyOutDir",
            ],
            local=_NpmBuild(),
        ),
    )


class FrontendSite(Construct):
    """Bucket do frontend e o comportamento padrao da distribuicao."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        self.bucket = s3.Bucket(
            self,
            "Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        self.handler_logs = logs.LogGroup(
            self,
            "HandlerLogs",
            log_group_name="/capiwatt/frontend-deploy",
            retention=logs.RetentionDays.THREE_DAYS,
            removal_policy=RemovalPolicy.DESTROY,
        )
        _log_auto_delete_handler_to(self.handler_logs, Stack.of(self))
        spa_rewrite = cloudfront.Function(
            self,
            "SpaRewrite",
            code=cloudfront.FunctionCode.from_file(file_path=str(SPA_REWRITE_JS)),
            runtime=cloudfront.FunctionRuntime.JS_2_0,
            comment="CapiWatt: caminho sem extensao -> /index.html",
        )
        self.default_behavior = cloudfront.BehaviorOptions(
            origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            function_associations=[
                cloudfront.FunctionAssociation(
                    function=spa_rewrite, event_type=cloudfront.FunctionEventType.VIEWER_REQUEST
                )
            ],
        )

    def publish(self, distribution: cloudfront.IDistribution) -> None:
        """Publica o build e o ``config.json`` no bucket e invalida a distribuicao."""
        build = frontend_build()
        assets = s3deploy.BucketDeployment(
            self,
            "HashedAssets",
            sources=[build],
            destination_bucket=self.bucket,
            exclude=["*"],
            include=HASHED_ASSETS,
            cache_control=[s3deploy.CacheControl.from_string(LONG_CACHE)],
            log_group=self.handler_logs,
            # Assets antigos ficam: uma aba com o index.html anterior ainda os pede.
            prune=False,
        )
        shell = s3deploy.BucketDeployment(
            self,
            "Shell",
            sources=[build, s3deploy.Source.json_data("config.json", runtime_config(self))],
            destination_bucket=self.bucket,
            exclude=HASHED_ASSETS,
            cache_control=[s3deploy.CacheControl.from_string(NO_CACHE)],
            log_group=self.handler_logs,
            distribution=distribution,
            distribution_paths=["/*"],
        )
        shell.node.add_dependency(assets)


def runtime_config(scope: Construct) -> dict[str, str]:
    """``/config.json`` do frontend (spec #101). Sem ``userPoolId`` e
    ``userPoolClientId`` o app fica no modo demo."""
    return {"region": Stack.of(scope).region}


def _log_auto_delete_handler_to(log_group: logs.ILogGroup, stack: Stack) -> None:
    """O provider do ``auto_delete_objects`` nao aceita log group; a Lambda
    dele (singleton do stack) recebe o ``LoggingConfig`` por override."""
    provider = stack.node.find_child("Custom::S3AutoDeleteObjectsCustomResourceProvider")
    handler = provider.node.find_child("Handler")
    handler.add_property_override("LoggingConfig", {"LogGroup": log_group.log_group_name})
    handler.node.add_dependency(log_group)
