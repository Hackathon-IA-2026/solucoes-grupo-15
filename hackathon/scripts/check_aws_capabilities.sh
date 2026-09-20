 #!/usr/bin/env bash
# check_aws_capabilities.sh — diagnóstico NÃO destrutivo da conta do hackathon (CapiWatt Lens MVP)
# Só list/describe/get/simulate. Não cria, altera nem exclui recursos. Não altera IAM.
# Não imprime credenciais: apenas indica se variáveis/perfil estão definidos.
set -u
export AWS_PAGER=""
REGIONS=("us-east-1" "us-west-2")
EMBED_MODELS=("amazon.titan-embed-text-v2:0" "cohere.embed-multilingual-v3" "amazon.titan-embed-text-v1")
MAXOUT=6000

run() {  # run "<serviço>" "<região|global>" "<o que comprova>" comando...
local svc="$1" region="$2" note="$3"; shift 3
echo; echo "=================================================================="
echo "SERVIÇO : $svc"; echo "REGIÃO  : $region"
echo "COMANDO : $*"; echo "COMPROVA: $note"
echo "------------------------------------------------------------------"
local out rc
out="$("$@" 2>&1)"; rc=$?
printf '%s\n' "$out" | head -c "$MAXOUT"
[ "${#out}" -gt "$MAXOUT" ] && echo "... [saída truncada em $MAXOUT caracteres]"
echo "------------------------------------------------------------------"
if [ $rc -eq 0 ]; then echo "RESULTADO: exit=0 OK"; else echo "RESULTADO: exit=$rc FALHOU"; fi
}

echo "#################### CapiWatt — check_aws_capabilities ####################"
echo "DATA (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "AWS_PROFILE definido?            $([ -n "${AWS_PROFILE:-}" ] && echo sim || echo não)"
echo "AWS_ACCESS_KEY_ID definido?      $([ -n "${AWS_ACCESS_KEY_ID:-}" ] && echo sim || echo não)"
echo "AWS_SESSION_TOKEN definido?      $([ -n "${AWS_SESSION_TOKEN:-}" ] && echo sim || echo não)  (sim => credenciais temporárias)"
echo "AWS_DEFAULT_REGION:              ${AWS_DEFAULT_REGION:-<não definida>}"

# ---------- 0. CLI e identidade ----------
run "AWS CLI" global "versão da CLI (comandos bedrock*/sesv2 exigem CLI v2 recente)" aws --version
run "STS" global "credenciais válidas; conta e ARN da identidade ativa (usuário ou role assumida)" \
aws sts get-caller-identity --output json

CALLER_ARN="$(aws sts get-caller-identity --query Arn --output text 2>/dev/null || true)"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)"
# Converte arn:aws:sts::ACCT:assumed-role/ROLE/SESSION -> arn:aws:iam::ACCT:role/ROLE (fonte de política p/ simulação)
POLICY_ARN="$CALLER_ARN"
case "$CALLER_ARN" in
arn:aws:sts::*:assumed-role/*)
    ROLE_NAME="$(echo "$CALLER_ARN" | awk -F/ '{print $2}')"
    POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" ;;
esac
echo; echo "Identidade usada na simulação de políticas: ${POLICY_ARN:-<indisponível>}"

run "IAM" global "se a identidade é um usuário IAM (falha esperada quando é role/credencial temporária)" \
aws iam get-user --output json

# Simulação = leitura pura; responde 'allowed'/'implicitDeny'/'explicitDeny' por ação SEM executá-la.
# NÃO avalia SCPs da organização — um 'allowed' aqui ainda pode ser negado na prática.
if [ -n "${POLICY_ARN:-}" ]; then
run "IAM (simulação)" global "quais ações do MVP a política da identidade permite (sem SCP)" \
    aws iam simulate-principal-policy --policy-source-arn "$POLICY_ARN" \
    --action-names bedrock:ListFoundationModels bedrock:GetFoundationModel bedrock:InvokeModel \
                    bedrock:InvokeModelWithResponseStream ses:SendEmail ses:SendRawEmail \
                    ses:GetAccount ses:CreateEmailIdentity ses:ListEmailIdentities \
                    logs:DescribeLogGroups logs:CreateLogGroup logs:PutLogEvents \
                    s3:ListAllMyBuckets s3:CreateBucket s3:PutObject \
                    iam:CreateUser iam:CreateAccessKey iam:CreateRole iam:AttachUserPolicy \
    --query 'EvaluationResults[].{acao:EvalActionName,decisao:EvalDecision}' --output table
fi

# ---------- 1. Bedrock (plano de controle) ----------
for R in "${REGIONS[@]}"; do
run "Bedrock" "$R" "serviço acessível e modelos de EMBEDDING listáveis nesta região (listar ≠ invocar)" \
    aws bedrock list-foundation-models --region "$R" --by-output-modality EMBEDDING \
    --query 'modelSummaries[].{id:modelId,provider:providerName,status:modelLifecycle.status}' --output table
for M in "${EMBED_MODELS[@]}"; do
    run "Bedrock/modelo $M" "$R" "modelo existe nesta região e está ativo (não comprova entitlement nem invocação)" \
    aws bedrock get-foundation-model --region "$R" --model-identifier "$M" \
        --query 'modelDetails.{id:modelId,status:modelLifecycle.status,inference:inferenceTypesSupported}' --output json
    # Disponível em CLIs recentes; se der 'argument ... invalid choice', a CLI é antiga — ignore.
    run "Bedrock/entitlement $M" "$R" "se a conta tem entitlement/acordo para o modelo (mais próximo de 'posso invocar' sem invocar)" \
    aws bedrock get-foundation-model-availability --region "$R" --model-id "$M" --output json
done
done

# ---------- 2. SES ----------
for R in "${REGIONS[@]}"; do
run "SES v2" "$R" "SES existe na conta; ProductionAccessEnabled=false => SANDBOX (só identidades verificadas)" \
    aws sesv2 get-account --region "$R" --output json
run "SES v2" "$R" "identidades (e-mails/domínios) já verificadas nesta região" \
    aws sesv2 list-email-identities --region "$R" --output table
run "SES v1" "$R" "cota de envio (Max24HourSend/SentLast24Hours)" \
    aws ses get-send-quota --region "$R" --output json
done

# ---------- 3. CloudWatch Logs (opcional no MVP; citado pelo Workshop) ----------
for R in "${REGIONS[@]}"; do
run "CloudWatch Logs" "$R" "leitura de log groups (não comprova escrita)" \
    aws logs describe-log-groups --region "$R" --limit 5 --output table
done

# ---------- 4. Informativo — M4 / alternativas (não obrigatórios no 1º ciclo) ----------
run "S3" global "listar buckets (não comprova leitura/gravação de objetos)" aws s3api list-buckets --query 'Buckets[].Name' --output table
for R in "${REGIONS[@]}"; do
run "Lambda (M4)" "$R" "listar funções (não comprova criar/invocar)" aws lambda list-functions --region "$R" --max-items 3 --query 'Functions[].FunctionName' --output table
run "DynamoDB (alternativa)" "$R" "listar tabelas (não comprova criar/gravar)" aws dynamodb list-tables --region "$R" --output table
run "OpenSearch Serverless (M4)" "$R" "listar coleções (não comprova criar)" aws opensearchserverless list-collections --region "$R" --output table
run "Bedrock AgentCore (não usado)" "$R" "serviço presente no Workshop; só informativo" aws bedrock-agentcore-control list-agent-runtimes --region "$R" --output table
done

echo; echo "#################### FIM — copie tudo acima e cole na conversa ####################"