# Entrega 1 — desenho e configuração científica

TCC de MMM com Google Meridian: preparar uma investigação GEO e uma comparação futura com o nacional. **Não há posterior, ROI/mROI estimado ou otimização.** O repositório da EDA permanece intacto.

**Publicação pendente:** o conector GitHub recusou escrita (403) e o transporte Git não tem autenticação. O conteúdo está em commit local; os links do GitHub/Colab só funcionarão após publicação. Ver [registro](outputs/logs/publication_status.json).

## Comece por aqui

1. [Guia científico e didático](docs/01_DESENHO_CIENTIFICO_DIDATICO.md): pergunta, evidências da EDA, DAG, estimandos, priors, validação e limites.
2. [Notebook único](notebooks/01_DESENHO_CIENTIFICO_COLAB.ipynb): percurso executável desta entrega. [Abrir no Colab](https://colab.research.google.com/github/thiagossilva17/MMM_Google_Meridian_Primeira_Entrega/blob/main/notebooks/01_DESENHO_CIENTIFICO_COLAB.ipynb).
3. [Configuração GEO](configs/baseline_geo.yaml), [validação](configs/validation_design.yaml) e [27 experimentos futuros](configs/experiment_registry.yaml).
4. [Proveniência](data/metadata/provenance.json), [auditoria dos dados](outputs/tables/data_audit.csv), [máscara de holdout](data/splits/holdout_geo.csv) e [aceitação](outputs/logs/acceptance.csv).

## Executar

Python 3.12; CPU suficiente. Na raiz do repositório, preferencialmente em ambiente virtual:

```bash
python -m pip install -r requirements.txt
python -m src.run_design
python -m pytest -q
```

O CSV oficial pequeno está versionado com sua licença. Se ausente, o carregador baixa exclusivamente o commit fixado e rejeita hash divergente. Não precisa de credenciais ou Google Drive. Para reproduzir uma revisão histórica, faça checkout de seu commit e use o mesmo SHA em `REVISION` no notebook.

## Evidência e limites

- Fonte: 40 GEOs × 156 semanas, 6.240 linhas; 20 colunas físicas e 19 analíticas.
- Meridian 2.1.0: InputData, ModelSpec e objeto Meridian construídos sem amostragem; dimensões e máscara efetiva verificadas.
- Holdout: 936 células (15%); seis por semana e 23/24 por GEO. Channel2 tem atividade em treino e teste nos 40 mercados.
- Testes: [pytest.xml](outputs/logs/pytest.xml). Notebook: [registro de validação](outputs/logs/notebook_validation.json). Execução: [manifesto](outputs/logs/run_manifest.json).
- **REVIEW científico:** prior Beta(1,99) de contribuição não possui justificativa de negócio; rever antes de G0. Também revisar controles/Promo, borda temporal e usos indiretos do KPI reservado.
- **PENDING_METHOD_DECISION:** protocolo preditivo compartilhado GEO × nacional; máscara GEO isolada não torna avaliações equivalentes.
- Notebook: estrutura e sete células Python sequenciais verificadas; kernel Jupyter local **BLOCKED** por restrição de sockets TCP/IPC. Saídas reais preservadas, sem alegar validação da interface.
- **NOT_TESTED_IN_HOSTED_COLAB:** execução local não equivale a uma sessão hospedada. Procedimento de validação no capítulo 11 do guia.

A próxima entrega começa somente após revisão aplicável e nova instrução. Todos os experimentos permanecem `planned`.
