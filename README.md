# 🎴 Cards of Doons | BOT

Bot oficial do servidor do Cards of Doons para Discord.

Desenvolvido em Python com discord.py 2.x, hospedado na Railway.

---

## 📋 Funcionalidades

- 👋 **Sistema de Boas-Vindas** — Mensagem automática quando novos membros entram
- 🎫 **Sistema de Tickets** — Suporte por canais privados
- 🤖 **IA de Suporte** — Atendimento automatizado via Groq (GPT-OSS 120B)
- 🛡️ **Chamada de Staff** — Transferência para atendimento humano
- 🔐 **Segurança** — Rate limit, anti-prompt injection e proteção de dados

---

## 🛠️ GUIA COMPLETO DE CONFIGURAÇÃO

Siga este guia do zero. Não é necessário experiência prévia.

---

## PARTE 1 — Criar o Bot no Discord

### 1.1 — Acessar o Portal do Desenvolvedor

1. Abra o navegador e acesse: **https://discord.com/developers/applications**
2. Faça login com sua conta do Discord.

### 1.2 — Criar uma nova aplicação

1. Clique no botão azul **"New Application"** (canto superior direito).
2. Digite um nome para a aplicação: `Cards of Doons | BOT`
3. Aceite os termos de serviço.
4. Clique em **"Create"**.

### 1.3 — Criar o Bot

1. No menu esquerdo, clique em **"Bot"**.
2. Clique em **"Add Bot"**.
3. Confirme clicando em **"Yes, do it!"**.
4. Defina o nome do bot: `Cards of Doons | BOT`
5. Você pode adicionar um ícone se quiser.

### 1.4 — Copiar o Token

1. Ainda na aba **"Bot"**, procure a seção **"Token"**.
2. Clique em **"Reset Token"** e confirme.
3. Clique em **"Copy"** para copiar o token.
4. **⚠️ IMPORTANTE: Guarde este token em local seguro. Nunca compartilhe com ninguém.**
5. Este token será usado na variável `DISCORD_TOKEN` na Railway.

### 1.5 — Ativar as Intents

1. Ainda na aba **"Bot"**, role a página para baixo até **"Privileged Gateway Intents"**.
2. Ative as três opções:
   - ✅ **PRESENCE INTENT**
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
3. Clique em **"Save Changes"**.

### 1.6 — Configurar Permissões e Gerar o Convite

1. No menu esquerdo, clique em **"OAuth2"**.
2. Clique em **"URL Generator"**.
3. Em **"SCOPES"**, marque:
   - ✅ `bot`
   - ✅ `applications.commands`
4. Em **"BOT PERMISSIONS"**, marque:
   - ✅ `Read Messages/View Channels`
   - ✅ `Send Messages`
   - ✅ `Embed Links`
   - ✅ `Read Message History`
   - ✅ `Manage Channels`
   - ✅ `Manage Messages`
   - ✅ `Mention Everyone`
5. Role até o final e copie o link gerado em **"GENERATED URL"**.

### 1.7 — Adicionar o Bot ao Servidor

1. Cole o link copiado no navegador.
2. Selecione o servidor **Cards of Doons**.
3. Clique em **"Autorizar"**.
4. Complete o CAPTCHA se aparecer.
5. O bot aparecerá como offline no servidor (ficará online após o deploy).

---

## PARTE 2 — Obter a API Key da Groq

### 2.1 — Criar conta na Groq

1. Acesse: **https://console.groq.com**
2. Crie uma conta gratuita ou faça login.

### 2.2 — Gerar a API Key

1. No painel, clique em **"API Keys"** no menu esquerdo.
2. Clique em **"Create API Key"**.
3. Dê um nome: `Cards of Doons Bot`
4. Copie a chave gerada.
5. **⚠️ Guarde em local seguro. Você não verá esta chave novamente.**
6. Esta chave será usada na variável `GROQ_API_KEY` na Railway.

---

## PARTE 3 — Criar o Repositório no GitHub

### 3.1 — Criar conta no GitHub (se não tiver)

1. Acesse: **https://github.com**
2. Clique em **"Sign up"** e crie sua conta.

### 3.2 — Criar um novo repositório

1. Após fazer login, clique no ícone **"+"** no canto superior direito.
2. Selecione **"New repository"**.
3. Configure:
   - **Repository name:** `cards-of-doons-bot`
   - **Description:** `Bot oficial do Cards of Doons`
   - **Visibility:** `Private` (recomendado para proteger o código)
   - **NÃO** marque "Add a README file"
4. Clique em **"Create repository"**.

### 3.3 — Fazer upload dos arquivos

**Opção A — Pela interface web do GitHub (mais fácil):**

1. Na página do repositório vazio, clique em **"uploading an existing file"**.
2. Arraste todos os arquivos do projeto para a área indicada.
3. **⚠️ VERIFIQUE: Certifique-se de que o arquivo `.env` NÃO está sendo enviado.**
4. Na caixa de "Commit changes", escreva: `feat: initial bot setup`
5. Clique em **"Commit changes"**.

**Opção B — Via Git no terminal:**

```bash
# Na pasta do projeto
git init
git add .
git status  # Verifique que .env NÃO aparece na lista
git commit -m "feat: initial bot setup"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/cards-of-doons-bot.git
git push -u origin main
