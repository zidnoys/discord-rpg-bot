# ⚔️ Discord RPG Bot — RPG Interativo

Um bot de RPG interativo para Discord com sistema de classes, combate por turnos, habilidades, inventário, loja, dungeons e ranking.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3+-7289da.svg?logo=discord&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎮 Funcionalidades

### Classes de Personagem
| Classe | Emoji | Estilo | Atributo Principal |
|--------|-------|--------|-------------------|
| **Guerreiro** | ⚔️ | Tanque corpo-a-corpo | Força + Defesa |
| **Lutador** | 🥊 | Combos e contra-ataques | Agilidade + Força |
| **Atirador** | 🔫 | Dano à distância, críticos | Destreza + Precisão |
| **Mago** | 🧙 | Magia, AoE, elementos | Inteligência + Mana |
| **Curandeiro** | 🩺 | Suporte, cura, proteção | Sabedoria + Mana |
| **Assassino** | 🗡️ | Furtividade, burst damage | Agilidade + Destreza |

### Sistemas
- **Combate por Turnos** — Interface interativa com botões (atacar, habilidade, item, fugir)
- **Progressão** — XP, level up, pontos de atributo, crescimento por classe
- **Habilidades** — 5 skills únicas por classe, com elementos e efeitos especiais
- **Inventário & Equipamento** — Armas, armaduras, escudos, acessórios, consumíveis
- **Loja** — Compra e venda de itens
- **Dungeons** — 6 dungeons com múltiplos andares e bosses
- **Sistema Elemental** — Fogo > Gelo > Raio > Água > Fogo, Luz ↔ Trevas
- **Ranking** — Leaderboard por nível, ouro, monstros e dungeons

### Comandos (Slash Commands)
| Comando | Descrição |
|---------|-----------|
| `/criar` | Criar personagem |
| `/perfil` | Ver perfil e stats |
| `/atributos` | Distribuir pontos de atributo |
| `/descansar` | Recuperar HP e MP |
| `/caçar` | Combate PvE contra monstros |
| `/habilidades` | Ver habilidades da classe |
| `/inventario` | Ver inventário |
| `/equipar` | Equipar item |
| `/desequipar` | Desequipar item |
| `/loja` | Ver itens da loja |
| `/comprar` | Comprar item |
| `/vender` | Vender item |
| `/dungeons` | Ver dungeons disponíveis |
| `/dungeon` | Entrar em dungeon |
| `/ranking` | Ver leaderboard |
| `/deletar` | Deletar personagem |

## 🚀 Setup

### Pré-requisitos
- Python 3.11+
- Uma conta no [Discord Developer Portal](https://discord.com/developers/applications)

### 1. Criar o Bot no Discord

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em **New Application** e dê um nome
3. Vá em **Bot** → **Reset Token** → copie o token
4. Em **Privileged Gateway Intents**, ative **Message Content Intent**
5. Em **OAuth2** → **URL Generator**: marque `bot` e `applications.commands`
6. Nas permissões do bot, marque: Send Messages, Embed Links, Use Slash Commands, Read Message History
7. Use a URL gerada para convidar o bot ao seu servidor

### 2. Instalar e Rodar

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/discord-rpg-bot.git
cd discord-rpg-bot

# Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure o token
export DISCORD_TOKEN="seu_token_aqui"
# Ou crie um arquivo .env com: DISCORD_TOKEN=seu_token_aqui

# Rode o bot
python bot.py
```

## 🗂️ Estrutura do Projeto

```
discord-rpg-bot/
├── bot.py              # Entry point do bot
├── config.py           # Configurações gerais
├── database.py         # Banco de dados SQLite
├── requirements.txt    # Dependências
├── cogs/
│   ├── character.py    # Criação de personagem, perfil, atributos
│   ├── combat.py       # Sistema de combate PvE
│   ├── inventory.py    # Inventário e equipamento
│   ├── shop.py         # Loja (compra/venda)
│   ├── skills.py       # Visualização de habilidades
│   ├── dungeon.py      # Sistema de dungeons
│   └── ranking.py      # Leaderboard
├── data/
│   ├── classes.json    # Dados das 6 classes
│   ├── monsters.json   # 12 tipos de monstros
│   ├── items.json      # 25+ itens (armas, armaduras, consumíveis)
│   ├── skills.json     # 30 habilidades (5 por classe)
│   └── dungeons.json   # 6 dungeons com progressão
└── utils/
    ├── embeds.py       # Helpers para embeds e barras de vida
    ├── formulas.py     # Fórmulas de dano, XP, elementos
    └── views.py        # Views interativas (botões e selects)
```

## ⚙️ Personalização

Todos os dados do jogo ficam nos arquivos JSON dentro de `data/`. Você pode facilmente:

- **Adicionar classes** em `classes.json`
- **Criar monstros** em `monsters.json`
- **Adicionar itens** em `items.json`
- **Criar habilidades** em `skills.json`
- **Criar dungeons** em `dungeons.json`

As configurações gerais (XP, ouro inicial, etc.) ficam em `config.py`.

## 📋 Referências

Projetos que serviram de inspiração:
- [Escordia-RPG-System](https://github.com/rodmarkun/Escordia-RPG-System) — Sistema RPG completo com classes, combate e dungeons
- [IdleRPG](https://github.com/Gelbpunkt/IdleRPG) — RPG idle para Discord
- [RPGBot](https://github.com/henry232323/RPGBot) — Bot RPG com inventário e economia
- [Avrae](https://github.com/avrae/avrae) — Bot D&D 5e com sistema de combate avançado

## 📄 Licença

MIT License
