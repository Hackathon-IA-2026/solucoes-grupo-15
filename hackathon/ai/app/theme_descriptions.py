"""Descrições conceituais canônicas dos temas regulatórios do CapiWatt Lens."""

from typing import Dict

THEME_DESCRIPTIONS: Dict[str, str] = {
    "comercializacao-de-energia": (
        "Ambiente de contratação, comercialização, lastro e liquidação financeira no mercado de energia."
    ),
    "compartilhamento-de-infraestrutura": (
        "Regras sobre compartilhamento de postes, dutos, faixas de servidão e redes de distribuição."
    ),
    "concorrencia-no-setor-eletrico": (
        "Monitoramento de concorrência, estruturas de mercado e prevenção de concentração econômica."
    ),
    "controle-societario-e-titularidade": (
        "Anuência prévia, transferências de controle societário e titularidade de concessões e autorizações."
    ),
    "cooperacao-institucional": (
        "Acordos e convênios com agências estaduais, órgãos judiciais, ministérios e defensorias."
    ),
    "encargos-e-fundos-setoriais": (
        "Gestão e fiscalização de encargos setoriais, CDE, CCC, RGR e recursos da CCEE."
    ),
    "expansao-da-transmissao": (
        "Leilões, concessões, reforços, melhorias e declaração de utilidade pública em transmissão."
    ),
    "gestao-e-alteracoes-contratuais": (
        "Acompanhamento, aditamentos e alterações contratuais de concessões e permissões."
    ),
    "implantacao-de-usinas": (
        "Acompanhamento de cronograma, excludente de responsabilidade e fiscalização de implantação de geração."
    ),
    "operacao-e-manutencao-da-transmissao": (
        "Fiscalização e monitoramento da disponibilidade e manutenção das instalações de transmissão."
    ),
    "operacao-e-manutencao-de-usinas": (
        "Acompanhamento de operação, desempenho e manutenção de usinas geradoras de energia."
    ),
    "outorgas-de-geracao": (
        "Autorizações, registros, alterações técnicas e revogações de outorgas de fontes hídricas e não hídricas."
    ),
    "pesquisa-desenvolvimento-e-inovacao": (
        "Regulamentação, aprovação e acompanhamento de programas de P&D e eficiência energética."
    ),
    "processos-externos-a-classificar": (
        "Processos e demandas externas pendentes de triagem e classificação temática."
    ),
    "processos-migrados-a-classificar": (
        "Processos herdados de sistemas legados em fase de categorização regulatória."
    ),
    "recursos-e-disputas-regulatorias": (
        "Recursos administrativos, pedidos de efeito suspensivo, impugnações e medidas cautelares."
    ),
    "regras-do-mercado-de-energia": (
        "Definição, aprimoramento e normatização das regras e procedimentos de comercialização."
    ),
    "saude-financeira-e-obrigacoes-setoriais": (
        "Fiscalização econômico-financeira, adimplência setorial e sustentabilidade dos agentes outorgados."
    ),
    "servicos-de-distribuicao": (
        "Qualidade do atendimento, conformidade de redes, pleitos e padrões dos serviços de distribuição."
    ),
    "tarifas-e-receitas-reguladas": (
        "Metodologia tarifária, reajustes periódicos, revisões e homologação da Receita Anual Permitida (RAP)."
    ),
    "pendente-classificacao": (
        "Processos em análise aguardando enquadramento temático definitivo."
    ),
}

def get_theme_description(tema_id: str, default_name: str = "") -> str:
    """Retorna a descrição canônica do tema ou gera uma descrição descritiva padrão."""
    if tema_id in THEME_DESCRIPTIONS:
        return THEME_DESCRIPTIONS[tema_id]
    if default_name:
        return f"Processos, decisões e atos regulatórios relacionados a {default_name.lower()}."
    return "Assuntos regulatórios que organizam processos, documentos e normas correlatas."
