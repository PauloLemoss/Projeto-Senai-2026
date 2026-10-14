# diferenciais-tecnicos Specification

## Purpose

Cobre os diferenciais técnicos do backend (barema, seção "4. Backend", item B5) que não são regra
de negócio de nenhuma capability de domínio: registro de logs por requisição e os comandos de
lint/formatação informados no README.

## Requirements

### Requirement: Registro de logs por requisição (B5)
Depois de cada requisição HTTP tratada pela aplicação, a saída da aplicação SHALL mostrar uma
única linha com data e hora legíveis, o método HTTP, o caminho e o status da resposta dessa
requisição, gerada por uma biblioteca de log declarada nas dependências do backend ou fornecida
pelo framework ou pela biblioteca padrão. `print` ou equivalente SHALL não contar como log válido
para este requisito.

#### Scenario: Requisição bem-sucedida gera uma linha de log legível
- **WHEN** o cliente faz `GET /api/v1/players` e a API responde `200`
- **THEN** a saída da aplicação mostra, numa única linha, data e hora legíveis, `GET`, o caminho
  da requisição e `200`

#### Scenario: Requisição recusada também gera uma linha de log legível
- **WHEN** o cliente faz uma requisição que a API recusa com `400`, `404` ou `409`
- **THEN** a saída da aplicação mostra, numa única linha, data e hora legíveis, o método, o
  caminho e o status da resposta (`400`, `404` ou `409`, conforme o caso)

### Requirement: Comandos de lint e de verificação de formatação (B5)
O README SHALL informar um comando de lint do backend que termina sem erros quando o código está
conforme, e um comando de verificação de formatação do backend, distinto do comando que formata:
o comando de verificação SHALL apenas conferir se os arquivos já estão formatados (saindo com
código de erro se não estiverem), sem alterar nenhum arquivo no processo.

#### Scenario: Comando de lint termina sem erros
- **WHEN** o comando de lint informado no README é executado sobre o código atual do backend
- **THEN** o comando termina com código de saída `0`, sem relatar nenhum erro

#### Scenario: Comando de verificação de formatação não altera arquivos
- **WHEN** o comando de verificação de formatação informado no README é executado sobre o código
  já formatado
- **THEN** o comando termina com código de saída `0` e nenhum arquivo do repositório é alterado
