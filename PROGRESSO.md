# SRTP — Progresso de Implementação

**Atualizado em: 29/06/2026**
**Entrega: 30/06 até 21h | Apresentação: 30/06 | Interoperabilidade: 07/07**

---

## Estado Atual: ~75% concluído

---

## Sessão de 29/06/2026 — o que foi feito

### Bugs corrigidos (sender.py / receiver.py)

**Bug crítico em `send_gbn`** — NACK tratado como ACK cumulativo:
- Antes: `if ack_flag == 1: ... elif nack_flag == 1:` → NACKs (que têm ambos `ack_flag=1` e `nack=1`) entravam no branch de ACK, avançando a base para o pacote perdido
- Depois: `if nack_flag: ... elif ack_flag:` → prioridade correta

**Bug de contagem em `send_gbn`** — `stats.retransmissions += (next_idx - base)` era calculado após `next_idx = base`, sempre 0. Corrigido para calcular antes do reset.

**Bug de IndexError em `send_gbn`** — ao receber o último ACK, `base` avança para `total` e o timeout check tentava `send_time[total]` (fora do array). Corrigido com `if base < total and ...`.

**`send_gbn` refatorado** — `send_times` dict → `send_time` list por pacote; `next_seq_idx` → `next_idx`; timer resetado corretamente ao retransmitir por timeout.

**`recv_gbn` corrigido** — distinção de duplicatas vs fora de ordem por aritmética modular:
- `diff == 0` → em ordem → ACK
- `diff > 8192` → duplicata (sender retransmitiu pacote já recebido) → re-ACK do último em ordem
- `diff <= 8192` → fora de ordem → NACK

**`recv_sr` corrigido** — duplicatas (offset ≥ 16384 - window_size) recebem re-ACK individual em vez de NACK.

### Testes realizados (localhost, sem perda)

Todos com SHA256 idêntico ao original (test_input.bin, 12.767 bytes, 51 pacotes):

| Modo | Janela | Pacotes | Retransmissões | SHA256 |
|------|--------|---------|----------------|--------|
| SAW | — | 51 | 0 | ✓ |
| GBN | 4 | 51 | 0 | ✓ |
| GBN | 16 | 51 | 0 | ✓ |
| SR | 4 | 51 | 0 | ✓ |
| SR | 16 | 51 | 0 | ✓ |

Edge case Length=0 (arquivo de 1275 bytes = 5×255) também passou nos 3 modos.

### Relatório (relatorio.tex)

- Referências corrigidas (eram de outro trabalho — INEP/Azure; agora: Kurose & Ross, Forouzan, Peterson & Davie, clumsy, Python docs)
- Parte 2 — Análise sob latência: fórmula U = min(1, W·Ttrans/RTT) com cálculo numérico para L3
- Parte 2 — Análise sob perda: custo O(W·p) no GBN vs O(p) no SR
- Parte 2 — Análise sob reordenação: comportamento detalhado GBN (descarte + lote) e SR (buffer + flush)
- Parte 2 — Impacto do tamanho de janela: trade-off throughput vs custo de retransmissão
- Conclusão: escrita completa com base nos dados reais da Parte 1
- Imagens Wireshark: todas as referências preservadas (ver tabela abaixo)

**Imagens no relatório:**
| Arquivo | Existe? | Seção |
|---------|---------|-------|
| `imagens/saw_L2_wireshark.png` | ✓ (no Overleaf) | Parte 1 — Latência |
| `imagens/saw_crc_wireshark.png` | ✓ (no Overleaf) | Parte 1 — CRC32 |
| `capturas/gbn_reorder_wireshark.png` | ✗ (capturar) | Parte 2 — Reordenação GBN |
| `capturas/sr_reorder_wireshark.png` | ✗ (capturar) | Parte 2 — Reordenação SR |

### README.md
- Reescrito do zero: requisitos, como rodar, argumentos, modelo de portas, estrutura do projeto, nomenclatura de capturas

---

## Estado por componente

| Componente | Status |
|-----------|--------|
| `packet.py` — cabeçalho, CRC32, aritmética SEQ | ✅ Completo |
| `connection.py` — handshake, teardown | ✅ Completo |
| `sender.py` — SAW | ✅ Completo e testado |
| `receiver.py` — SAW | ✅ Completo e testado |
| `sender.py` — GBN | ✅ Bugs corrigidos, testado localmente |
| `receiver.py` — GBN | ✅ Bugs corrigidos, testado localmente |
| `sender.py` — SR | ✅ Testado localmente |
| `receiver.py` — SR | ✅ Bugs corrigidos, testado localmente |
| Edge case Length=0 | ✅ Implementado e testado |
| `README.md` | ✅ Escrito |
| Relatório Parte 1 (texto + dados) | ✅ Completo |
| Relatório Parte 2 (texto) | ✅ Completo (tabelas aguardam dados das capturas) |
| Relatório — Conclusão | ✅ Escrita |
| Capturas SAW L0 | ⚠️ Falta (L1–L3 e P0–P4 existem) |
| Capturas GBN (L0–L3, P0–P4, R0–R2, w4 e w16) | ❌ Falta |
| Capturas SR (L0–L3, P0–P4, R0–R2, w4 e w16) | ❌ Falta |
| Tabelas Parte 2 preenchidas com dados | ❌ Aguarda capturas |
| `.zip` de entrega | ❌ Falta |

---

## Uso

```bash
# Receiver
python3 srtp.py --listen --port 6000 --output recebido.bin --mode gbn --window 16

# Sender
python3 srtp.py --host 192.168.1.10 --port 6000 --file arquivo.bin --mode gbn --window 16

# Modos: saw | gbn | sr
```
