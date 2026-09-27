# Chamada de teste ao Titan Embed V2 em us-east-1 e us-west-2 (2026-09-26)

Sessão `s-2026-09-26-vector-index`, topic-vector-index-hosting (#90). Objetivo: confirmar que o código do `ai` como está (`REGION = "us-east-1"` em `ai/app/embeddings.py`) funciona na conta do workshop, cuja infraestrutura fica em us-west-2.

- Identidade: `assumed-role/WSParticipantRole/Participant` (credenciais de `.env`), conta 640205779371.
- `aws bedrock-runtime invoke-model --model-id amazon.titan-embed-text-v2:0`, corpo `{"inputText": "teste de geração distribuída MMGD", "dimensions": 1024, "normalize": true}`:
  - us-east-1: ok, 1024 dimensões, 10 tokens de entrada.
  - us-west-2: ok, 1024 dimensões, 10 tokens de entrada.
- Similaridade de cosseno entre os dois vetores: 1,0000 (o mesmo modelo nas duas regiões).

Conclusão: nenhum SCP bloqueia o Bedrock em us-east-1 nesta conta; a task role do `ai` (criada pelo CDK) só precisa da permissão `bedrock:InvokeModel` no ARN de us-east-1. Não foi testada a própria task role, que ainda não existe.
