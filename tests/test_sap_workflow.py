"""
Testes de Integração de Ponta a Ponta do SISPATO / SAP (RF001 a RF055)
======================================================================
Valida todo o fluxo operacional da Anatomia Patológica do HC-UFPE:
- Recepção HC (AGHU) com bipador de 10 dígitos e solicitações mistas (HP + IHQ)
- Rejeição / Não conformidade e superação preservando histórico
- Recepção Externa SUS com cadastro e verificação de duplicidade por CPF/CNS
- Macroscopia (frasco -> cassetes 1:N -> envio ao processamento)
- Processamento Técnico (tecidos -> blocos 1:N -> corte -> lâminas 1:N -> coloração -> envio microscopia -> arquivo)
- Microscopia (laudo prévio do residente -> revisão patologista -> complemento IHQ -> liberação -> arquivo)
- Visão Unificada (Árvore Hierárquica por QR Code), Acervo Científico (CSV) e Impressoras Zebra/Argox
"""


async def _init_test_db(db, base):
    async with db.engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


def test_fluxo_completo_sap_ponta_a_ponta(client, monkeypatch, tmp_path):
    # Usa banco SQLite isolado para tornar o teste idempotente em múltiplas execuções
    from src.resources.database import DatabaseManager, Base
    import asyncio

    test_db = DatabaseManager(f"sqlite+aiosqlite:///{tmp_path}/test_sap.db")
    asyncio.run(_init_test_db(test_db, Base))
    monkeypatch.setattr(client.app.state, "app_db", test_db, raising=False)

    # 1. Consulta com código de 10 dígitos do bipador HID (7 dígitos solicitação + 3 dígitos amostra)
    res_bip = client.get("/api/sap/solicitacao/1479377001")
    assert res_bip.status_code == 200
    dados_bip = res_bip.json()
    assert dados_bip["codigo_solicitacao"] == "1479377"
    assert dados_bip["amostra_bipada_foco"] == "1"
    assert dados_bip["total_amostras"] == 2

    # 2. Registra uma rejeição / não conformidade antes do recebimento
    res_rej = client.post(
        "/api/sap/rejeicoes",
        json={
            "codigo_solicitacao": "1479377",
            "numero_amostra": "1",
            "nome_paciente": dados_bip["nome_paciente"],
            "prontuario": dados_bip["prontuario"],
            "tipo_inconformidade": "Frasco / Material Físico",
            "motivo_padrao": "Quantidade de frascos divergente da solicitação",
            "operador": "rodolfo.recepcao",
        },
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["rejeicao"]["superada"] is False

    # 3. Recebe a solicitação 1479377 (supera a rejeição mantendo-a no histórico e gera etiquetas ZPL + Ficha)
    res_rec = client.post(
        "/api/sap/receber",
        json={
            "origem_peca": "HC",
            "codigo_solicitacao": "1479377",
            "amostras_conferidas": ["1", "2"],
            "descricoes_amostras": {
                "1": "PRODUTO DE RETOSSIGMOIDECTOMIA",
                "2": "AMPLIAÇÃO DE MARGEM PROXIMAL",
            },
            "suspeita_neoplasia": True,
            "operador": "rodolfo.recepcao",
        },
    )
    assert res_rec.status_code == 200
    exame_gerado = res_rec.json()["exame"]
    exame_id = exame_gerado["id"]
    codigo_sap = exame_gerado["codigo_sap"]
    assert codigo_sap.startswith("HP-")
    assert len(exame_gerado["etiquetas_frascos"]) == 2
    assert "^XA" in exame_gerado["etiquetas_frascos"][0]["zpl"]
    assert len(exame_gerado["ficha_trabalho"]["amostras"]) == 2

    # 4. Macroscopia: identifica frasco por QR Code, registra macroscopia, gera 2 cassetes e envia ao Processamento
    qr_frasco_1 = exame_gerado["etiquetas_frascos"][0]["qr_code"]
    res_id_macro = client.post(
        "/api/sap/macroscopia/identificar",
        json={"codigo": qr_frasco_1, "operador": "macro.silvana"},
    )
    assert res_id_macro.status_code == 200
    frasco_id = res_id_macro.json()["exame"]["arvore_subprodutos"][0]["id"]

    res_reg_macro = client.post(
        "/api/sap/macroscopia/registrar",
        json={
            "exame_id": exame_id,
            "frasco_id": frasco_id,
            "descricao_macroscopica": "Segmento de retossigmoide medindo 18 cm com lesão vegetante.",
            "quantidade_cassetes": 2,
            "descricao_fragmentos": "Lesão central e margem proximal",
            "operador": "macro.silvana",
        },
    )
    assert res_reg_macro.status_code == 200
    assert len(res_reg_macro.json()["cassetes_gerados"]) == 2

    res_env_proc = client.post(
        "/api/sap/macroscopia/enviar-processamento",
        json={"exame_id": exame_id, "operador": "macro.silvana"},
    )
    assert res_env_proc.status_code == 200
    assert res_env_proc.json()["exame"]["etapa_atual"] == "Processamento Técnico"

    # 5. Processamento Técnico: tecidos -> blocos -> corte/lâminas -> coloração -> envio microscopia -> arquivo blocos
    for acao in [
        "INICIAR_PROCESSAMENTO",
        "GERAR_BLOCOS",
        "CORTE_GERAR_LAMINAS",
        "COLORACAO_E_LIBERACAO",
        "ENVIAR_MICROSCOPIA",
        "ARQUIVAR_BLOCOS",
    ]:
        res_p = client.post(
            "/api/sap/processamento/executar",
            json={
                "exame_id": exame_id,
                "acao_processamento": acao,
                "quantidade_blocos": 1,
                "quantidade_laminas": 2,
                "operador": "tecnico.histologia",
            },
        )
        assert res_p.status_code == 200

    visao_proc = res_p.json()["exame"]
    assert visao_proc["etapa_atual"] == "Microscopia"
    assert visao_proc["quantidade_blocos"] == 2
    assert visao_proc["quantidade_laminas"] == 4

    # 6. Microscopia: laudo prévio do residente -> revisão -> complemento IHQ -> liberação -> arquivo lâminas
    res_lp = client.post(
        "/api/sap/microscopia/executar",
        json={
            "exame_id": exame_id,
            "acao_microscopia": "SALVAR_LAUDO_PREVIO",
            "laudo_previo": "Adenocarcinoma tubular invasivo moderadamente diferenciado.",
            "diagnostico_associado": "Adenocarcinoma de Retossigmoide",
            "operador": "residente.patologia",
        },
    )
    assert res_lp.status_code == 200
    assert "Pré-laudado" in res_lp.json()["exame"]["status_pre_laudo"]

    res_comp = client.post(
        "/api/sap/microscopia/executar",
        json={
            "exame_id": exame_id,
            "acao_microscopia": "SOLICITAR_COMPLEMENTO",
            "tipo_pedido": "IHQ",
            "marcadores": "MLH1, MSH2, MSH6, PMS2",
            "justificativa": "Pesquisa de instabilidade de microssatélites",
            "operador": "dra.jaque",
        },
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["exame"]["complementos"][0]["exame_ihq_gerado"].startswith("IHQ-")

    res_lib = client.post(
        "/api/sap/microscopia/executar",
        json={
            "exame_id": exame_id,
            "acao_microscopia": "LIBERAR_EXAME",
            "operador": "dra.jaque",
        },
    )
    assert res_lib.status_code == 200
    assert res_lib.json()["exame"]["concluido"] is True

    # 7. Rastreabilidade por QR Code de uma lâmina (RF041)
    qr_lamina = res_lib.json()["exame"]["arvore_subprodutos"][0]["cassetes"][0]["blocos"][0]["laminas"][0]["qr_code"]
    res_rast = client.get(f"/api/sap/rastreabilidade/{qr_lamina}")
    assert res_rast.status_code == 200
    assert res_rast.json()["exame"]["codigo_sap"] == codigo_sap
    assert res_rast.json()["exame"]["rejeicoes_historico"][0]["superada"] is True

    # 8. Recepção Externa SUS com verificação de CPF/CNS (RF005, RF006)
    res_sus = client.post(
        "/api/sap/receber",
        json={
            "origem_peca": "SUS",
            "prefixo_exame": "CCV",
            "paciente_sus": {
                "nome": "MARIA DO CARMO SILVA",
                "cpf": "12345678909",
                "cns": "700009876543210",
                "data_nascimento": "10/05/1982",
                "municipio_origem": "Prefeitura do Recife",
            },
            "amostras_sus": [{"numero_amostra": "1", "descricao_material": "Esfregaço Cérvico-Vaginal"}],
        },
    )
    assert res_sus.status_code == 200
    assert res_sus.json()["exame"]["codigo_sap"].startswith("CCV-")

    # 9. Busca no Acervo Científico e Exportação CSV (RF044-RF050) + Impressoras (RF054-RF055)
    res_acervo = client.get("/api/sap/acervo?marcador_complemento=MLH1")
    assert res_acervo.status_code == 200
    assert res_acervo.json()["total_encontrado"] >= 1

    res_csv = client.get("/api/sap/acervo/exportar-csv?diagnostico=Adenocarcinoma")
    assert res_csv.status_code == 200
    assert "Adenocarcinoma" in res_csv.text

    res_imp = client.get("/api/sap/impressoras")
    assert res_imp.status_code == 200
    assert len(res_imp.json()["impressoras"]) == 4
