# SRTP — O que falta para entregar

```
Gerado em 27/06/2026 · Entrega: 30/06 até 21h
```
Legenda: n pronto e validado nn existe mas com bug / incompleto n não existe

## 1. Protocolo Base (especificação)

Item Status Nota
Cabeçalho 9 bytes n OK packet.py
CRC32 sobre header(CRC=0)+payload n OK packet.py
Descarte silencioso de CRC inválido (sem
NACK)

```
n OK parse_packet → None
```
SEQ 14 bits, wrap em 16384 n OK seq_add
Handshake three-way (janela = min) n OK connection.py
Teardown two-way (FIN/FIN+ACK) n OK connection.py
Timeout fixo 100 ms n OK connection.py
Portas P / P+1, --listen n OK srtp.py
Seleção --mode saw/gbn/sr n OK srtp.py
Edge case Length=0 (arquivo múltiplo exato de 255) [x] OK (implementado e testado)
## 2. Parte 1 — Stop-and-Wait (peso total 40%)

## Implementação (20%)

#### n send_saw / recv_saw completos e testados (51 pacotes, SHA256 idêntico).

## Relatório (20%) — n não iniciado

#### [x] Throughput teórico máximo do SAW (fórmula ARQ, Kurose & Ross §3.4) vs medido em L0/P

#### [x] Análise L0–L3: throughput + nº retransmissões, explicar transição L1→L2→L3 com timeout

#### 100 ms

#### [x] Análise P0–P4: throughput + retransmissões, relacionar com eficiência sob perda

#### [x] Análise CRC32: captura de pacote corrompido detectado + o que aconteceria sem CRC

## Capturas obrigatórias (Wireshark .pcapng, máquinas distintas, ≥50 pacotes)

#### [x] L0 (0 ms), L1 (50 ms), L2 (100 ms), L3 (150 ms) — clumsy latência (capturado e salvo)

#### [x] P0 (0%), P1 (1%), P2 (5%), P3 (10%), P4 (25%) — clumsy perda (capturado e salvo)

## 3. Parte 2 — Go-Back-N e Selective Repeat (peso total 50%)

## Implementação (20%) — nn esqueleto com bugs

#### GBN sender (send_gbn)


#### [ ] Mapeamento SEQ → índice de chunk com wrap-around correto (_seq_to_idx é frágil)

#### [ ] Timer do base da janela (lógica atual confusa, rearma errado)

#### [ ] ACK cumulativo: avançar base corretamente

#### [ ] Timeout/NACK: retransmitir TODOS desde base

#### [ ] Contagem de retransmissões correta (hoje soma 0 em alguns casos)

#### [ ] Testar end-to-end

#### GBN receiver (recv_gbn)

#### [ ] Validar: só aceita em ordem, NACK com SEQ esperado, reenvia ACK do último em ordem em

#### duplicatas

#### SR sender (send_sr)

#### [ ] Mapeamento SEQ → índice com wrap-around

#### [ ] Timer individual por pacote

#### [ ] ACK(n) marca só n; NACK(n) retransmite só n

#### [ ] Avançar base só sobre ACKs contíguos

#### [ ] Testar end-to-end

#### SR receiver (recv_sr)

#### [ ] Validar bufferização fora-de-ordem + entrega em ordem ao preencher lacunas

### Relatório (30%) — n não iniciado

#### [ ] Comparativo SAW vs GBN vs SR sob latência (L0–L3)

#### [ ] Comparativo GBN vs SR sob perda (P1–P4) — custo de retransmissão

#### [ ] Comparativo sob reordenação (R0–R2) — ponto central, vale 10%, capturas mostrando lote

#### (GBN) vs buffer (SR)

#### [ ] Impacto do tamanho de janela em cada protocolo

#### [ ] Conclusão comparativa fundamentada em dados

### Capturas obrigatórias (GBN e SR)

#### [ ] Repetir L0–L3 e P0–P4 para GBN

#### [ ] Repetir L0–L3 e P0–P4 para SR

#### [ ] R0 (0%), R1 (10%), R2 (25%) reordenação — GBN e SR

#### [ ] Tudo com 2 tamanhos de janela (sugestão: 4 e 16)

#### [ ] Nomear arquivos: saw_L2.pcapng, sr_R2_janela16.pcapng, etc.

## 4. Entrega / Empacotamento

#### [ ] README real (atual está corrompido/vazio) — compilação, execução, argumentos CLI

#### [ ] Diretório capturas/ com todos os .pcapng nomeados por cenário

#### [ ] Relatório PDF único (Parte 1 + Parte 2)

#### [ ] .zip sem binários / temporários / build

Remover do zip: __pycache__/, *.pyc, received_test.bin, test_input.bin, recv_out.txt, recv_err.txt, received_output.bin

## 5. Teste de Interoperabilidade (10%) — 07/07, ao vivo


#### [ ] Garantir conformidade estrita ao spec (handshake, portas, cabeçalho) para funcionar com

#### outro grupo

#### [ ] Verificar arquivo idêntico por hash

## Resumo de Prioridade (ordem sugerida)

# Tarefa Observação
1 Corrigir GBN Bloqueio técnico, libera capturas da Parte 2
2 Corrigir SR Idem
3 Edge case Length=0 Rápido, evita falha na interoperabilidade
4 Montar ambiente + clumsy e coletar
capturas

```
SAW primeiro, depois GBN/SR
```
5 Escrever relatório Conforme as capturas forem saindo
6 README + empacotar zip Etapa final

Estimativa: protocolo base + SAW funcional ≈ 30–35% concluído. Restante (GBN/SR corretos, capturas, relatório,
README) ≈ 65–70%.