import os
import sys
import boto3
import re
from datetime import datetime
from pathlib import Path

# Adiciona o diretorio principal ao sys.path para importar modules locais
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.theme_descriptions import get_theme_description

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[áãâà]', 'a', text)
    text = re.sub(r'[éê]', 'e', text)
    text = re.sub(r'[í]', 'i', text)
    text = re.sub(r'[óõô]', 'o', text)
    text = re.sub(r'[ú]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def parse_md_table(filepath: Path) -> list:
    items = []
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return items
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line.startswith('|') or 'De —' in line or 'De -' in line or '---' in line:
            continue
            
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            tipo_processo = parts[1]
            tema_nome = parts[2]
            
            if not tipo_processo or not tema_nome:
                continue
                
            macrotema = tipo_processo.split(':')[0].strip() if ':' in tipo_processo else tipo_processo.split('-')[0].strip()
            tema_id = slugify(tema_nome)
            
            items.append({
                "tipo_processo": tipo_processo,
                "tema_id": tema_id,
                "tema_nome": tema_nome,
                "descricao": get_theme_description(tema_id, tema_nome),
                "macrotema_sei": macrotema,
                "temas_secundarios": [],
                "origem_classificacao": "direta",
                "atualizado_em": datetime.utcnow().isoformat() + "Z"
            })
            
    return items

def main():
    filepath = Path(__file__).resolve().parent.parent.parent.parent / "requirements" / "document-types" / "types-of-process.md"
    print(f"Lendo especificação canônica de {filepath}")
    
    items = parse_md_table(filepath)
    print(f"Encontrados {len(items)} tipos de processos.")
    
    if not items:
        return
        
    client_kwargs = {"region_name": settings.aws_region}
    if settings.dynamodb_endpoint_url:
        client_kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        
    dynamodb = boto3.resource("dynamodb", **client_kwargs)
    table = dynamodb.Table(settings.dynamodb_table_process_themes)
    
    print(f"Sincronizando com a tabela DynamoDB: {settings.dynamodb_table_process_themes}")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            
    print("Sincronização concluída com sucesso.")

if __name__ == "__main__":
    main()
