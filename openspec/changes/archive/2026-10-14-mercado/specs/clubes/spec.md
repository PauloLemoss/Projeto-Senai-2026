## MODIFIED Requirements

### Requirement: Consulta de clube com elenco, valor do elenco e patrimônio
`GET /clubs/{id}` SHALL devolver o clube com `players` (o elenco), ordenado por posição (GOL,
ZAG, LAT, MEI, ATA), depois por nome e depois por id; `squad_value` (soma dos valores de mercado
dos jogadores do clube) e `net_worth` (`cash` + `squad_value`) SHALL ser calculados a cada
consulta, nunca gravados. Cada jogador do elenco SHALL trazer `contract` (`purchase_value`,
`loyalty_until`, `remaining_days`, `penalty_rate`), com `remaining_days` e `penalty_rate`
calculados a cada consulta como se o jogador fosse vendido naquele instante (RN15), nunca
gravados.

#### Scenario: Clube recém-criado tem elenco vazio
- **WHEN** consulta-se um clube que acabou de ser criado
- **THEN** `players` vem `[]`, `squad_value` é `0.00` e `net_worth` é igual ao `cash`

#### Scenario: Elenco ordenado por posição, depois nome, depois id
- **WHEN** um clube tem jogadores em mais de uma posição
- **THEN** `players` vem na ordem GOL, ZAG, LAT, MEI, ATA; dentro da mesma posição, por nome e
  depois por id

#### Scenario: Clube inexistente
- **WHEN** o cliente consulta `GET /clubs/{id}` para um id que não existe
- **THEN** a API responde `404` com `message`

#### Scenario: Jogador do elenco mostra o contrato calculado na hora
- **WHEN** um clube com `cash` 261,15 tem no elenco um jogador comprado por 37,00, com fidelidade
  até `2027-03-02T10:15:00-03:00`, consultado quando faltam 120 dias
- **THEN** o jogador no `players` traz `contract` com `purchase_value` 37,00, `loyalty_until`
  `2027-03-02T10:15:00-03:00`, `remaining_days` 120 e `penalty_rate` 10 (faixa de 31 a 180 dias)
