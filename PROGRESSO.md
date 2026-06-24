# SRTP — Progresso de Implementação

## Contexto do Trabalho

**Disciplina:** Laboratório de Redes de Computadores — PUCRS  
**Entrega:** 30/06 até as 21h  
**Apresentação 1:** 30/06 | **Interoperabilidade:** 07/07  
**Grupo:** trios

### Objetivo

Implementar o **SRTP (Simple Reliable Transport Protocol)** — um protocolo de transporte confiável sobre UDP — em três variantes:

| Modo | Argumento | Status |
|------|-----------|--------|
| Stop-and-Wait | `--mode saw` | ✅ Funcionando |
| Go-Back-N | `--mode gbn` | 🔧 Esqueleto |
| Selective Repeat | `--mode sr` | 🔧 Esqueleto |

---

## Especificação do Protocolo (resumo)

### Cabeçalho — 9 bytes

```
 0                   1                   2
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|S|F|        SEQ (14 bits)       |A|N|        ACK (14 bits)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Length (8 bits)      |           CRC32 (32 bits)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **SEQ/ACK:** 14 bits, contado em pacotes (não bytes), wrap-around em 16384
- **Length durante transferência:** 255 = pacote intermediário; < 255 = último pacote; 0 = fim sem payload residual
- **Length durante handshake:** tamanho de janela proposto
- **CRC32:** calculado com campo CRC zerado; pacote corrompido é descartado silenciosamente (sem NACK)

### Modelo de Portas

```
Receiver:  escuta na porta P
Sender:    envia para P, recebe ACKs em P+1 (vincula após handshake)
```

Ambos recebem apenas `P` como parâmetro. O receiver envia ACKs de P para P+1 do sender.

### Handshake (three-way)

```
Sender                   Receiver
  |-- SYN (Length=W_s) -->|
  |<-- SYN+ACK (Length=W_r)|
  |-- ACK ---------------->|
        [transferência]
```

Janela efetiva = `min(W_sender, W_receiver)`

### Encerramento (two-way)

```
Sender        Receiver
  |-- FIN -->|
  |<- FIN+ACK|
```

---

## Arquivos Criados

```
TF - Redes/
├── packet.py       # Cabeçalho, pack/unpack, CRC32, aritmética de SEQ
├── connection.py   # Handshake three-way, teardown two-way
├── sender.py       # Lógica do sender (SAW ✅, GBN 🔧, SR 🔧)
├── receiver.py     # Lógica do receiver (SAW ✅, GBN 🔧, SR 🔧)
├── srtp.py         # Entry point CLI
└── PROGRESSO.md    # Este arquivo
```

### Uso

```bash
# Receiver
python srtp.py --listen --port 6000 --output recebido.bin --mode saw --window 4

# Sender
python srtp.py --host 192.168.1.10 --port 6000 --file arquivo.bin --mode saw --window 4

# Modos disponíveis: saw | gbn | sr
# Window: 1-255 (ignorado no SAW, negociado no GBN/SR)
```

---

## O que Está Funcionando ✅

### `packet.py` — 100% completo
- Empacotamento e desempacotamento do cabeçalho de 9 bytes
- CRC32 calculado sobre `header (CRC=0) + payload`
- Detecção de corrupção: pacote com CRC inválido retorna `None`
- Aritmética circular de SEQ (14 bits, módulo 16384)
- Testado: round-trip, corrupção de byte, payload de 255 bytes

### `connection.py` — 100% completo
- `handshake_active`: sender envia SYN, aguarda SYN+ACK, envia ACK final; retorna janela negociada e endereço do receiver
- `handshake_passive`: receiver aguarda SYN, responde SYN+ACK, confirma ACK; retorna janela negociada e endereço do sender
- `teardown_active`: sender envia FIN, aguarda FIN+ACK no socket de ACKs (P+1)
- Tratamento de `ConnectionResetError` do Windows (ICMP port unreachable em UDP)

### `sender.py` / `receiver.py` SAW — 100% completo e testado
- Transferência de 12.767 bytes (51 pacotes de dados) com hash SHA256 idêntico ao original
- Timeout de 100ms com retransmissão automática
- Pacotes fora de ordem descartados silenciosamente no receiver
- Pacotes com CRC inválido descartados silenciosamente
- Estatísticas: pacotes enviados, retransmissões, tempo, throughput

---

## O que Falta Implementar 🔧

### 1. Go-Back-N — `sender.py` + `receiver.py`

**Sender (`send_gbn`):**
- [ ] Corrigir o mapeamento SEQ → índice de chunk (wrap-around após 16383 pacotes)
- [ ] Implementar timer individual por pacote base da janela (não apenas o base)
- [ ] ACK cumulativo: ao receber ACK(n), avançar `base` para `n+1` corretamente com wrap-around
- [ ] Ao receber NACK ou timeout: retransmitir **todos** os pacotes desde `base` até `next_seq_idx`

**Receiver (`recv_gbn`):**
- [ ] Está majoritariamente correto — descartar pacotes fora de ordem e enviar NACK com SEQ esperado
- [ ] Verificar: o receiver GBN deve reenviar ACK do último pacote em ordem ao receber duplicatas

### 2. Selective Repeat — `sender.py` + `receiver.py`

**Sender (`send_sr`):**
- [ ] Corrigir mapeamento SEQ → índice (wrap-around)
- [ ] Timer individual por pacote dentro da janela
- [ ] Ao receber ACK(n): marcar apenas pacote n como confirmado
- [ ] Ao receber NACK(n): retransmitir apenas o pacote n
- [ ] Avançar `base` somente quando pacotes contíguos a partir do base forem todos ACKados

**Receiver (`recv_sr`):**
- [ ] Buffer de fora-de-ordem já implementado
- [ ] NACK quando detecta lacuna (já implementado como fallback)
- [ ] Verificar entrega em ordem ao preencher lacunas

### 3. Testes obrigatórios (Parte 1 — SAW)

Todos entre **máquinas distintas** com captura Wireshark (`.pcapng`):

| Cenário | Parâmetro | Ferramenta |
|---------|-----------|------------|
| L0 | 0ms latência | baseline |
| L1 | 50ms latência | clumsy |
| L2 | 100ms latência | clumsy |
| L3 | 150ms latência | clumsy |
| P0 | 0% perda | baseline |
| P1 | 1% perda | clumsy |
| P2 | 5% perda | clumsy |
| P3 | 10% perda | clumsy |
| P4 | 25% perda | clumsy |

Arquivo de teste: mínimo 50 pacotes = ≥ 12.750 bytes.

### 4. Testes obrigatórios (Parte 2 — GBN e SR)

Repetir todos os cenários L0–L3 e P0–P4 para GBN e SR. Adicionar:

| Cenário | Parâmetro |
|---------|-----------|
| R0 | 0% reordenação |
| R1 | 10% reordenação |
| R2 | 25% reordenação |

Testar com **pelo menos dois tamanhos de janela** (sugestão: 4 e 16).

### 5. Relatório (Parte 1)

- [ ] Análise do throughput teórico do SAW: `U = L/R / (RTT + L/R)` onde L = 264 bytes (9 header + 255 payload), confrontar com L0/P0 medido
- [ ] Análise dos cenários L0–L3 com capturas Wireshark como evidência
- [ ] Análise dos cenários P0–P4 com throughput medido e número de retransmissões
- [ ] Demonstração de detecção de CRC32 (captura de pacote corrompido)

### 6. Relatório (Parte 2)

- [ ] Análise comparativa SAW vs GBN vs SR sob latência (L0–L3)
- [ ] Análise comparativa GBN vs SR sob perda (P1–P4) — custo de retransmissão
- [ ] Análise comparativa GBN vs SR sob **reordenação** (R0–R2) — ponto central da Parte 2
- [ ] Impacto do tamanho de janela em cada protocolo
- [ ] Conclusão comparativa baseada nos dados medidos

### 7. Entrega

- [ ] README com instruções de execução e argumentos CLI
- [ ] Diretório `capturas/` com arquivos `.pcapng` nomeados (ex: `saw_L2.pcapng`, `sr_R2_janela16.pcapng`)
- [ ] Relatório em PDF único cobrindo Parte 1 e Parte 2
- [ ] `.zip` com tudo acima (sem binários ou arquivos temporários)

---

## Bugs Conhecidos / Observações

1. **GBN e SR não testados end-to-end ainda** — os loops de envio/recepção têm problemas de mapeamento SEQ→índice que precisam ser revisados antes de qualquer teste real.

2. **Wrap-around do SEQ** — com arquivos grandes (> 16383 × 255 ≈ 4 MB) o SEQ dá wrap-around em 16384. Os modos GBN/SR precisam usar aritmética modular correta no mapeamento índice↔SEQ.

3. **Timer por pacote no GBN/SR** — a implementação atual usa verificações periódicas de timeout no loop. Para fidelidade ao spec, cada pacote deve ter seu próprio timestamp de envio e ser retransmitido individualmente após 100ms sem ACK (SR) ou o grupo inteiro (GBN).

4. **Windows SO_REUSEADDR** — adicionado nas sockets para evitar `[WinError 10048]` ao reiniciar rapidamente o processo na mesma porta.
