## Project structure

otimizacao-sedes/
│
├── data/
│   ├── raw/              # dados originais (planilha bruta)
│   └── processed/        # dados tratados
│
├── src/
│   ├── __init__.py
│   ├── load_data.py      # leitura dos dados
│   ├── preprocess.py     # limpeza e preparação
│   ├── scoring.py        # regra de pontuação (1, 0.5, 0)
│   ├── optimizer.py      # lógica de testar cidades/pares
│   └── utils.py          # funções auxiliares
│
├── notebooks/
│   └── exploracao.ipynb  # análise exploratória (opcional)
│
├── results/
│   ├── rankings.csv      # melhores cidades/pares
│   └── graficos/         # visualizações
│
├── tests/
│   └── test_scoring.py   # testes simples
│
├── main.py               # executa o projeto
├── requirements.txt      # dependências
├── README.md             # explicação do projeto
└── .gitignore
