"""Busca os oficios (jur.oficio) no Odoo e grava painel-oficios/oficios.js.

Requer uma chave com leitura no modulo jur_oficios (ver .env.example: a
chave do agente.escritorio nao serve para isso, so para juridico_escritorio).

Segue as mesmas regras de leitura do AGENTE.md do painel de processos:
chamadas em serie, sempre com `fields`, em lotes, sem campos de arquivo/HTML
pesado (draft_response/approved_response/sent_response ficam de fora da
busca em massa).
"""
import json
import os
import sys
import xmlrpc.client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

URL = os.environ['ODOO_URL']
DB = os.environ['ODOO_DB']
LOGIN = os.environ['ODOO_LOGIN']
KEY = os.environ['ODOO_API_KEY']

BATCH = 200

FIELDS = [
    'name', 'internal_reference', 'bpm_numero_oficio', 'company_id',
    'document_type', 'source_channel', 'issuing_body', 'case_number',
    'received_date', 'response_deadline', 'internal_deadline', 'prazo_situacao',
    'prazo_texto', 'state', 'priority', 'risk_level', 'bpm_criticidade',
    'categoria_pedido', 'request_summary', 'request_excerpt',
    'response_type', 'response_type_manual', 'response_type_ia',
    'assigned_user_id', 'approved_by', 'approved_at', 'sent_at',
    'requires_human_review', 'pending_documents_count', 'documents_ready',
    'tema_id', 'closing_notes',
]

SUBSIDIO_FIELDS = ['oficio_id', 'name', 'area', 'status', 'result', 'requested_at', 'create_date']

# Rotulos das Selections, para o painel nao precisar adivinhar (fields_get
# com attributes=['selection'] em 16/09/2026).
SELECTIONS = {
    'state': {
        'recebido': 'Cadastro', 'texto_extraido': 'Cadastro - texto lido',
        'triagem_concluida': 'Triagem', 'sem_relacao': 'Sem Relacao',
        'aguardando_busca': 'Solicitar documentos', 'busca_concluida': 'Acompanhar documentos',
        'estrategia_definida': 'Estrategia', 'minuta_gerada': 'Minuta',
        'em_revisao': 'Em Revisao', 'aprovado': 'Aprovacao', 'respondido': 'Respondido',
        'encerrado': 'Encerramento', 'erro_processamento': 'Erro de Processamento',
    },
    'document_type': {
        'oficio_judicial': 'Oficio Judicial', 'requisicao_policial': 'Requisicao Policial',
        'requisicao_administrativa': 'Requisicao Administrativa', 'outro': 'Outro',
    },
    'priority': {'0': 'Baixa', '1': 'Normal', '2': 'Alta', '3': 'Urgente'},
    'risk_level': {'baixo': 'Baixo', 'medio': 'Medio', 'alto': 'Alto'},
    'bpm_criticidade': {'alta': 'Alta', 'media': 'Media', 'baixa': 'Baixa'},
    'categoria_pedido': {
        'informacao': 'Pedido de informacao',
        'obrigacao_fazer': 'Ordem de fazer (bloqueio, suspensao, cumprimento)',
        'misto': 'Informacao + ordem de fazer',
    },
    'response_type': {
        'sem_relacao': 'Sem Relacao', 'nao_localizado': 'Nao Localizado',
        'localizado_sem_dados_relevantes': 'Localizado sem Dados Relevantes',
        'fornecimento_parcial': 'Fornecimento Parcial',
        'fornecimento_integral': 'Fornecimento Integral',
        'impossibilidade_tecnica': 'Impossibilidade Tecnica', 'revisao_humana': 'Revisao Humana',
    },
    'prazo_situacao': {
        'vencido': 'Vencido', 'hoje': 'Vence hoje', 'proximo': 'Vence em ate 3 dias',
        'normal': 'No prazo', 'sem_prazo': 'Sem prazo',
    },
    'subsidio_status': {
        'pendente': 'Pendente', 'solicitado': 'Solicitado',
        'recebido': 'Recebido', 'nao_aplicavel': 'Nao Aplicavel',
    },
}

# Status de jur.oficio.required.document que ainda contam como "em aberto"
# para o card de subsidios pendentes.
SUBSIDIO_ABERTO = {'pendente', 'solicitado'}


def m2o_nome(valor):
    return valor[1] if valor else None


def rotulo(campo, valor):
    if valor is False or valor is None:
        return None
    return SELECTIONS.get(campo, {}).get(valor, valor)


def main():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, LOGIN, KEY, {})
    if not uid:
        sys.exit('Login recusado: confira ODOO_LOGIN / ODOO_API_KEY em painel-oficios/.env')

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    ctx = {'lang': 'pt_BR', 'tz': 'America/Sao_Paulo'}

    def call(model, method, *args, **kwargs):
        kwargs.setdefault('context', ctx)
        return models.execute_kw(DB, uid, KEY, model, method, list(args), kwargs)

    total = call('jur.oficio', 'search_count', [])
    print(f'{total} oficios no Odoo')

    oficios = []
    offset = 0
    while offset < total:
        lote = call('jur.oficio', 'search_read', [], fields=FIELDS,
                    limit=BATCH, offset=offset, order='id')
        oficios.extend(lote)
        offset += BATCH
        print(f'  lidos {min(offset, total)}/{total}')

    cliente_por_oficio = {o['id']: m2o_nome(o.get('company_id')) or 'Sem empresa' for o in oficios}
    nome_por_oficio = {o['id']: o.get('bpm_numero_oficio') or o['name'] for o in oficios}

    total_subsidios = call('jur.oficio.required.document', 'search_count',
                            [('status', 'in', list(SUBSIDIO_ABERTO))])
    print(f'{total_subsidios} subsidios pendentes/solicitados no Odoo')

    subsidios = []
    offset = 0
    while offset < total_subsidios:
        lote = call('jur.oficio.required.document', 'search_read',
                    [('status', 'in', list(SUBSIDIO_ABERTO))],
                    fields=SUBSIDIO_FIELDS, limit=BATCH, offset=offset, order='id')
        subsidios.extend(lote)
        offset += BATCH
        print(f'  lidos {min(offset, total_subsidios)}/{total_subsidios}')

    saida = []
    for o in oficios:
        saida.append({
            'id': o['id'],
            'nome': o['name'],
            'referenciaInterna': o.get('internal_reference') or None,
            'numeroOficio': o.get('bpm_numero_oficio') or None,
            'cliente': m2o_nome(o.get('company_id')) or 'Sem empresa',
            'tipoDocumento': rotulo('document_type', o.get('document_type')),
            'canal': o.get('source_channel'),
            'orgaoEmissor': o.get('issuing_body') or None,
            'numeroProcesso': o.get('case_number') or None,
            'entrada': o.get('received_date') or None,
            'prazoResposta': o.get('response_deadline') or None,
            'prazoInterno': o.get('internal_deadline') or None,
            'situacaoPrazo': rotulo('prazo_situacao', o.get('prazo_situacao')),
            'prazoTexto': o.get('prazo_texto') or None,
            'situacao': rotulo('state', o.get('state')),
            'prioridade': rotulo('priority', o.get('priority')),
            'risco': rotulo('risk_level', o.get('risk_level')),
            'criticidade': rotulo('bpm_criticidade', o.get('bpm_criticidade')),
            'naturezaPedido': rotulo('categoria_pedido', o.get('categoria_pedido')),
            'resumoPedido': o.get('request_summary') or o.get('request_excerpt') or None,
            'tipoResposta': rotulo('response_type', o.get('response_type')),
            'tipoRespostaManual': bool(o.get('response_type_manual')),
            'tipoRespostaIA': rotulo('response_type', o.get('response_type_ia')),
            'responsavel': m2o_nome(o.get('assigned_user_id')),
            'aprovadoPor': m2o_nome(o.get('approved_by')),
            'aprovadoEm': o.get('approved_at') or None,
            'enviadoEm': o.get('sent_at') or None,
            'exigeRevisaoHumana': bool(o.get('requires_human_review')),
            'subsidiosPendentes': o.get('pending_documents_count') or 0,
            'documentosProntos': bool(o.get('documents_ready')),
            'tema': m2o_nome(o.get('tema_id')),
            'notasEncerramento': o.get('closing_notes') or None,
        })

    subsidios_saida = []
    for s in subsidios:
        oficio_id = s['oficio_id'][0] if s.get('oficio_id') else None
        subsidios_saida.append({
            'id': s['id'],
            'oficioId': oficio_id,
            'oficio': nome_por_oficio.get(oficio_id),
            'cliente': cliente_por_oficio.get(oficio_id, 'Sem empresa'),
            'nome': s.get('name') or None,
            'area': s.get('area') or None,
            'status': rotulo('subsidio_status', s.get('status')),
            'resultado': s.get('result') or None,
            'solicitadoEm': s.get('requested_at') or None,
            'criadoEm': s.get('create_date') or None,
        })

    pasta = os.path.dirname(os.path.abspath(__file__))
    dados_js = (
        '// Gerado por gerar_painel.py — nao editar a mao.\n'
        f'const OFICIOS = {json.dumps(saida, ensure_ascii=False)};\n'
        f'const SUBSIDIOS = {json.dumps(subsidios_saida, ensure_ascii=False)};\n'
    )

    caminho = os.path.join(pasta, 'oficios.js')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(dados_js)
    print(f'Gravado {caminho} com {len(saida)} oficios e {len(subsidios_saida)} subsidios em aberto.')

    # Versao de arquivo unico (abre com duplo clique, sem servidor).
    with open(os.path.join(pasta, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    tag = '<script src="oficios.js" onerror="document.getElementById(\'erro\').style.display=\'block\'"></script>'
    if tag not in html:
        sys.exit('Nao achei a tag <script src="oficios.js"> em index.html')
    inline = '<script>\n' + dados_js.replace('</', '<\\/') + '</script>'
    completo = os.path.join(pasta, 'painel_oficios_completo.html')
    with open(completo, 'w', encoding='utf-8') as f:
        f.write(html.replace(tag, inline))
    print(f'Gravado {completo}')


if __name__ == '__main__':
    main()
