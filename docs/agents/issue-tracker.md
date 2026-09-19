# Rastreador de Issues: Markdown Local

As issues e especificações deste repositório residem como arquivos markdown em `.scratch/`.

## Convenções

- Uma funcionalidade por diretório: `.scratch/<slug-da-feature>/`
- A especificação técnica fica em `.scratch/<slug-da-feature>/spec.md`
- As issues de implementação ficam em arquivos individuais em `.scratch/<slug-da-feature>/issues/<NN>-<slug>.md`, numerados a partir de `01` — nunca um arquivo único combinado de tickets
- O estado de triagem é registrado em uma linha `Status:` próxima ao topo de cada arquivo de issue (consulte `triage-labels.md` para as strings de papéis)
- Comentários e histórico de conversa são anexados ao final do arquivo sob a seção `## Comentários` (`## Comments`)

## Quando uma skill disser "publicar no rastreador de issues" ("publish to the issue tracker")

Crie um novo arquivo sob `.scratch/<slug-da-feature>/` (criando o diretório se necessário).

## Quando uma skill disser "obter o ticket relevante" ("fetch the relevant ticket")

Leia o arquivo no caminho referenciado. O usuário normalmente informará o caminho ou o número da issue diretamente.

## Operações de Wayfinding (Mapeamento de Tarefas)

Usado pela skill `/wayfinder`. O **mapa** é um arquivo com um arquivo **filho** por ticket.

- **Mapa**: `.scratch/<esforço>/map.md` — contém o corpo de Notas / Decisões até o momento / Névoa (Fog).
- **Ticket filho**: `.scratch/<esforço>/issues/NN-<slug>.md`, numerado a partir de `01`, com a pergunta ou tarefa no corpo. Uma linha `Type:` registra o tipo de ticket (`research`/`prototype`/`grilling`/`task`); uma linha `Status:` registra `claimed`/`resolved`.
- **Bloqueios (Dependencies)**: Uma linha `Blocked by: NN, NN` próxima ao topo. Um ticket é desbloqueado quando todos os arquivos listados estiverem com status `resolved`.
- **Fronteira (Frontier)**: Varrer `.scratch/<esforço>/issues/` buscando arquivos abertos, desbloqueados e não reivindicados; o primeiro em ordem numérica tem prioridade.
- **Reivindicar (Claim)**: Definir `Status: claimed` e salvar antes de iniciar qualquer trabalho.
- **Resolver (Resolve)**: Anexar a resposta sob a seção `## Resposta` (`## Answer`), definir `Status: resolved`, e anexar um ponteiro de contexto (resumo + link) na seção de decisões em `map.md`.
