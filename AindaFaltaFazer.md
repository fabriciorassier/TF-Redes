# SRTP — O que falta para entregar

**Atualizado em: 29/06/2026 | Entrega: 30/06 até 21h**

---

## Resumo rápido de prioridade

| # | Tarefa | Bloqueador de quê |
|---|--------|-------------------|
| 1 | Capturar `saw_L0.pcapng` (faltando) | Relatório Parte 1 completo |
| 2 | Capturar GBN: L0–L3, P0–P4, R0–R2 × janelas 4 e 16 | Tabelas Parte 2 + imagens Wireshark |
| 3 | Capturar SR: L0–L3, P0–P4, R0–R2 × janelas 4 e 16 | Idem |
| 4 | Screenshots Wireshark reordenação GBN/SR → salvar em `capturas/` | Figuras do relatório |
| 5 | Preencher tabelas Parte 2 no relatorio.tex com dados medidos | Relatório final |
| 6 | Montar o `.zip` de entrega | Entrega |

---

## Detalhamento

### Capturas obrigatórias — NENHUMA da Parte 2 existe ainda

**Ambiente necessário:** Mac (WiFi) + Windows (Ethernet) na mesma rede, clumsy no Windows, Wireshark no Windows.

**Setup de rede:**
1. Descobrir IPs: no Mac `ipconfig getifaddr en0`; no Windows `ipconfig`
2. Testar: `ping <IP-Windows>` do Mac
3. Liberar portas no firewall Windows: UDP entrada/saída nas portas 6000 e 6001
4. Instalar clumsy (https://github.com/jagt/clumsy/releases) no Windows
5. Filtro do clumsy: `udp.DstPort == 6000 or udp.SrcPort == 6000`

**Como rodar os testes entre máquinas:**
```bash
# Windows (receiver):
python srtp.py --listen --port 6000 --output recebido.bin --mode gbn --window 4

# Mac (sender):
python3 srtp.py --host <IP-Windows> --port 6000 --file test_input.bin --mode gbn --window 4
```

**Capturas SAW (falta só L0):**
- [ ] `saw_L0.pcapng` — sem clumsy, baseline (L1–L3 e P0–P4 já existem em `capturas/`)

**Capturas GBN — tudo falta:**
- [ ] `gbn_L0_janela4.pcapng` e `gbn_L0_janela16.pcapng`
- [ ] `gbn_L1_janela4.pcapng` e `gbn_L1_janela16.pcapng`
- [ ] `gbn_L2_janela4.pcapng` e `gbn_L2_janela16.pcapng`
- [ ] `gbn_L3_janela4.pcapng` e `gbn_L3_janela16.pcapng`
- [ ] `gbn_P0_janela4.pcapng` e `gbn_P0_janela16.pcapng`
- [ ] `gbn_P1_janela4.pcapng` e `gbn_P1_janela16.pcapng`
- [ ] `gbn_P2_janela4.pcapng` e `gbn_P2_janela16.pcapng`
- [ ] `gbn_P3_janela4.pcapng` e `gbn_P3_janela16.pcapng`
- [ ] `gbn_P4_janela4.pcapng` e `gbn_P4_janela16.pcapng`
- [ ] `gbn_R0_janela4.pcapng` e `gbn_R0_janela16.pcapng`
- [ ] `gbn_R1_janela4.pcapng` e `gbn_R1_janela16.pcapng`
- [ ] `gbn_R2_janela4.pcapng` e `gbn_R2_janela16.pcapng`

**Capturas SR — tudo falta:**
- [ ] Mesmos cenários acima com prefixo `sr_`

**Screenshots Wireshark para o relatório:**
- [ ] `capturas/gbn_reorder_wireshark.png` — captura do cenário R2 GBN mostrando NACKs e retransmissão em lote
- [ ] `capturas/sr_reorder_wireshark.png` — captura do cenário R2 SR mostrando buffer e ACKs individuais

### Relatório (relatorio.tex)

Texto e análise estão todos escritos. Falta só preencher os dados nas tabelas vazias:

- [ ] Tabela 3 — Comparação de Throughput sob Latência (SAW/GBN/SR × L0–L3) → valores de KB/s
- [ ] Tabela 4 — Custo de Retransmissões GBN vs SR (P1–P4 × janelas 4 e 16) → nº retransmissões

Depois de preencher as tabelas, compilar o PDF no Overleaf e baixar para incluir no zip.

### Empacotamento do .zip

- [ ] Criar `capturas/` com todos os `.pcapng` nomeados corretamente
- [ ] Verificar que `README.md` está legível
- [ ] Gerar `.zip` excluindo: `__pycache__/`, `*.pyc`, `received_test.bin`, `test_input.bin`, `recv_out.txt`, `recv_err.txt`, `received_output.bin`, `received_test.bin`, `PROGRESSO.md`, `AindaFaltaFazer.md`

```bash
# Comando para gerar o zip (rodar na pasta do projeto):
zip -r SRTP_Grupo.zip . \
  --exclude "*.pyc" \
  --exclude "__pycache__/*" \
  --exclude "received_test.bin" \
  --exclude "test_input.bin" \
  --exclude "recv_out.txt" \
  --exclude "recv_err.txt" \
  --exclude "received_output.bin" \
  --exclude "PROGRESSO.md" \
  --exclude "AindaFaltaFazer.md" \
  --exclude ".git/*"
```

---

## O que NÃO falta (já está feito)

- ✅ Protocolo base completo: packet.py, connection.py, srtp.py
- ✅ SAW: send_saw + recv_saw (testado, SHA256 OK)
- ✅ GBN: send_gbn + recv_gbn (bugs corrigidos em 29/06, testado localmente)
- ✅ SR: send_sr + recv_sr (bugs corrigidos em 29/06, testado localmente)
- ✅ Edge case Length=0 (arquivo múltiplo exato de 255 bytes) — testado nos 3 modos
- ✅ README.md completo
- ✅ Relatório: todo o texto escrito (Parte 1 com dados, Parte 2 análise, Conclusão, Referências)
- ✅ Capturas SAW: L1, L2, L3, P0, P1, P2, P3, P4 (falta só L0)
- ✅ Conformidade com spec para interoperabilidade (packet.py verificado)

---

## Interoperabilidade (07/07)

O que garante conformidade:
- Cabeçalho de 9 bytes com layout exato (verificado em packet.py)
- CRC32 calculado com campo CRC zerado (confirmado)
- Handshake three-way e teardown two-way (confirmado em connection.py)
- Modelo de portas P/P+1 (confirmado em srtp.py)

Risco: **nenhum** conhecido no protocolo base. Testar com outro grupo usando `--mode saw` primeiro.
