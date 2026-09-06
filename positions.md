# Dicionário de posições — `playerPosition`

| Sigla | Significado                                              | Categoria ampla |
|-------|-----------------------------------------------------------|:----------------:|
| GK    | Goalkeeper (Goleiro)                                       | D     |
| LB    | Left Back (Lateral-esquerdo)                                | D                |
| RB    | Right Back (Lateral-direito)                                | D                |
| LCB   | Left Centre-Back (Zagueiro esquerdo)                        | D                |
| RCB   | Right Centre-Back (Zagueiro direito)                        | D                |
| MCB   | Middle Centre-Back (Zagueiro central, sistemas de 3 zagueiros) | D            |
| D     | Defender (Defensor genérico)                                | D                |
| LWB   | Left Wing-Back (Ala-esquerdo)                               | D*               |
| RWB   | Right Wing-Back (Ala-direito)                               | D*               |
| DM    | Defensive Midfielder (Volante)                              | M                |
| CM    | Central Midfielder (Meio-campista central)                  | M                |
| M     | Midfielder (Meio-campista genérico)                         | M                |
| AM    | Attacking Midfielder (Meia-atacante)                        | M*               |
| LM    | Left Midfielder (Meia pela esquerda)                        | M                |
| RM    | Right Midfielder (Meia pela direita)                        | M                |
| LW    | Left Winger (Ponta-esquerda)                                | A                |
| RW    | Right Winger (Ponta-direita)                                | A                |
| F     | Forward (Atacante)                                          | A                |
| CF    | Centre-Forward (Centroavante)                               | A                |

## Pontos de atenção

- **LWB/RWB (ala)**: fica numa faixa entre lateral e ala; em sistemas de 5 defensores é claramente linha de defesa, mas em 3-5-2 com ala mais avançado pode atuar funcionalmente mais perto do meio-campo. Mapeado como D por padrão, mas é a posição com maior risco de classificação errada por sigla fixa.
- **AM (meia-atacante)**: fisicamente joga avançado, quase junto do ataque, mas taticamente é meio-campo na nomenclatura padrão. Mapeado como M, mas é a posição com maior variância de posicionamento real em campo.
- **Recomendação geral**: usar essa tabela como prior/desempate, mas confirmar o agrupamento de linha (D/M/A) pela posição real (x) do jogador no evento — principalmente pra LWB/RWB e AM — em vez de fixar a categoria só pela sigla, já que jogadores se movem taticamente durante a partida.