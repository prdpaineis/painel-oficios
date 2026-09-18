# Painel de Ofícios

Dashboard estático (HTML+JS, sem build) que lê os ofícios/requisições recebidos
no Odoo (módulo `jur_oficios`) e publica um painel com prazos, situação,
responsáveis e subsídios pendentes.

Publicado via GitHub Pages a partir de `docs/`.

**Atenção:** os dados aqui incluem número de processo e resumo de pedidos de
clientes (inclusive requisições policiais). O repositório é público por
decisão explícita — qualquer pessoa com o link vê esses dados.

## Atualização automática

`.github/workflows/atualizar-painel.yml` roda `docs/gerar_painel.py` todo dia às
07:00 (horário de Brasília), regrava `docs/oficios.js` e commita o resultado —
o GitHub Pages republica sozinho. Também pode ser disparado manualmente pela
aba **Actions** do repositório (`workflow_dispatch`).

As credenciais do Odoo (`ODOO_URL`, `ODOO_DB`, `ODOO_LOGIN`, `ODOO_API_KEY`)
ficam como **Secrets** do repositório (Settings → Secrets and variables →
Actions), nunca em arquivo versionado.

## Rodar localmente

```
pip install -r requirements.txt
cp .env.example .env   # preencha as credenciais do Odoo
cd docs
python gerar_painel.py
python -m http.server   # abra http://localhost:8000
```

`gerar_painel.py` também grava `docs/painel_oficios_completo.html`
(o `index.html` com os dados já embutidos — abre com duplo clique, sem
servidor). Esse arquivo é ignorado pelo git: não deve ser publicado nem
enviado a terceiros além de quem já tem acesso aos dados.

## Estrutura

```
docs/
  index.html         # o painel em si (servido pelo GitHub Pages)
  gerar_painel.py     # busca dados no Odoo e grava oficios.js
  oficios.js          # gerado — não editar à mão
```

## Se der erro ao gerar

| Mensagem | Causa |
|---|---|
| `Login recusado` | `.env` fora da pasta `docs/`, ou chave revogada |
| `AccessError` em `jur.oficio` | o usuário perdeu acesso ao módulo de ofícios: pedir ao admin do Odoo |
| lento / timeout | servidor de produção carregado; rodar de novo mais tarde |

Regras do lado do Odoo: a chave é só de leitura (não chama `create`, `write`,
`message_post` nem `action_*`); o script já lê em lotes de 200 e sem campos de
arquivo pesado — não rodar em paralelo.
