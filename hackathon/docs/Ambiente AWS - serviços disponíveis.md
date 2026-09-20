# **Ambiente AWS do hackathon: serviços disponíveis**

Só funcionam as regiões us-east-1 e us-west-2. O provisionamento de recursos é feito via CloudFormation ou CDK.

## **Serviços por área**

| Área | Serviços | Alcance |
| :---- | :---- | :---- |
| Computação | Lambda, ECS, Auto Scaling | Completo |
| Dados e armazenamento | S3, DynamoDB, OpenSearch, EFS | Completo |
| IA e agentes | Bedrock AgentCore, Agent Registry, SageMaker, Bedrock | Bedrock tem restrição de modelos |
| Integração | EventBridge, SNS, API Gateway (execute-api) | execute-api apenas invoca APIs existentes |
| Identidade | Cognito Identity, Cognito User Pools | Completo |
| Build e deploy | CloudFormation, CodeBuild, ECR | ECR apenas cria e consulta repositórios |
| Observabilidade e auditoria | CloudWatch, CloudWatch Logs, CloudTrail, X-Ray, Application Signals | Application Signals apenas StartDiscovery |
| Segurança e configuração | IAM, KMS, SSM, STS | IAM com restrições de passagem de papel |
| Infraestrutura EC2 | EC2 | Consultar VPCs e subnets, e gerenciar launch templates |
| Gerenciamento | Resource Groups Tagging | Completo |

Sobre IAM, duas condições definem o que é possível montar. Um papel criado pelo time só pode ser entregue a Bedrock, Bedrock AgentCore, ECS, EC2 e EFS; para Lambda e CodeBuild, o papel a ser passado é o próprio WSParticipantRole. E sts:AssumeRole está liberado apenas para os papéis cdk-\*, admin\_persona, publisher\_persona e consumer\_persona.

## **Modelos do Bedrock**

Catálogo de modelos da conta em us-east-1. Testes por amostragem com as credenciais de participante confirmaram resposta de Claude Sonnet 5 e OpenAI GPT 6 Astra.

* Anthropic Claude: Sonnet 5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 4.6, Opus 4.5, Sonnet 4.5, Haiku 4.5, Fable 5 e Fable 5.1  
* Amazon Nova: Premier, Pro, Lite, Micro e Nova 2 Lite  
* OpenAI: GPT 6 Astra e GPT 5.6 nas variantes Terra, Luna e Sol  
* xAI: Grok 4.6  
* Moonshot: Kimi K3  
* DeepSeek: R1  
* Writer: Palmyra X4 e X5  
* TwelveLabs: Marengo e Pegasus  
* Amazon Titan: embeddings de texto

O identificador leva prefixo us. ou global., e o prefixo importa: um modelo pode responder em uma forma e falhar na outra, então se der negativa vale tentar a outra. Dentro do Code Editor a identidade é outra, mais restrita, e ali funcionam apenas os perfis global. da Anthropic.

## **Obs: Região no workshop**

Dentro do Code Editor do workshop (o VS Code que abre no navegador), o Claude Code precisa apontar para us-east-1. Rode isto no terminal antes de abrir o claude:

export AWS\_REGION=us-east-1  
export AWS\_DEFAULT\_REGION=us-east-1